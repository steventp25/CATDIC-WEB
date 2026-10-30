# BACKEND/visitas_obra.py
# Etapa 2 · T4v — Visitas de una obra: (a) subir el PDF de la visita o (b) conectar la obra con su carpeta
# LEVANTAMIENTO\VISITA A OBRA de Dropbox (decisión 4 de Steven, 24/10; D4 de decisiones-steven-2026-10-22).
# PLANES/etapa-2.md, T4v; CLAUDE.md §1.3, §1.5, §5.1, Regla de Oro #1.
#
# - (a) Lo subido va a la carpeta local de datos (config.obtener_datos_raiz → <obra>\visitas\<nombre §5.1>\), nunca a
#   Dropbox ni al repo, sin sobrescribir jamás (" v2") y con el sha256 de cada archivo. Si algo falla, no queda nada a
#   medias: ni carpeta ni fila. La fecha y la clase las da el usuario; si no las da, salen del nombre del PDF con la
#   misma regla P1 del sincronizador; si tampoco, quedan "pendiente de verificar" + DUDA_BLOQUEANTE. Mixta no se acepta.
# - (b) La carpeta se valida (absoluta, dentro de la raíz de Dropbox, que exista y termine en LEVANTAMIENTO\VISITA A
#   OBRA), se guarda en la obra con auditoría y se corre el sincronizador de la Etapa 1. Dropbox es SOLO LECTURA.
# - En los dos casos, al terminar se corre el lector de visitas (Etapa 3 · T3) sobre las visitas nuevas.
import getpass
import hashlib
import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pymupdf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

import config
from database import _respaldar_bd, get_connection
from obras import ErrorObra, _http, _nombre_seguro, _proyecto, _transaccion
from reglas_ingenieria import PENDIENTE, _es_fecha_ddmmaaaa_valida
from sync import lector_visita
from sync.escaner_dropbox import SUBRUTA_VISITAS
from sync.parser_visitas import (
    CAMPO_CLASE,
    CAMPO_FECHA,
    CLASE_COMPLETIVO,
    CLASE_MIXTA,
    CLASE_PARCIAL,
    combinar_datos_visita,
    interpretar_nombre_carpeta_visita,
    interpretar_nombre_pdf_visita,
)
from sync.sincronizador import (
    ESTADO_CON_DUDAS,
    ESTADO_SIN_PROCESAR,
    ESTADOS_ABIERTOS,
    FORMATOS_SUPERVISION,
    HALLAZGO,
    ORIGEN_ESTADO_DUDAS,
    TIPO_SUPERVISION,
    ProyectoNoEncontrado,
    _dudas_de_visita,
    _hallazgos_de_visita,
    _id_visita,
    _insertar_lote,
    _valores_leidos,
    sincronizar,
)

router = APIRouter()

MODULO_AUDITORIA = "OBRAS"
FUENTE_SUBIDA = "subida"      # origen_datos_json["fuente"] de una visita subida desde el programa
FUENTE_DROPBOX = "dropbox"
CLASES_SUBIDA = (CLASE_PARCIAL, CLASE_COMPLETIVO)  # T4b, decisión de Steven: Mixta no se acepta
MAX_BYTES_PDF = 300 * 1024 * 1024
MAX_BYTES_FOTO = 40 * 1024 * 1024
MAX_FOTOS = 60
EXT_FOTOS = (".jpg", ".jpeg", ".png")
LARGO_MAXIMO_TEXTO = 80
_RE_PROHIBIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _usuario() -> str:
    return getpass.getuser()


def _ahora() -> str:
    return datetime.now().isoformat()


def _json(valor) -> str:
    return json.dumps(valor, ensure_ascii=False)


def _auditar(conn, accion: str, entidad_id: str, detalle: dict, usuario: str):
    conn.execute("""
        INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (_ahora(), usuario, MODULO_AUDITORIA, accion, entidad_id, _json(detalle)))


def _dudas_abiertas(visita_ids: List[str]) -> Dict[str, List[Dict]]:
    """Dudas sin resolver de cada visita (bloqueantes y hallazgos), para el resultado y la Mesa."""
    if not visita_ids:
        return {}
    conn = get_connection()
    try:
        marcas = ", ".join("?" * len(visita_ids))
        filas = conn.execute(f"""SELECT id, visita_id, categoria, campo_afectado, descripcion_pregunta
                                 FROM dudas_y_hallazgos WHERE resuelta = 0 AND visita_id IN ({marcas})
                                 ORDER BY id""", visita_ids).fetchall()
    finally:
        conn.close()
    resultado: Dict[str, List[Dict]] = {v: [] for v in visita_ids}
    for f in filas:
        resultado[f["visita_id"]].append(dict(f))
    return resultado


def _correr_lector(visita_id: str, respaldar: bool, usuario: str) -> Dict:
    """
    Lector T3 sobre una visita. Nunca lanza: lo que falle queda en el resultado y en una DUDA_BLOQUEANTE
    `lector_visita` de la visita (el lector ya la deja si el PDF no tiene forma de visita; si falló antes, p. ej.
    porque la carpeta tiene 2 PDF, la deja esta función), y la visita abierta pasa a Con dudas: no queda sin leer
    en silencio.
    """
    try:
        r = lector_visita.cargar_visita(visita_id, respaldar=respaldar, usuario=usuario)
        return {"ok": True, "grupos": r["grupos"], "paginas": r["paginas"], "dudas_nuevas": r["dudas_nuevas"]}
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
    conn = get_connection()
    conn.isolation_level = None
    try:
        visita = conn.execute("SELECT * FROM visitas WHERE id = ?", (visita_id,)).fetchone()
        if visita is not None:
            conn.execute("BEGIN IMMEDIATE")
            try:
                if lector_visita._insertar_duda(conn, visita, "", lector_visita.CAMPO_PDF_VISITA,
                                                f"El lector de visitas no pudo leer la visita: {error}"):
                    lector_visita._marcar_con_dudas(conn, visita)
                    _auditar(conn, "LECTOR_NO_LEYO_VISITA", visita_id, {"motivo": error}, usuario)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
    finally:
        conn.close()
    return {"ok": False, "error": error}


def _estado_visitas(visita_ids: List[str]) -> Dict[str, Dict]:
    if not visita_ids:
        return {}
    conn = get_connection()
    try:
        marcas = ", ".join("?" * len(visita_ids))
        return {f["id"]: dict(f) for f in conn.execute(
            f"SELECT id, numero, nombre_carpeta, fecha_visita, clase, estado FROM visitas WHERE id IN ({marcas})",
            visita_ids)}
    finally:
        conn.close()


# ---------- (a) Subir visita ----------

def _validar_texto(valor: str, campo: str) -> str:
    texto = " ".join(str(valor or "").split()).upper()
    if not texto:
        raise ErrorObra(f"Falta {campo} de la visita.")
    if len(texto) > LARGO_MAXIMO_TEXTO:
        raise ErrorObra(f"El texto de {campo} es demasiado largo (máximo {LARGO_MAXIMO_TEXTO} caracteres).")
    if _RE_PROHIBIDOS.search(texto):
        raise ErrorObra(f'El texto de {campo} no puede llevar ninguno de estos caracteres: < > : " / \\ | ? *')
    return texto


def _validar_numero(numero) -> int:
    texto = str(numero if numero is not None else "").strip()
    if not texto.isdigit() or not 1 <= int(texto) <= 999:
        raise ErrorObra(f"El número de visita '{texto}' debe ser un entero entre 1 y 999.")
    return int(texto)


def _validar_clase(clase: str) -> Optional[str]:
    texto = " ".join(str(clase or "").split())
    if not texto:
        return None
    if texto.casefold() in (CLASE_MIXTA.casefold(), "mixto"):
        raise ErrorObra("La clase Mixta no se acepta: sube cada parte como una visita Parcial o Completivo "
                        "(decisión de Steven, T4b).")
    for c in CLASES_SUBIDA:
        if texto.casefold() == c.casefold():
            return c
    raise ErrorObra(f"La clase '{texto}' debe ser Parcial o Completivo.")


def _validar_fecha(fecha: str) -> Optional[str]:
    texto = str(fecha or "").strip()
    if not texto:
        return None
    if not _es_fecha_ddmmaaaa_valida(texto):
        raise ErrorObra(f"La fecha '{texto}' debe ser DD/MM/AAAA y existir en el calendario (ej. 28/09/2026).")
    return texto


def nombre_carpeta_visita(numero: int, elementos: str, nivel: str, clase: Optional[str],
                          fecha: Optional[str]) -> str:
    """'<N>. <ELEMENTOS> <NIVEL> <PARCIAL|COMPLETIVO> <DD-MM-AAAA>' (§5.1). Lo que no se dio no se escribe."""
    partes = [f"{numero}.", elementos, nivel]
    if clase:
        partes.append(clase.upper())
    if fecha:
        partes.append(fecha.replace("/", "-"))
    return " ".join(partes)


def _comprobar_nombre(nombre: str, numero: int, clase: Optional[str], fecha: Optional[str]):
    """El nombre armado se vuelve a leer con el parser del sincronizador: debe dar lo mismo que escribió el usuario."""
    leido = interpretar_nombre_carpeta_visita(nombre)
    fecha_iso = datetime.strptime(fecha, "%d/%m/%Y").strftime("%Y-%m-%d") if fecha else PENDIENTE
    if leido["numero"] != numero or leido["fecha_iso"] != fecha_iso or leido["clase"] != (clase or PENDIENTE):
        raise ErrorObra("Los elementos o el nivel llevan una fecha o una palabra de clase (Parcial, Completivo…) que "
                        f"confunde la lectura de la visita ('{nombre}'): escríbelas solo en sus campos.")


def _copiar_subida(subida, destino: Path, limite: int, etiqueta: str) -> Dict:
    """Copia por trozos a `destino` calculando sha256. No valida el contenido."""
    sha, total = hashlib.sha256(), 0
    flujo = subida.file
    try:
        flujo.seek(0)
    except Exception:  # noqa: BLE001 — flujo no rebobinable: se lee desde donde esté
        pass
    with open(destino, "wb") as f:
        while True:
            trozo = flujo.read(1024 * 1024)
            if not trozo:
                break
            total += len(trozo)
            if total > limite:
                raise ErrorObra(f"El archivo {etiqueta} pesa más de {limite // (1024 * 1024)} MB.", 413)
            sha.update(trozo)
            f.write(trozo)
    if total == 0:
        raise ErrorObra(f"El archivo {etiqueta} está vacío.")
    return {"sha256": sha.hexdigest(), "tamano_bytes": total}


def _carpeta_sin_sobrescribir(carpeta: Path, nombre: str) -> Path:
    """`carpeta/nombre`, o `nombre v2`, `nombre v3`… si ya existe (el nombre lleva puntos: no se usa Path.stem)."""
    destino, n = carpeta / nombre, 1
    while destino.exists():
        n += 1
        destino = carpeta / f"{nombre} v{n}"
    return destino


def _guardar_pdf(subida, carpeta: Path) -> Dict:
    nombre = _nombre_seguro(getattr(subida, "filename", "")) if subida is not None else ""
    if subida is None or not nombre:
        raise ErrorObra("Falta el PDF de la visita.")
    if not nombre.lower().endswith(".pdf"):
        raise ErrorObra(f"El archivo de la visita debe ser un PDF ('{nombre}').")
    destino = carpeta / nombre
    info = _copiar_subida(subida, destino, MAX_BYTES_PDF, f"'{nombre}'")
    try:
        with pymupdf.Document(stream=destino.read_bytes(), filetype="pdf") as doc:  # por bytes: no lo deja abierto
            if doc.needs_pass:
                raise ErrorObra(f"El PDF '{nombre}' está protegido con contraseña.")
            paginas = len(doc)
    except ErrorObra:
        raise
    except Exception as exc:  # noqa: BLE001 — cualquier PDF ilegible
        raise ErrorObra(f"El archivo '{nombre}' no es un PDF legible ({exc}).") from None
    if paginas == 0:
        raise ErrorObra(f"El PDF '{nombre}' no tiene páginas.")
    return {"nombre": nombre, "tipo": "pdf", "paginas": paginas, **info}


def _guardar_fotos(fotos, carpeta: Path) -> List[Dict]:
    fotos = [f for f in (fotos or []) if f is not None and getattr(f, "filename", "")]
    if len(fotos) > MAX_FOTOS:
        raise ErrorObra(f"Se pueden subir como máximo {MAX_FOTOS} fotos sueltas por visita.")
    if not fotos:
        return []
    carpeta.mkdir()
    guardadas = []
    for subida in fotos:
        nombre = _nombre_seguro(subida.filename)
        if not nombre.lower().endswith(EXT_FOTOS):
            raise ErrorObra(f"La foto '{nombre}' debe ser JPG o PNG.")
        destino, n = carpeta / nombre, 1
        while destino.exists():  # dos fotos con el mismo nombre: ninguna pisa a la otra
            n += 1
            destino = carpeta / f"{Path(nombre).stem} v{n}{Path(nombre).suffix}"
        info = _copiar_subida(subida, destino, MAX_BYTES_FOTO, f"'{nombre}'")
        try:
            with Image.open(destino) as imagen:
                imagen.verify()
        except (UnidentifiedImageError, OSError, SyntaxError):
            raise ErrorObra(f"La foto '{nombre}' no es una imagen legible.") from None
        guardadas.append({"nombre": destino.name, "tipo": "foto", **info})
    return guardadas


def subir_visita(proyecto_id: str, pdf, numero, elementos: str, nivel: str, fecha: str = "", clase: str = "",
                 fotos=None, usuario: Optional[str] = None, leer: bool = True) -> Dict:
    """
    Guarda la visita subida y la registra en `visitas` (fuente "subida", auditada). `pdf` y cada foto son objetos con
    `.filename` y `.file` (UploadFile). Después corre el lector T3 (si `leer`). Devuelve la visita, sus dudas y el
    resultado del lector.
    """
    usuario = usuario or _usuario()
    numero = _validar_numero(numero)
    elementos = _validar_texto(elementos, "los elementos")
    nivel = _validar_texto(nivel, "el nivel")
    fecha = _validar_fecha(fecha)
    clase = _validar_clase(clase)
    nombre = nombre_carpeta_visita(numero, elementos, nivel, clase, fecha)
    _comprobar_nombre(nombre, numero, clase, fecha)

    conn = get_connection()
    try:
        proyecto = _proyecto(conn, proyecto_id)
        if proyecto["tipo"] != TIPO_SUPERVISION:
            raise ErrorObra(f"La obra es de {proyecto['tipo']}: las visitas se suben solo en obras de Supervisión.")
        repetida = conn.execute("SELECT id, nombre_carpeta FROM visitas WHERE proyecto_id = ? AND numero = ?",
                                (proyecto_id, numero)).fetchall()
    finally:
        conn.close()
    try:
        raiz = config.obtener_datos_raiz()
    except config.CarpetaDatosInvalida as exc:
        raise ErrorObra(str(exc), 409) from None

    carpeta_visitas = raiz / proyecto_id / "visitas"
    temporal = carpeta_visitas / f".subida-{uuid.uuid4().hex[:8]}"
    temporal.mkdir(parents=True, exist_ok=False)
    final: Optional[Path] = None
    try:
        archivo_pdf = _guardar_pdf(pdf, temporal)
        archivos_fotos = _guardar_fotos(fotos, temporal / "fotos")
        conn = get_connection()
        try:
            _transaccion(conn)
            try:
                final = _carpeta_sin_sobrescribir(carpeta_visitas, nombre)
                temporal.rename(final)
                archivos = [{**archivo_pdf, "ruta": str(final / archivo_pdf["nombre"])}] + [
                    {**f, "ruta": str(final / "fotos" / f["nombre"])} for f in archivos_fotos]
                interp = combinar_datos_visita(interpretar_nombre_carpeta_visita(nombre),
                                               [interpretar_nombre_pdf_visita(archivo_pdf["nombre"])])
                visita = {"nombre_carpeta": final.name, "ruta_carpeta": str(final), "archivos": archivos,
                          "sin_pdf": False, "interpretacion": interp}
                visita_id = _id_visita(conn, proyecto_id, final.name, set())
                valores = _valores_leidos(visita)
                origen = {"fuente": FUENTE_SUBIDA,
                          "fecha": {"carpeta": "usuario"}.get(interp["origen_fecha"], interp["origen_fecha"]),
                          "pdfs_fecha": list(interp["pdfs_origen"].get(CAMPO_FECHA, [])),
                          "clase": {"carpeta": "usuario"}.get(interp["origen_clase"], interp["origen_clase"]),
                          "pdfs_clase": list(interp["pdfs_origen"].get(CAMPO_CLASE, [])),
                          "datos_usuario": {"numero": numero, "elementos": elementos, "nivel": nivel,
                                            "fecha": fecha or "", "clase": clase or ""},
                          "subida_por": usuario, "subida_en": _ahora()}
                conn.execute("""
                    INSERT INTO visitas (id, proyecto_id, numero, nombre_carpeta, ruta_carpeta, fecha_visita, clase,
                        estado, formatos_solicitados, salida_json, nota, version, actualizado, clase_detalle_json,
                        archivos_json, campos_pendientes_json, origen_datos_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', '', 1, ?, ?, ?, ?, ?)
                """, (visita_id, proyecto_id, numero, final.name, str(final), valores["fecha_visita"],
                      valores["clase"], ESTADO_SIN_PROCESAR, _json(FORMATOS_SUPERVISION), _ahora(),
                      valores["clase_detalle_json"], valores["archivos_json"], valores["campos_pendientes_json"],
                      _json(origen)))
                dudas = _insertar_lote(conn, proyecto_id, visita_id, _dudas_de_visita(visita), set())
                lote = _hallazgos_de_visita(visita)
                if repetida:  # en Terra hay dos #17 y dos #21 (Parcial y Completivo): se avisa, no se bloquea
                    lote.append((HALLAZGO, "numero", f"Visita '{final.name}': ya hay en la obra otra visita con el "
                                 f"número {numero} ({', '.join(r['nombre_carpeta'] for r in repetida)}). Revisa que sea "
                                 "una visita distinta; no se fusionan."))
                hallazgos = _insertar_lote(conn, proyecto_id, visita_id, lote, set())
                estado = ESTADO_CON_DUDAS if dudas else ESTADO_SIN_PROCESAR
                if dudas:
                    origen["estado"] = ORIGEN_ESTADO_DUDAS
                    conn.execute("UPDATE visitas SET estado = ?, origen_datos_json = ? WHERE id = ?",
                                 (estado, _json(origen), visita_id))
                _auditar(conn, "SUBIR_VISITA", visita_id, {
                    "proyecto_id": proyecto_id, "carpeta": str(final), "numero": numero, "elementos": elementos,
                    "nivel": nivel, "fecha_usuario": fecha or "", "clase_usuario": clase or "",
                    "fecha_visita": valores["fecha_visita"], "clase": valores["clase"], "estado": estado,
                    "archivos": [{k: a[k] for k in ("nombre", "tipo", "sha256", "tamano_bytes")} for a in archivos],
                    "dudas_creadas": [d["campo_afectado"] for d in dudas + hallazgos]}, usuario)
                conn.execute("COMMIT")
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                if final is not None and final.exists():
                    shutil.rmtree(final, ignore_errors=True)  # nada a medias: ni carpeta ni fila
                raise
        finally:
            conn.close()
    finally:
        shutil.rmtree(temporal, ignore_errors=True)
        try:
            carpeta_visitas.rmdir()  # solo si quedó vacía (primera subida fallida de la obra)
            carpeta_visitas.parent.rmdir()
        except OSError:
            pass

    lector = _correr_lector(visita_id, True, usuario) if leer else None
    fila = _estado_visitas([visita_id])[visita_id]
    return {"visita": {**fila, "ruta_carpeta": str(final), "archivos": archivos},
            "lector": lector, "dudas": _dudas_abiertas([visita_id])[visita_id]}


# ---------- (b) Conectar con Dropbox ----------

def validar_carpeta_visitas(ruta: str) -> Dict[str, Path]:
    """
    Valida la carpeta LEVANTAMIENTO\\VISITA A OBRA que indica el usuario (solo lectura). Devuelve
    {"visitas": carpeta de visitas, "proyecto": carpeta de la obra en Dropbox}. Lanza ErrorObra (422) si no sirve.
    """
    texto = str(ruta or "").strip().strip('"').strip()
    if not texto:
        raise ErrorObra("Indica la carpeta LEVANTAMIENTO\\VISITA A OBRA de la obra.")
    carpeta = Path(texto)
    if not carpeta.is_absolute():
        raise ErrorObra(f"La ruta '{texto}' debe ser completa (p. ej. C:\\Users\\…\\CATDIC Dropbox\\SUPERVISION\\…"
                        "\\LEVANTAMIENTO\\VISITA A OBRA).")
    dropbox = config.obtener_dropbox_raiz().resolve()
    resuelta = carpeta.resolve()
    if resuelta == dropbox or dropbox not in resuelta.parents:
        raise ErrorObra(f"La carpeta '{texto}' está fuera de la raíz de Dropbox ('{dropbox}'): solo se conectan "
                        "carpetas de Dropbox.")
    try:
        es_carpeta = resuelta.is_dir()
    except OSError:
        es_carpeta = False
    if not es_carpeta:
        raise ErrorObra(f"La carpeta '{texto}' no existe o no se puede leer desde esta computadora.")
    esperado = tuple(p.casefold() for p in SUBRUTA_VISITAS.parts)
    if tuple(p.casefold() for p in resuelta.parts[-len(esperado):]) != esperado:
        raise ErrorObra(f"La carpeta '{texto}' no tiene la forma esperada: debe ser la carpeta "
                        f"'{SUBRUTA_VISITAS}' de la obra (CLAUDE.md §5.1).")
    proyecto = resuelta.parents[len(esperado) - 1]
    if proyecto == dropbox:
        raise ErrorObra(f"'{SUBRUTA_VISITAS}' está directamente en la raíz de Dropbox: falta la carpeta de la obra.")
    return {"visitas": resuelta, "proyecto": proyecto}


def _misma_ruta(a: str, b: Path) -> bool:
    if not (a or "").strip():
        return False
    try:
        return Path(a).resolve() == b
    except OSError:
        return False


def conectar_dropbox(proyecto_id: str, carpeta_visitas: str, usuario: Optional[str] = None,
                     leer: bool = True) -> Dict:
    """
    Guarda en la obra la carpeta de Dropbox (auditado), corre el sincronizador de la Etapa 1 sobre ella y el lector T3
    sobre las visitas nuevas que siguen abiertas. Dropbox solo se lee.
    """
    usuario = usuario or _usuario()
    rutas = validar_carpeta_visitas(carpeta_visitas)
    conn = get_connection()
    try:
        proyecto = _proyecto(conn, proyecto_id)
        if proyecto["tipo"] != TIPO_SUPERVISION:
            raise ErrorObra(f"La obra es de {proyecto['tipo']}: el sincronizador lee solo visitas de Supervisión.")
        otra = [f["nombre"] for f in conn.execute("SELECT id, nombre, carpeta_dropbox FROM proyectos WHERE id != ?",
                                                  (proyecto_id,)) if _misma_ruta(f["carpeta_dropbox"], rutas["proyecto"])]
        if otra:
            raise ErrorObra(f"Esa carpeta ya está conectada a la obra '{otra[0]}': una carpeta de Dropbox no se "
                            "conecta a dos obras.", 409)
        anterior = proyecto["carpeta_dropbox"] or ""
        nueva = str(rutas["proyecto"])
        _transaccion(conn)
        try:
            if anterior != nueva:
                conn.execute("UPDATE proyectos SET carpeta_dropbox = ?, actualizado = ? WHERE id = ?",
                             (nueva, _ahora(), proyecto_id))
            _auditar(conn, "CONECTAR_DROPBOX", proyecto_id, {
                "carpeta_visitas": str(rutas["visitas"]), "carpeta_dropbox_anterior": anterior,
                "carpeta_dropbox_nueva": nueva, "cambio": anterior != nueva}, usuario)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()

    try:
        resumen = sincronizar(proyecto_id)["proyectos"][0]  # solo lectura de Dropbox
    except ProyectoNoEncontrado:
        raise ErrorObra("Proyecto no encontrado.", 404) from None

    nuevas = [v["id"] for v in resumen["visitas"] if v["cambio"] == "nueva"]
    estados = _estado_visitas(nuevas)
    lector: Dict[str, Dict] = {}
    if leer:
        a_leer = [v for v in nuevas if estados[v]["estado"] in ESTADOS_ABIERTOS]
        if a_leer:
            conn = get_connection()
            try:
                _respaldar_bd(conn, Path(config.obtener_db_path()))  # un respaldo para toda la tanda
            finally:
                conn.close()
        for v in nuevas:
            lector[v] = (_correr_lector(v, False, usuario) if v in a_leer else
                         {"ok": False, "omitida": True,
                          "error": f"la visita quedó {estados[v]['estado']}: el lector no la abre"})
    estados = _estado_visitas(nuevas)
    dudas = _dudas_abiertas(nuevas)
    return {
        "carpeta_dropbox": str(rutas["proyecto"]), "carpeta_visitas": str(rutas["visitas"]),
        "sync": {k: resumen[k] for k in ("layout", "visitas_nuevas", "actualizadas", "sin_cambios", "con_dudas",
                                         "procesadas", "omitidas", "desaparecidas", "avisos")},
        "visitas_nuevas": [{**estados[v], "lector": lector.get(v), "dudas": dudas[v]} for v in nuevas],
    }


# ---------- API ----------

class ConexionDropbox(BaseModel):
    carpeta_visitas: str


@router.post("/api/proyectos/{proyecto_id}/visitas", status_code=201)
def api_subir_visita(proyecto_id: str, pdf: Optional[UploadFile] = File(None),
                     fotos: Optional[List[UploadFile]] = File(None), numero: str = Form(""),
                     elementos: str = Form(""), nivel: str = Form(""), fecha: str = Form(""), clase: str = Form("")):
    try:
        return subir_visita(proyecto_id, pdf, numero, elementos, nivel, fecha, clase, fotos)
    except ErrorObra as exc:
        raise _http(exc)


@router.post("/api/proyectos/{proyecto_id}/dropbox")
def api_conectar_dropbox(proyecto_id: str, cuerpo: ConexionDropbox):
    try:
        return conectar_dropbox(proyecto_id, cuerpo.carpeta_visitas)
    except ErrorObra as exc:
        raise _http(exc)
