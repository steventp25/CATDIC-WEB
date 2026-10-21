# BACKEND/sync/sincronizador.py
# Etapa 1 · T5 — Sincroniza la tabla `visitas` con las carpetas de Dropbox (POST /api/dropbox/sync).
#
# - Dropbox SOLO LECTURA (§1.3): el escaneo lo hace sync.escaner_dropbox (iterdir/stat).
# - Regla de Oro #1: fecha y clase salen del nombre de la carpeta o del PDF (P1), nunca del
#   mtime. Lo que falte queda PENDIENTE y la visita va a "Con dudas" con su DUDA_BLOQUEANTE.
#   Si el número de visita no es un entero legible, la visita NO se inserta (se reporta en `omitidas`).
# - Upsert por (proyecto_id, ruta_carpeta). Una transacción y una fila de auditoría por proyecto (§1.5).
# - Visita existente: no se pisa lo que Steven respondió en la Mesa de Dudas ni el estado/salida
#   de una visita que ya avanzó (En proceso, En revisión, Procesada).
# - P3 ESTRICTA (T8, decisión de Steven): una visita nueva Parcial/Completivo queda "Procesada"
#   solo si en INFORMES\2.DATA PROCESADA\ hay un único STP con su misma fecha DD-MM-AAAA y que
#   nombra su misma clase. Un STP de esa fecha sin clase (o con las dos), varios candidatos o una
#   visita Mixta -> "Con dudas" con DUDA_BLOQUEANTE en `estado`. Sin STP de la fecha -> "Sin procesar".
# - origen_datos_json (T8): de dónde salió la fecha, la clase y el estado de cada visita.
# - Corrección única (T8): las "Procesada" que dejó la regla laxa de T5 se revisan una vez con la
#   regla estricta (auditoría SYNC/CORREGIR_P3_ESTRICTA si cambian).
import json
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from database import get_connection
from reglas_ingenieria import PENDIENTE
from sync.escaner_dropbox import LAYOUT_SUPERVISION, SUBRUTA_INFORMES_PROCESADOS, escanear_proyecto
from sync.parser_visitas import (
    CAMPO_CLASE,
    CAMPO_FECHA,
    CLASE_COMPLETIVO,
    CLASE_PARCIAL,
    PALABRAS_CLASE,
)

MODULO_AUDITORIA = "SYNC"
ACCION_AUDITORIA = "SINCRONIZAR_DROPBOX"
ACCION_CORREGIR_P3 = "CORREGIR_P3_ESTRICTA"
USUARIO = "steven"

TIPO_SUPERVISION = "Supervisión"
# P4: las visitas de Supervisión piden solo STP-MIVED (el FI MIVED va por nivel y tipo, no por visita)
FORMATOS_SUPERVISION = ["STP-MIVED"]

ESTADO_SIN_PROCESAR = "Sin procesar"
ESTADO_CON_DUDAS = "Con dudas"
ESTADO_PROCESADA = "Procesada"
CLASES_SIMPLES = (CLASE_PARCIAL, CLASE_COMPLETIVO)
# Estados que la sincronización nunca toca (la visita ya avanzó)
ESTADOS_AVANZADOS = {"En proceso", "En revisión", "Procesada"}
# Estados que pueden pasar a "Con dudas" si aparece una duda nueva
ESTADOS_ABIERTOS = {"Sin procesar", "En cola", "Con dudas"}

DUDA = "DUDA_BLOQUEANTE"
HALLAZGO = "HALLAZGO_INTERNO"
CAMPO_ARCHIVOS = "archivos_json"
CAMPO_ESTADO = "estado"
CAMPO_NOMBRE = "nombre_carpeta"
MOTIVO_SIN_PDF = "la carpeta no tiene PDF de la visita"

# Origen del estado en origen_datos_json["estado"] (solo cuando lo decide el sync)
ORIGEN_ESTADO_P3 = "sync_p3"            # Procesada: un único STP con su fecha y su clase
ORIGEN_ESTADO_DUDAS = "sync_dudas"      # Con dudas: campos pendientes, sin PDF o P3 ambigua
ORIGEN_ESTADO_SIN_STP = "sync_sin_stp"  # Sin procesar: ningún STP válido de su fecha
REGLA_P3 = "estricta"                   # marca de que la visita ya se evaluó con la regla de T8

_RE_CLASE_INFORME = re.compile(
    r"\b(" + "|".join(sorted(PALABRAS_CLASE, key=len, reverse=True)) + r")\b", re.IGNORECASE
)
# "<base>.pdf", "<base> v2.pdf", "<base> v3.pdf" -> mismo informe (§5.2, versionado)
_RE_VERSION_PDF = re.compile(r"^(?P<base>.*?)(?:\s+v(?P<version>\d+))?\.pdf$", re.IGNORECASE)
_MARCA_STP = " - stp - "


class ProyectoNoEncontrado(LookupError):
    """El proyecto pedido con ?proyecto_id= no está en la tabla `proyectos`."""


# ---------- Utilidades ----------

def _ahora() -> str:
    return datetime.now().isoformat()


def _json(valor) -> str:
    return json.dumps(valor, ensure_ascii=False)


def _slug(texto: str) -> str:
    """'17.PARCIAL VERTICALES S-3 28-09-2026' -> '17-parcial-verticales-s-3-28-09-2026'."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-") or "visita"


def _id_visita(conn, proyecto_id: str, nombre_carpeta: str, usados: Set[str]) -> str:
    """Id estable y legible; si choca con otra visita, sufijo -2, -3..."""
    base = f"{proyecto_id}-{_slug(nombre_carpeta)}"
    candidato, n = base, 2
    while candidato in usados or conn.execute(
            "SELECT 1 FROM visitas WHERE id = ?", (candidato,)).fetchone():
        candidato = f"{base}-{n}"
        n += 1
    usados.add(candidato)
    return candidato


def _es_numero(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _clases_en_texto(texto: str) -> Set[str]:
    return {PALABRAS_CLASE[m.group(1).upper()] for m in _RE_CLASE_INFORME.finditer(texto)}


# ---------- P3: STP ya procesados ----------

def stp_de_fecha(informes: List[Dict], fecha_iso: str) -> List[Dict]:
    """STP de `informes` con la misma fecha exacta DD-MM-AAAA (no M/D, no MIVED).

    Las versiones de un mismo informe (<base>.pdf, <base> v2.pdf...) cuentan como uno solo.
    Devuelve [{"base", "rutas" (ordenadas por versión), "clases" (clases que nombra)}].
    """
    if fecha_iso == PENDIENTE:
        return []
    aaaa, mm, dd = fecha_iso.split("-")
    re_fecha = re.compile(rf"(?<!\d){dd}-{mm}-{aaaa}(?!\d)")

    grupos: Dict[str, Dict] = {}
    for informe in informes:
        nombre = informe["nombre"]
        if _MARCA_STP not in nombre.casefold():
            continue
        coincide = _RE_VERSION_PDF.match(nombre)
        if not coincide or not re_fecha.search(nombre):
            continue
        base = coincide.group("base").strip()
        version = int(coincide.group("version") or 1)
        grupo = grupos.setdefault(base.casefold(), {"base": base, "versiones": [], "clases": set()})
        grupo["versiones"].append((version, informe["ruta"]))
        grupo["clases"] |= _clases_en_texto(nombre)

    resultado = []
    for clave in sorted(grupos):
        grupo = grupos[clave]
        resultado.append({
            "base": grupo["base"],
            "rutas": [r for _, r in sorted(grupo["versiones"])],
            "clases": sorted(grupo["clases"]),
        })
    return resultado


def evaluar_p3(informes: List[Dict], fecha_iso: str, clase: str) -> Dict:
    """Regla P3 estricta (decisión de Steven, T8). Devuelve:

    {"estado": Procesada | Con dudas | Sin procesar, "origen": sync_p3 | sync_dudas | sync_sin_stp,
     "stp": rutas del STP elegido (solo Procesada), "candidatos": [grupos], "descartados": [grupos],
     "motivo": texto}
    - Sin STP de la fecha -> Sin procesar.
    - Visita Mixta (o sin clase simple) con algún STP de su fecha -> Con dudas (no se decide solo).
    - Parcial/Completivo: Procesada solo si hay UN STP que nombra exactamente su clase y ningún
      otro STP de la fecha sin clase (o con las dos). Varios con su clase, o alguno sin clase
      -> Con dudas. Los que nombran solo la clase contraria se descartan (son de otra visita).
    """
    grupos = stp_de_fecha(informes, fecha_iso)
    vacio = {"stp": [], "candidatos": [], "descartados": []}
    if not grupos:
        return {**vacio, "estado": ESTADO_SIN_PROCESAR, "origen": ORIGEN_ESTADO_SIN_STP,
                "motivo": "no hay STP con la fecha de la visita"}
    if clase not in CLASES_SIMPLES:
        return {**vacio, "estado": ESTADO_CON_DUDAS, "origen": ORIGEN_ESTADO_DUDAS,
                "candidatos": grupos,
                "motivo": f"la visita es {clase} y hay STP con su fecha; no se decide "
                          "automáticamente cuál le corresponde"}
    contraria = CLASE_COMPLETIVO if clase == CLASE_PARCIAL else CLASE_PARCIAL
    misma = [g for g in grupos if g["clases"] == [clase]]
    descartados = [g for g in grupos if g["clases"] == [contraria]]
    sin_clase = [g for g in grupos if g not in misma and g not in descartados]
    if len(misma) == 1 and not sin_clase:
        return {**vacio, "estado": ESTADO_PROCESADA, "origen": ORIGEN_ESTADO_P3,
                "stp": misma[0]["rutas"], "candidatos": misma, "descartados": descartados,
                "motivo": f"un único STP con la fecha y la clase {clase}"}
    if misma or sin_clase:
        if sin_clase and not misma:
            motivo = f"hay STP con la fecha de la visita pero su nombre no dice {clase}"
        elif sin_clase:
            motivo = (f"hay STP con la fecha y la clase {clase} y además STP de esa fecha "
                      "sin clase en el nombre")
        else:
            motivo = f"hay {len(misma)} STP con la fecha y la clase {clase}"
        return {**vacio, "estado": ESTADO_CON_DUDAS, "origen": ORIGEN_ESTADO_DUDAS,
                "candidatos": misma + sin_clase, "descartados": descartados, "motivo": motivo}
    return {**vacio, "estado": ESTADO_SIN_PROCESAR, "origen": ORIGEN_ESTADO_SIN_STP,
            "descartados": descartados,
            "motivo": f"los STP de esa fecha son de la clase {contraria}"}


def _nombres_candidatos(grupos: List[Dict]) -> List[List[str]]:
    return [[Path(r).name for r in g["rutas"]] for g in grupos]


def _texto_candidatos(grupos: List[Dict]) -> str:
    return "; ".join(" | ".join(nombres) for nombres in _nombres_candidatos(grupos)) or "ninguno"


def _descripcion_duda_estado(nombre_carpeta: str, fecha_iso: str, evaluacion: Dict) -> str:
    fecha = "/".join(reversed(fecha_iso.split("-"))) if fecha_iso != PENDIENTE else PENDIENTE
    return (f"Visita '{nombre_carpeta}': P3 estricta, {evaluacion['motivo']} "
            f"(fecha {fecha}) en INFORMES\\2.DATA PROCESADA; indica si alguno corresponde "
            f"a esta visita: {_texto_candidatos(evaluacion['candidatos'])}")


def _origen_estado(evaluacion: Dict) -> Dict:
    """Claves de estado para origen_datos_json a partir de evaluar_p3."""
    origen = {"estado": evaluacion["origen"], "regla_p3": REGLA_P3}
    if evaluacion["stp"]:
        origen["stp"] = list(evaluacion["stp"])
    if evaluacion["estado"] == ESTADO_CON_DUDAS:
        origen["stp_candidatos"] = _nombres_candidatos(evaluacion["candidatos"])
    if evaluacion["descartados"]:
        origen["stp_otra_clase"] = _nombres_candidatos(evaluacion["descartados"])
    return origen


# ---------- Dudas y hallazgos ----------

def _duda_existe(conn, visita_id: str, campo: str, categoria: str) -> bool:
    """Ya hay una duda igual (misma visita, campo y categoría), resuelta o no."""
    return conn.execute("""
        SELECT 1 FROM dudas_y_hallazgos
        WHERE visita_id = ? AND campo_afectado = ? AND categoria = ?
    """, (visita_id, campo, categoria)).fetchone() is not None


def _campos_resueltos(conn, visita_id: str) -> Set[str]:
    """Campos que Steven ya respondió en la Mesa de Dudas (duda con resuelta = 1)."""
    filas = conn.execute("""
        SELECT DISTINCT campo_afectado FROM dudas_y_hallazgos
        WHERE visita_id = ? AND resuelta = 1
    """, (visita_id,)).fetchall()
    return {f[0] for f in filas}


def _insertar_duda(conn, proyecto_id: str, visita_id: str, categoria: str,
                   campo: str, descripcion: str) -> bool:
    """Inserta la duda si no existe una igual. Devuelve True si la insertó."""
    if _duda_existe(conn, visita_id, campo, categoria):
        return False
    # Duda de la visita completa: no hay elemento (id_elemento vacío, no se inventa)
    conn.execute("""
        INSERT INTO dudas_y_hallazgos
        (proyecto_id, visita_id, id_elemento, categoria, campo_afectado, descripcion_pregunta, creado)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (proyecto_id, visita_id, "", categoria, campo, descripcion, _ahora()))
    return True


def _dudas_de_visita(visita: Dict) -> List[Tuple[str, str, str]]:
    """(categoria, campo, descripcion) que pide la visita escaneada, en orden."""
    interp = visita["interpretacion"]
    nombre = visita["nombre_carpeta"]
    dudas = []
    # 1. Campos que quedaron pendientes de verificar
    for campo in interp["campos_pendientes"]:
        motivo = interp["motivos"].get(campo, "")
        dudas.append((DUDA, campo,
                      f"Visita '{nombre}': {campo} {PENDIENTE}. {motivo}".strip()))
    # 2. Carpeta sin PDF
    if visita["sin_pdf"]:
        dudas.append((DUDA, CAMPO_ARCHIVOS, f"Visita '{nombre}': {MOTIVO_SIN_PDF}."))
    return dudas


def _campo_de_aviso(aviso: str) -> str:
    """Campo al que se refiere un aviso de interpretación de T3 (p. ej. #8: PDF contradice la clase)."""
    if "se usa la clase" in aviso:
        return CAMPO_CLASE
    if "se usa la fecha" in aviso:
        return CAMPO_FECHA
    return CAMPO_NOMBRE


def _hallazgos_de_visita(visita: Dict) -> List[Tuple[str, str, str]]:
    """Avisos de interpretación -> HALLAZGO_INTERNO (no cambian el estado)."""
    nombre = visita["nombre_carpeta"]
    return [(HALLAZGO, _campo_de_aviso(a), f"Visita '{nombre}': {a}")
            for a in visita["interpretacion"]["avisos"]]


def _insertar_lote(conn, proyecto_id: str, visita_id: str, lote, omitir: Set[str]) -> List[Dict]:
    """Inserta dudas/hallazgos nuevos (salta los campos de `omitir`). Devuelve los insertados."""
    insertadas = []
    vistos = set()
    for categoria, campo, descripcion in lote:
        if campo in omitir or (categoria, campo) in vistos:
            continue
        vistos.add((categoria, campo))
        if _insertar_duda(conn, proyecto_id, visita_id, categoria, campo, descripcion):
            insertadas.append({"visita_id": visita_id, "categoria": categoria,
                               "campo_afectado": campo, "descripcion_pregunta": descripcion})
    return insertadas


# ---------- Visitas ----------

def _origen_fecha_clase(interp: Dict, omitir: Set[str]) -> Dict:
    """Claves de fecha/clase para origen_datos_json ("carpeta" | "pdf" | None + PDFs usados).
    Los campos de `omitir` (respondidos en la Mesa de Dudas) no se tocan."""
    pdfs = interp.get("pdfs_origen") or {}
    origen = {}
    if CAMPO_FECHA not in omitir:
        origen["fecha"] = interp.get("origen_fecha")
        origen["pdfs_fecha"] = list(pdfs.get(CAMPO_FECHA) or [])
    if CAMPO_CLASE not in omitir:
        origen["clase"] = interp.get("origen_clase")
        origen["pdfs_clase"] = list(pdfs.get(CAMPO_CLASE) or [])
    return origen


def _leer_origen(fila) -> Dict:
    try:
        valor = json.loads(fila["origen_datos_json"] or "{}")
    except (TypeError, ValueError):
        return {}
    return valor if isinstance(valor, dict) else {}


def _valores_leidos(visita: Dict) -> Dict:
    """Columnas de `visitas` que salen de Dropbox (nombre de carpeta y PDFs)."""
    interp = visita["interpretacion"]
    return {
        "numero": interp["numero"],
        "nombre_carpeta": visita["nombre_carpeta"],
        "ruta_carpeta": visita["ruta_carpeta"],
        "fecha_visita": interp["fecha_iso"],  # ya es PENDIENTE si no se pudo leer
        "clase": interp["clase"],
        "clase_detalle_json": _json(interp.get("clase_detalle") or []),
        "archivos_json": _json(visita["archivos"]),
        "campos_pendientes_json": _json(interp["campos_pendientes"]),
    }


def _insertar_visita_nueva(conn, proyecto: Dict, visita: Dict, informes: List[Dict],
                           usados: Set[str]) -> Tuple[str, str, List[Dict], Dict]:
    """Inserta una visita nueva con su estado inicial. Devuelve (id, estado, dudas, salida)."""
    pid = proyecto["id"]
    valores = _valores_leidos(visita)
    visita_id = _id_visita(conn, pid, visita["nombre_carpeta"], usados)
    interp = visita["interpretacion"]

    # Fila primero (las dudas la referencian por FK); el estado se fija después
    conn.execute("""
        INSERT INTO visitas
        (id, proyecto_id, numero, nombre_carpeta, ruta_carpeta, fecha_visita, clase, estado,
         formatos_solicitados, salida_json, nota, version, actualizado,
         clase_detalle_json, archivos_json, campos_pendientes_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (visita_id, pid, valores["numero"], valores["nombre_carpeta"], valores["ruta_carpeta"],
          valores["fecha_visita"], valores["clase"], ESTADO_SIN_PROCESAR,
          _json(FORMATOS_SUPERVISION), "{}", "", 1, _ahora(),
          valores["clase_detalle_json"], valores["archivos_json"],
          valores["campos_pendientes_json"]))

    dudas = _insertar_lote(conn, pid, visita_id, _dudas_de_visita(visita), set())
    salida: Dict = {}
    origen = _origen_fecha_clase(interp, set())
    if dudas:
        estado = ESTADO_CON_DUDAS  # 1. campos pendientes / 2. sin PDF
        origen["estado"] = ORIGEN_ESTADO_DUDAS
    else:
        # 3. P3 estricta: STP ya generado con la misma fecha y la misma clase
        evaluacion = evaluar_p3(informes, interp["fecha_iso"], interp["clase"])
        estado = evaluacion["estado"]
        origen.update(_origen_estado(evaluacion))
        if estado == ESTADO_PROCESADA:
            salida = {"stp": evaluacion["stp"]}
        elif estado == ESTADO_CON_DUDAS:
            dudas += _insertar_lote(conn, pid, visita_id, [(
                DUDA, CAMPO_ESTADO, _descripcion_duda_estado(
                    visita["nombre_carpeta"], interp["fecha_iso"], evaluacion))], set())

    hallazgos = _insertar_lote(conn, pid, visita_id, _hallazgos_de_visita(visita), set())
    conn.execute("UPDATE visitas SET estado = ?, salida_json = ?, origen_datos_json = ? WHERE id = ?",
                 (estado, _json(salida), _json(origen), visita_id))
    return visita_id, estado, dudas + hallazgos, salida


def _actualizar_visita_existente(conn, proyecto: Dict, fila: sqlite3.Row,
                                 visita: Dict) -> Tuple[bool, str, List[Dict]]:
    """Actualiza solo lo leído de Dropbox. Devuelve (cambió, estado, dudas insertadas).

    No pisa fecha/clase/clase_detalle/campos_pendientes respondidos en la Mesa de Dudas.
    Nunca cambia estado ni salida_json de una visita En proceso / En revisión / Procesada.
    """
    pid = proyecto["id"]
    visita_id = fila["id"]
    valores = _valores_leidos(visita)
    resueltos = _campos_resueltos(conn, visita_id)

    nuevos = {
        "nombre_carpeta": valores["nombre_carpeta"],
        "archivos_json": valores["archivos_json"],
    }
    if _es_numero(valores["numero"]):  # nunca se escribe un número ilegible
        nuevos["numero"] = valores["numero"]
    if CAMPO_FECHA not in resueltos:
        nuevos["fecha_visita"] = valores["fecha_visita"]
    if CAMPO_CLASE not in resueltos:
        nuevos["clase"] = valores["clase"]
        nuevos["clase_detalle_json"] = valores["clase_detalle_json"]
    # Los campos ya respondidos dejan de estar pendientes
    pendientes = [c for c in visita["interpretacion"]["campos_pendientes"] if c not in resueltos]
    nuevos["campos_pendientes_json"] = _json(pendientes)

    cambios = {k: v for k, v in nuevos.items() if fila[k] != v}

    insertadas = _insertar_lote(conn, pid, visita_id, _dudas_de_visita(visita), resueltos)
    insertadas += _insertar_lote(conn, pid, visita_id, _hallazgos_de_visita(visita), set())

    # Origen de fecha/clase: se rellena/actualiza como esos campos (no si Steven los respondió)
    origen_viejo = _leer_origen(fila)
    origen = {**origen_viejo, **_origen_fecha_clase(visita["interpretacion"], resueltos)}

    estado = fila["estado"]
    if any(d["categoria"] == DUDA for d in insertadas) and estado in ESTADOS_ABIERTOS \
            and estado != ESTADO_CON_DUDAS:
        cambios["estado"] = estado = ESTADO_CON_DUDAS
        origen["estado"] = ORIGEN_ESTADO_DUDAS
    if origen != origen_viejo:
        cambios["origen_datos_json"] = _json(origen)

    if cambios:
        sets = ", ".join(f"{k} = ?" for k in cambios)
        conn.execute(f"UPDATE visitas SET {sets}, actualizado = ? WHERE id = ?",
                     (*cambios.values(), _ahora(), visita_id))
    return bool(cambios) or bool(insertadas), estado, insertadas


# ---------- Corrección única de la regla laxa de T5 (T8) ----------

def _salida_es_del_sync(salida_json: str, carpeta_informes: Path) -> bool:
    """True si salida_json tiene la forma que deja el sync: {"stp": [rutas en 2.DATA PROCESADA]}."""
    try:
        salida = json.loads(salida_json or "{}")
    except (TypeError, ValueError):
        return False
    if not isinstance(salida, dict) or set(salida) != {"stp"}:
        return False
    rutas = salida["stp"]
    if not isinstance(rutas, list) or not rutas:
        return False
    return all(isinstance(r, str) and Path(r).parent == carpeta_informes for r in rutas)


def corregir_procesadas_p3(conn, proyecto: Dict, informes: List[Dict],
                           carpeta_informes: Path) -> Dict:
    """Revisa una sola vez con la P3 estricta las visitas "Procesada" que marcó el sync.

    Entra una visita Procesada si su origen de estado es sync_p3 sin la marca regla_p3=estricta,
    o si no tiene origen de estado y su salida_json es la que deja el sync. Una Procesada con
    otro origen (p. ej. un generador de la Etapa 3) no se toca, ni una con la duda `estado`
    ya respondida por Steven. Si ya no cumple -> Con dudas + DUDA_BLOQUEANTE `estado`, la salida
    anterior se guarda en el origen y en la duda, y se audita (SYNC/CORREGIR_P3_ESTRICTA).
    Si cumple, solo se marca regla_p3=estricta. Idempotente. No hace commit.
    """
    pid = proyecto["id"]
    corregidas, confirmadas = [], []
    filas = conn.execute("SELECT * FROM visitas WHERE proyecto_id = ? AND estado = ? ORDER BY id",
                         (pid, ESTADO_PROCESADA)).fetchall()
    for fila in filas:
        origen = _leer_origen(fila)
        origen_estado = origen.get("estado")
        if origen_estado == ORIGEN_ESTADO_P3:
            if origen.get("regla_p3") == REGLA_P3:
                continue  # ya evaluada con la regla estricta
        elif origen_estado is not None:
            continue  # estado decidido fuera del sync
        elif not _salida_es_del_sync(fila["salida_json"], carpeta_informes):
            continue  # Procesada sin origen y con salida que no es del sync
        if CAMPO_ESTADO in _campos_resueltos(conn, fila["id"]):
            continue  # Steven ya decidió el estado en la Mesa de Dudas

        evaluacion = evaluar_p3(informes, fila["fecha_visita"], fila["clase"])
        if evaluacion["estado"] == ESTADO_PROCESADA:
            origen.update(_origen_estado(evaluacion))
            conn.execute("UPDATE visitas SET origen_datos_json = ? WHERE id = ?",
                         (_json(origen), fila["id"]))
            confirmadas.append(fila["id"])
            continue

        salida_anterior = json.loads(fila["salida_json"] or "{}")
        if evaluacion["estado"] == ESTADO_SIN_PROCESAR:
            # Ya no hay STP válido de su fecha: igual se pregunta, nunca se decide solo
            evaluacion = {**evaluacion, "estado": ESTADO_CON_DUDAS, "origen": ORIGEN_ESTADO_DUDAS}
        origen.update(_origen_estado(evaluacion))
        origen["correccion_p3"] = {
            "estado_anterior": fila["estado"],
            "salida_anterior": salida_anterior,
            "fecha": _ahora(),
        }
        descripcion = (_descripcion_duda_estado(fila["nombre_carpeta"], fila["fecha_visita"],
                                                evaluacion)
                       + ". Antes estaba Procesada con: "
                       + (" | ".join(Path(r).name for r in salida_anterior.get("stp", []))
                          or "sin salida"))
        dudas = _insertar_lote(conn, pid, fila["id"], [(DUDA, CAMPO_ESTADO, descripcion)], set())
        conn.execute("""UPDATE visitas SET estado = ?, salida_json = ?, origen_datos_json = ?,
                        actualizado = ? WHERE id = ?""",
                     (ESTADO_CON_DUDAS, "{}", _json(origen), _ahora(), fila["id"]))
        detalle = {
            "visita_id": fila["id"],
            "nombre_carpeta": fila["nombre_carpeta"],
            "estado_anterior": fila["estado"],
            "estado_nuevo": ESTADO_CON_DUDAS,
            "salida_anterior": salida_anterior,
            "motivo": evaluacion["motivo"],
            "candidatos": _nombres_candidatos(evaluacion["candidatos"]),
            "stp_otra_clase": _nombres_candidatos(evaluacion["descartados"]),
        }
        conn.execute("""
            INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (_ahora(), USUARIO, MODULO_AUDITORIA, ACCION_CORREGIR_P3, fila["id"], _json(detalle)))
        corregidas.append({**detalle, "dudas_creadas": dudas})
    return {"corregidas": corregidas, "confirmadas": confirmadas}


# ---------- Proyecto ----------

def _resumen_vacio(proyecto: Dict, layout: str) -> Dict:
    return {
        "id": proyecto["id"],
        "nombre": proyecto["nombre"],
        "layout": layout,
        "visitas_nuevas": 0,
        "actualizadas": 0,
        "sin_cambios": 0,
        "con_dudas": 0,
        "procesadas": 0,
        "desaparecidas": [],
        "omitidas": [],
        "avisos": [],
        "corregidas_p3": [],
        "p3_confirmadas": [],
        # Detalle adicional para la Mesa de Dudas / depuración
        "visitas": [],
        "dudas_creadas": [],
        "planos_sellados": [],
    }


def _sincronizar_proyecto(conn, proyecto: Dict) -> Dict:
    pid = proyecto["id"]
    carpeta = (proyecto["carpeta_dropbox"] or "").strip()
    if not carpeta:
        resumen = _resumen_vacio(proyecto, PENDIENTE)
        resumen["avisos"].append(f"{PENDIENTE}: el proyecto no tiene carpeta_dropbox; no se escanea")
        _auditar(conn, resumen, carpeta)
        return resumen

    escaneo = escanear_proyecto(carpeta)  # solo lectura
    resumen = _resumen_vacio(proyecto, escaneo["layout"])
    resumen["avisos"].extend(escaneo["avisos"])
    resumen["planos_sellados"] = [p["nombre"] for p in escaneo["planos_sellados"]]

    if escaneo["layout"] != LAYOUT_SUPERVISION:
        resumen["avisos"].append(
            f"layout '{escaneo['layout']}': no se sincronizan visitas de este proyecto en esta etapa")
        _auditar(conn, resumen, carpeta)
        return resumen
    if proyecto["tipo"] != TIPO_SUPERVISION:
        resumen["avisos"].append(
            f"proyecto de tipo '{proyecto['tipo']}': no se sincronizan visitas en esta etapa")
        _auditar(conn, resumen, carpeta)
        return resumen

    # Planos sellados: se actualiza si hay; si no hay, no se borra lo que estaba
    if resumen["planos_sellados"]:
        valor = "; ".join(resumen["planos_sellados"])
        if valor != (proyecto["planos_sellados"] or ""):
            conn.execute("UPDATE proyectos SET planos_sellados = ?, actualizado = ? WHERE id = ?",
                         (valor, _ahora(), pid))

    # T8: corrección única de las Procesada de la regla laxa, antes de leer las existentes
    correccion = corregir_procesadas_p3(
        conn, proyecto, escaneo["informes_procesados"], Path(carpeta) / SUBRUTA_INFORMES_PROCESADOS)
    resumen["corregidas_p3"] = correccion["corregidas"]
    resumen["p3_confirmadas"] = correccion["confirmadas"]
    corregidas_ids = {c["visita_id"] for c in correccion["corregidas"]}
    for c in correccion["corregidas"]:
        resumen["dudas_creadas"].extend(c["dudas_creadas"])

    existentes = {f["ruta_carpeta"]: f for f in conn.execute(
        "SELECT * FROM visitas WHERE proyecto_id = ?", (pid,)).fetchall()}
    usados: Set[str] = set()
    vistas: Set[str] = set()

    for visita in escaneo["visitas"]:
        ruta = visita["ruta_carpeta"]
        vistas.add(ruta)
        numero = visita["interpretacion"]["numero"]
        fila = existentes.get(ruta)

        if fila is None:
            if not _es_numero(numero):
                # Regla de Oro #1: el número no se inventa (numero es NOT NULL)
                resumen["omitidas"].append({
                    "nombre_carpeta": visita["nombre_carpeta"],
                    "ruta_carpeta": ruta,
                    "motivo": visita["interpretacion"]["motivos"].get(
                        "numero", f"número de visita {PENDIENTE}"),
                })
                continue
            visita_id, estado, dudas, salida = _insertar_visita_nueva(
                conn, proyecto, visita, escaneo["informes_procesados"], usados)
            resumen["visitas_nuevas"] += 1
            cambio = "nueva"
        else:
            visita_id = fila["id"]
            cambio_flag, estado, dudas = _actualizar_visita_existente(conn, proyecto, fila, visita)
            cambio_flag = cambio_flag or visita_id in corregidas_ids or visita_id in set(
                correccion["confirmadas"])
            salida = json.loads(conn.execute(
                "SELECT salida_json FROM visitas WHERE id = ?", (visita_id,)).fetchone()[0] or "{}")
            if cambio_flag:
                resumen["actualizadas"] += 1
                cambio = "actualizada"
            else:
                resumen["sin_cambios"] += 1
                cambio = "sin cambios"

        if estado == ESTADO_CON_DUDAS:
            resumen["con_dudas"] += 1
        elif estado == ESTADO_PROCESADA:
            resumen["procesadas"] += 1
        resumen["dudas_creadas"].extend(dudas)
        resumen["visitas"].append({
            "id": visita_id,
            "nombre_carpeta": visita["nombre_carpeta"],
            "estado": estado,
            "cambio": cambio,
            "salida": salida,
        })

    # Visitas en BD cuya carpeta ya no está: no se borran, se informan
    for ruta, fila in existentes.items():
        if ruta not in vistas:
            resumen["desaparecidas"].append({
                "id": fila["id"], "nombre_carpeta": fila["nombre_carpeta"],
                "ruta_carpeta": ruta, "estado": fila["estado"],
            })

    _auditar(conn, resumen, carpeta)
    return resumen


def _auditar(conn, resumen: Dict, carpeta: str):
    """Una fila de auditoría por proyecto sincronizado (§1.5), en la misma transacción."""
    detalle = {
        "carpeta_dropbox": carpeta,
        "layout": resumen["layout"],
        "visitas_nuevas": resumen["visitas_nuevas"],
        "actualizadas": resumen["actualizadas"],
        "sin_cambios": resumen["sin_cambios"],
        "con_dudas": resumen["con_dudas"],
        "procesadas": resumen["procesadas"],
        "dudas_creadas": len(resumen["dudas_creadas"]),
        "desaparecidas": [d["id"] for d in resumen["desaparecidas"]],
        "omitidas": [o["nombre_carpeta"] for o in resumen["omitidas"]],
        "planos_sellados": resumen["planos_sellados"],
        "n_avisos": len(resumen["avisos"]),
        "corregidas_p3": [c["visita_id"] for c in resumen["corregidas_p3"]],
        "p3_confirmadas": resumen["p3_confirmadas"],
    }
    conn.execute("""
        INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (_ahora(), USUARIO, MODULO_AUDITORIA, ACCION_AUDITORIA, resumen["id"], _json(detalle)))


def sincronizar(proyecto_id: Optional[str] = None) -> Dict:
    """Sincroniza las visitas de un proyecto (o de todos) con Dropbox.

    Lanza ProyectoNoEncontrado si `proyecto_id` no existe. Cada proyecto va en su propia
    transacción: si algo falla, ese proyecto queda como estaba.
    """
    conn = get_connection()
    conn.isolation_level = None  # transacciones explícitas
    try:
        if proyecto_id is not None:
            filas = conn.execute("SELECT * FROM proyectos WHERE id = ?", (proyecto_id,)).fetchall()
            if not filas:
                raise ProyectoNoEncontrado(proyecto_id)
        else:
            filas = conn.execute("SELECT * FROM proyectos ORDER BY id").fetchall()

        resumenes = []
        for fila in filas:
            proyecto = dict(fila)
            conn.execute("BEGIN")
            try:
                resumen = _sincronizar_proyecto(conn, proyecto)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            resumenes.append(resumen)
        return {"status": "ok", "proyectos": resumenes}
    finally:
        conn.close()
