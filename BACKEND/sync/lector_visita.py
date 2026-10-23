# BACKEND/sync/lector_visita.py
# Etapa 3 · T3 — Lector del PDF de visita -> `elementos_visita` (Capa 2, CLAUDE.md §4.1).
#
# Estructura que encontró el reconocimiento de T2 (PLANES/etapa-3-reconocimiento-visita.md):
# una foto por página; debajo de la foto, la etiqueta en un span de 12 pt en negrita, luego
# "Creado el: ..." (10 pt) y, a veces, una nota libre (10 pt regular). El orden lo da la página.
#
# Regla de Oro #1: la etiqueta es texto libre del técnico y se guarda LITERAL. Solo se llenan
# id/tipo/ejes cuando el texto lo da sin interpretar; todo lo demás queda "pendiente de verificar"
# y genera UNA DUDA_BLOQUEANTE por grupo (no una por campo). La prima ’ (U+2019) y mc/MC no se
# normalizan (lo tiene que aprobar Steven). Nunca se sacan datos de diseño de las fotos (§4.1).
# Dropbox es SOLO LECTURA: el PDF se abre sin guardarlo y las fotos reducidas van a una caché local.
import getpass
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pymupdf
from PIL import Image, ImageOps

import config
from database import get_connection, _respaldar_bd
from sync.sincronizador import ESTADO_CON_DUDAS, ESTADOS_ABIERTOS
from reglas_ingenieria import (
    PENDIENTE,
    agrupar_log_fotografico_visita,
    formatear_campo_ejes,
    interpretar_eje_de_visita,
)

ENV_CACHE_RAIZ = "CATDIC_CACHE_RAIZ"
MODULO_AUDITORIA = "LECTOR_VISITA"
ACCION_CARGAR = "CARGAR_VISITA"
ACCION_RECHAZAR = "RECHAZAR_PDF_VISITA"
DUDA = "DUDA_BLOQUEANTE"
CAMPO_PDF_VISITA = "lector_visita"
ORIGEN_ESTADO_LECTOR = "lector_visita"  # origen_datos_json["estado"] cuando el lector abre dudas
LADO_MAXIMO_PX = 1000   # §5.2
CALIDAD_JPG = 72        # §5.2
TAM_ETIQUETA_PT = 11.5  # la etiqueta mide 12 pt; "Creado el:" y las notas, 10 pt
_RE_CREADO = re.compile(r"^\s*Creado el:\s*(.*)$")
_RE_NIVEL = re.compile(r"\bS-\d+\b", re.IGNORECASE)
_RE_ID = re.compile(r"[A-Z]{1,3}\d{1,3}")
_RE_EJE_UNA_LETRA = re.compile(r"[A-ZÑ]'?\d+'?|\d+'?[A-ZÑ]'?", re.IGNORECASE)


# ---------- Rutas ----------

def obtener_cache_raiz() -> Path:
    """Caché de fotos reducidas (D1): CATDIC_CACHE_RAIZ o <carpeta del usuario>\\CATDIC-CACHE."""
    valor = os.environ.get(ENV_CACHE_RAIZ, "").strip()
    return Path(valor) if valor else Path.home() / "CATDIC-CACHE"


def _dentro_de(ruta: Path, carpeta: Path) -> bool:
    try:
        ruta.resolve().relative_to(carpeta.resolve())
        return True
    except ValueError:
        return False


def _validar_cache(cache_raiz: Path) -> Path:
    dropbox = config.obtener_dropbox_raiz()
    if _dentro_de(cache_raiz, dropbox):
        raise ValueError(f"La caché '{cache_raiz}' está dentro de Dropbox ('{dropbox}'): las fotos "
                         "reducidas nunca se escriben en Dropbox.")
    return cache_raiz


# ---------- Lectura del PDF (solo lectura) ----------

def _foto_principal(pagina) -> Optional[dict]:
    """La imagen de mayor tamaño de la página (el logo del generador se ignora)."""
    imagenes = pagina.get_image_info()
    return max(imagenes, key=lambda i: i["width"] * i["height"]) if imagenes else None


def _leer_texto_pagina(pagina, foto_bbox) -> Dict:
    """
    Etiqueta (span 12 pt negrita), hora y nota libre del texto de la ZONA de la foto: debajo de ella
    o a su derecha (las fotos apaisadas de la #18 llevan 'Creado el:' al lado). Quedan fuera la
    cabecera (sobre la foto), el pie y la numeración '(n)'. 'Creado' y 'el:' pueden venir en líneas
    distintas y la hora va en su propia línea: se toma por su posición vertical, no por la línea.
    """
    x0f, y0f, x1f, y1f = foto_bbox
    pie = pagina.rect.height - 100  # "Id. de doc." / "página N de M" / "Generado por": no son contenido
    tokens = []
    for bloque in pagina.get_text("dict")["blocks"]:
        if bloque["type"] != 0:
            continue
        for linea in bloque["lines"]:
            lx0, ly0 = linea["bbox"][0], linea["bbox"][1]
            debajo = ly0 >= y1f - 1
            a_la_derecha = lx0 >= x1f - 1 and ly0 >= y0f - 1
            if not (debajo or a_la_derecha) or ly0 >= pie:
                continue
            for s in linea["spans"]:
                if s["text"].strip():
                    tokens.append({"texto": s["text"], "tam": s["size"], "y": s["bbox"][1],
                                   "negrita": "bold" in s["font"].lower() or bool(s["flags"] & 16)})
    etiqueta, hora, nota = [], [], []
    marcador_y = None
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if marcador_y is None:
            m = _RE_CREADO.match(t["texto"])
            partido = (t["texto"].strip() == "Creado" and i + 1 < len(tokens)
                       and tokens[i + 1]["texto"].strip().startswith("el:"))
            if m:
                marcador_y = t["y"]
                if m.group(1).strip():
                    hora.append(m.group(1).strip())
            elif partido:  # 'Creado' y 'el:' en líneas distintas
                marcador_y = t["y"]
                resto = tokens[i + 1]["texto"].strip()[3:].strip()
                if resto:
                    hora.append(resto)
                i += 1
            elif t["tam"] >= TAM_ETIQUETA_PT and t["negrita"]:
                etiqueta.append(t["texto"].strip())
        elif abs(t["y"] - marcador_y) <= 3:  # la hora comparte la altura de 'Creado el:'
            hora.append(t["texto"].strip())
        else:
            nota.append(t["texto"].strip())
        i += 1
    return {"etiqueta": " ".join(etiqueta).strip(), "nota": " ".join(nota).strip(),
            "hora": " ".join(hora).strip() or None, "tiene_creado": marcador_y is not None}


def leer_pdf_visita(ruta_pdf: Path) -> List[Dict]:
    """
    Lista de páginas de la visita en el orden del PDF:
    [{pagina, etiqueta, nota, hora, foto_bbox}]. Lanza ValueError si no tiene estructura de visita
    (alguna página sin foto o sin 'Creado el:'): no se carga nada a medias ni se descarta nada.
    """
    paginas, anomalas = [], []
    with pymupdf.open(str(ruta_pdf)) as doc:  # solo lectura: nunca se guarda
        if doc.page_count == 0:
            raise ValueError(f"'{Path(ruta_pdf).name}' no tiene páginas: no es un PDF de visita.")
        for n, pagina in enumerate(doc, start=1):
            foto = _foto_principal(pagina)
            if foto is None:
                anomalas.append((n, "sin foto"))
                continue
            texto = _leer_texto_pagina(pagina, foto["bbox"])
            if not texto["tiene_creado"]:
                anomalas.append((n, "sin 'Creado el:'"))
                continue
            paginas.append({"pagina": n, "foto_bbox": tuple(foto["bbox"]), **{
                k: texto[k] for k in ("etiqueta", "nota", "hora")}})
    if anomalas:
        detalle = ", ".join(f"p. {n} {motivo}" for n, motivo in anomalas[:10])
        raise ValueError(f"'{Path(ruta_pdf).name}' no tiene la estructura de una visita "
                         f"(una foto y 'Creado el:' por página): {detalle}.")
    return paginas


def _guardar_foto_en_cache(ruta_pdf: Path, pagina: int, bbox, destino: Path) -> None:
    """Rasteriza la foto tal como se ve en la página (respeta su orientación), máx. 1000×1000, JPG q72."""
    ancho_pt, alto_pt = bbox[2] - bbox[0], bbox[3] - bbox[1]
    dpi = int(max(36, min(300, round(72 * LADO_MAXIMO_PX / max(ancho_pt, alto_pt)))))
    with pymupdf.open(str(ruta_pdf)) as doc:
        pix = doc[pagina - 1].get_pixmap(dpi=dpi, clip=pymupdf.Rect(*bbox), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img = ImageOps.exif_transpose(img)
    img.thumbnail((LADO_MAXIMO_PX, LADO_MAXIMO_PX), Image.LANCZOS)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, format="JPEG", quality=CALIDAD_JPG)


# ---------- Interpretación sin adivinar ----------

def nivel_de_carpeta(nombre_carpeta: str) -> str:
    """Nivel de la carpeta solo si trae exactamente uno (p. ej. 'S-4'); si no, pendiente."""
    niveles = {m.upper() for m in _RE_NIVEL.findall(nombre_carpeta or "")}
    return niveles.pop() if len(niveles) == 1 else PENDIENTE


def interpretar_etiqueta(etiqueta: str) -> Dict[str, str]:
    """
    Solo lo que el texto da sin interpretar. Devuelve id_elemento, tipo_elemento y ejes.
    - 'A1' o '1A' (una sola letra, prima recta opcional) -> ejes 'EJE A-1' vía interpretar_eje_de_visita.
    - '<ID> <cruce>' con ID de la forma letras+número (C1, Z4, L9) -> id y ejes.
    - Antes de interpretar se normaliza (decisión de Steven): prima ’ -> ' y mayúsculas (c1 a4 -> C1, EJE A-4).
    - Cualquier otra cosa (Mh4, Tramo D-B, Pórtico eje 3, L5, Mc eje A’ Tramo 3-4’...) queda pendiente.
      El tipo nunca se deduce.
    """
    resultado = {"id_elemento": PENDIENTE, "tipo_elemento": PENDIENTE, "ejes": PENDIENTE}
    # Normalización aprobada por Steven (23/10/2026): prima ’ -> ' y mayúsculas, solo para interpretar.
    # etiqueta_original se guarda siempre literal.
    tokens = (etiqueta or "").replace("’", "'").upper().split()

    def _ejes(token: str) -> Optional[str]:
        if not _RE_EJE_UNA_LETRA.fullmatch(token):  # 'Mh4' tiene dos letras: no es un cruce de ejes
            return None
        cruce = interpretar_eje_de_visita(token)
        if cruce == PENDIENTE:
            return None
        valor = formatear_campo_ejes("cruce_puntual", eje_letra_1=cruce[0], eje_num_1=cruce[1])
        return None if valor == PENDIENTE else valor

    if len(tokens) == 1:
        ejes = _ejes(tokens[0])
        if ejes:
            resultado["ejes"] = ejes
    elif len(tokens) == 2 and _RE_ID.fullmatch(tokens[0]):
        ejes = _ejes(tokens[1])
        if ejes:
            resultado.update(id_elemento=tokens[0], ejes=ejes)
    return resultado


# ---------- Armado de grupos ----------

def armar_grupos(paginas: List[Dict], nombre_carpeta: str) -> List[Dict]:
    """
    Agrupa con agrupar_log_fotografico_visita (M1: una etiqueta abre el grupo, las siguientes sin
    etiqueta le pertenecen). De agrupar solo se usa la estructura: el id_sugerido y la deducción de
    pórtico por orden NO se usan. orden_en_log = página que abre el grupo.
    """
    por_pagina = {f"p{p['pagina']:03d}": p for p in paginas}
    log = [{"archivo": f"p{p['pagina']:03d}", "etiqueta_elemento": p["etiqueta"], "leyenda": ""}
           for p in paginas]
    nivel = nivel_de_carpeta(nombre_carpeta)
    grupos = []
    for g in agrupar_log_fotografico_visita(log):
        fotos = [por_pagina[a] for a in g["fotos"]]
        etiqueta = fotos[0]["etiqueta"]  # literal; etiqueta_apertura del motor puede venir reescrita
        datos = interpretar_etiqueta(etiqueta)
        grupos.append({
            "orden_en_log": fotos[0]["pagina"], "etiqueta_original": etiqueta,
            "nivel": nivel, **datos, "fotos": fotos,
            "reconocido": datos["id_elemento"] != PENDIENTE and datos["ejes"] != PENDIENTE,
        })
    return grupos


def _texto_duda(grupo: Dict) -> str:
    primera, ultima = grupo["fotos"][0]["pagina"], grupo["fotos"][-1]["pagina"]
    una = primera == ultima
    paginas = f"página {primera}" if una else f"páginas {primera} a {ultima}"
    if not grupo["etiqueta_original"]:
        return (f"Las primeras fotos de la visita ({paginas}) no tienen etiqueta: ¿a qué elemento "
                "pertenecen? No se asignan por adivinanza.")
    return (f"{'Foto de la' if una else 'Fotos de las'} {paginas} con la etiqueta literal "
            f"'{grupo['etiqueta_original']}': ¿abre un elemento nuevo (tipo, ID, ejes) o pertenece al anterior?")


# ---------- Carga a la BD ----------

def _ahora() -> str:
    return datetime.now().isoformat()


def _json(valor) -> str:
    return json.dumps(valor, ensure_ascii=False)


def _pdf_de_la_visita(visita, ruta_pdf: Optional[Path]) -> Path:
    if ruta_pdf is not None:
        return Path(ruta_pdf)
    archivos = json.loads(visita["archivos_json"] or "[]")
    pdfs = [a for a in archivos if str(a.get("nombre", "")).lower().endswith(".pdf")]
    if len(pdfs) != 1:
        raise ValueError(f"La visita tiene {len(pdfs)} PDF; indica cuál leer (no se elige uno solo).")
    return Path(pdfs[0].get("ruta") or Path(visita["ruta_carpeta"]) / pdfs[0]["nombre"])


def _duda_existe(conn, visita_id: str, campo: str) -> bool:
    return conn.execute("""SELECT 1 FROM dudas_y_hallazgos WHERE visita_id = ? AND campo_afectado = ?
                           AND categoria = ?""", (visita_id, campo, DUDA)).fetchone() is not None


def _insertar_duda(conn, visita, id_elemento: str, campo: str, texto: str) -> bool:
    if _duda_existe(conn, visita["id"], campo):
        return False
    conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria,
                    campo_afectado, descripcion_pregunta, creado) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (visita["proyecto_id"], visita["id"], id_elemento, DUDA, campo, texto, _ahora()))
    return True


def _marcar_con_dudas(conn, visita) -> Optional[str]:
    """
    Misma regla que el sync: una visita 'Sin procesar' o 'En cola' con bloqueantes abiertas pasa a
    'Con dudas' (T10 no debe tomarla para procesar). Las avanzadas (En proceso, En revisión,
    Procesada) nunca se tocan. Devuelve el estado nuevo, o None si no cambió.
    """
    if visita["estado"] not in ESTADOS_ABIERTOS or visita["estado"] == ESTADO_CON_DUDAS:
        return None
    abiertas = conn.execute("""SELECT COUNT(*) FROM dudas_y_hallazgos WHERE visita_id = ?
                               AND categoria = ? AND resuelta = 0""", (visita["id"], DUDA)).fetchone()[0]
    if not abiertas:
        return None
    try:
        origen = json.loads(visita["origen_datos_json"] or "{}")
        origen = origen if isinstance(origen, dict) else {}
    except ValueError:
        origen = {}
    origen["estado"] = ORIGEN_ESTADO_LECTOR
    conn.execute("UPDATE visitas SET estado = ?, origen_datos_json = ?, actualizado = ? WHERE id = ?",
                 (ESTADO_CON_DUDAS, _json(origen), _ahora(), visita["id"]))
    return ESTADO_CON_DUDAS


def cargar_visita(visita_id: str, ruta_pdf: Optional[Path] = None, usuario: Optional[str] = None,
                  respaldar: bool = True) -> Dict:
    """
    Lee el PDF de la visita y carga sus elementos a `elementos_visita`. Idempotente por
    (visita_id, orden_en_log): una segunda corrida no duplica filas ni dudas.
    - respaldar=True (por defecto) saca un respaldo de la BD antes de escribir, también si el PDF se rechaza.
    - Un PDF sin estructura de visita no carga nada: crea una duda y lanza ValueError.
    """
    usuario = usuario or getpass.getuser()
    cache_raiz = _validar_cache(obtener_cache_raiz())
    conn = get_connection()
    conn.isolation_level = None
    try:
        visita = conn.execute("SELECT * FROM visitas WHERE id = ?", (visita_id,)).fetchone()
        if visita is None:
            raise LookupError(f"No existe la visita '{visita_id}'.")
        pdf = _pdf_de_la_visita(visita, ruta_pdf)
        try:
            paginas = leer_pdf_visita(pdf)
        except ValueError as e:
            if respaldar:
                _respaldar_bd(conn, Path(config.obtener_db_path()))
            conn.execute("BEGIN")
            _insertar_duda(conn, visita, "", CAMPO_PDF_VISITA, str(e))
            _marcar_con_dudas(conn, visita)
            conn.execute("""INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
                            VALUES (?, ?, ?, ?, ?, ?)""", (_ahora(), usuario, MODULO_AUDITORIA, ACCION_RECHAZAR,
                                                           visita_id, _json({"pdf": str(pdf), "motivo": str(e)})))
            conn.execute("COMMIT")
            raise
        grupos = armar_grupos(paginas, visita["nombre_carpeta"])

        respaldo = _respaldar_bd(conn, Path(config.obtener_db_path())) if respaldar else None
        carpeta_cache = cache_raiz / visita["proyecto_id"] / visita["id"]
        for p in paginas:  # primero la caché (sin tocar la BD); lo ya generado no se rehace
            destino = carpeta_cache / f"p{p['pagina']:03d}.jpg"
            if not destino.exists():
                _guardar_foto_en_cache(pdf, p["pagina"], p["foto_bbox"], destino)

        nuevas = actualizadas = sin_cambios = dudas_nuevas = 0
        conn.execute("BEGIN")
        try:
            for g in grupos:
                fotos_json = _json([{
                    "pagina": f["pagina"], "etiqueta": f["etiqueta"], "nota": f["nota"], "hora": f["hora"],
                    "cache": f"{visita['proyecto_id']}/{visita['id']}/p{f['pagina']:03d}.jpg",
                } for f in g["fotos"]])
                valores = (g["etiqueta_original"], g["id_elemento"], g["tipo_elemento"], g["nivel"],
                           g["ejes"], fotos_json)
                uid = f"{visita_id}-{g['orden_en_log']:03d}"
                fila = conn.execute("""SELECT etiqueta_original, id_elemento, tipo_elemento, nivel, ejes,
                                       fotos_json FROM elementos_visita WHERE visita_id = ? AND orden_en_log = ?""",
                                    (visita_id, g["orden_en_log"])).fetchone()
                if fila is None:
                    conn.execute("""INSERT INTO elementos_visita (uid, visita_id, orden_en_log, etiqueta_original,
                                    id_elemento, tipo_elemento, nivel, ejes, fotos_json)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (uid, visita_id, g["orden_en_log"], *valores))
                    nuevas += 1
                elif tuple(fila) != valores:
                    conn.execute("""UPDATE elementos_visita SET etiqueta_original = ?, id_elemento = ?,
                                    tipo_elemento = ?, nivel = ?, ejes = ?, fotos_json = ?
                                    WHERE visita_id = ? AND orden_en_log = ?""", (*valores, visita_id, g["orden_en_log"]))
                    actualizadas += 1
                else:
                    sin_cambios += 1
                if not g["reconocido"]:  # UNA duda por grupo no reconocido
                    if _insertar_duda(conn, visita, g["etiqueta_original"] or "(sin etiqueta)",
                                      f"elemento_visita:p{g['orden_en_log']:03d}", _texto_duda(g)):
                        dudas_nuevas += 1
            estado_nuevo = _marcar_con_dudas(conn, visita)
            detalle = {"pdf": str(pdf), "paginas": len(paginas), "grupos": len(grupos),
                       "estado_anterior": visita["estado"], "estado_nuevo": estado_nuevo or visita["estado"],
                       "filas_nuevas": nuevas, "filas_actualizadas": actualizadas, "sin_cambios": sin_cambios,
                       "dudas_nuevas": dudas_nuevas, "cache": str(carpeta_cache),
                       "respaldo": respaldo.name if respaldo else None}
            conn.execute("""INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
                            VALUES (?, ?, ?, ?, ?, ?)""", (_ahora(), usuario, MODULO_AUDITORIA, ACCION_CARGAR,
                                                           visita_id, _json(detalle)))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return {**detalle, "grupos_detalle": [
            {"orden_en_log": g["orden_en_log"], "etiqueta_original": g["etiqueta_original"],
             "fotos": len(g["fotos"]), "id_elemento": g["id_elemento"], "ejes": g["ejes"]} for g in grupos]}
    finally:
        conn.close()
