# BACKEND/obras.py
# Etapa 2 · T4n — "Nueva obra": datos generales, planos (vectorial + sellado), cambio de plano y los datos que el
# plano no da y escribe el usuario (T3n). PLANES/etapa-2.md, T4n; CLAUDE.md §1.3, §1.5, Regla de Oro #1.
#
# - El vectorial es la fuente de lectura; el sellado, la referencia legal. Que el vectorial corresponde al sellado
#   lo CERTIFICA el usuario (casilla obligatoria, auditada con usuario y fecha); el programa no lo compara.
# - Los archivos se guardan en la carpeta local de datos (config.obtener_datos_raiz), nunca en Dropbox ni en el repo,
#   sin sobrescribir jamás (sufijo " v2") y con su sha256.
# - Lo que el usuario escribe (E-n ↔ nivel, L# → tipo, emparejamiento de hojas, techos) queda `confirmado` con
#   auditoría; lo que falta queda pendiente en una DUDA_BLOQUEANTE de la obra.
import getpass
import hashlib
import json
import re
import shutil
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pymupdf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

import config
from database import get_connection
from reglas_ingenieria import PENDIENTE, _es_fecha_ddmmaaaa_valida

router = APIRouter()

TEXTO_CERTIFICACION = "Certifico que el vectorial corresponde a la versión sellada"
TIPOS_OBRA = ("Supervisión", "Levantamiento")
FORMATO_POR_TIPO = {"Supervisión": "STP-MIVED + Formularios MIVED", "Levantamiento": "HV"}
MAX_BYTES_PLANO = 300 * 1024 * 1024
TIPOS_DATO_USUARIO = ("equivalencia_nivel", "losa_tipo", "hoja_par", "techo")
DUDA_DE_TIPO = {  # tipo de dato del usuario -> campo_afectado de la duda que cierra al completarlo
    "equivalencia_nivel": "equivalencias_en_nivel",
    "losa_tipo": "losas_tipo",
    "hoja_par": "emparejamiento_hojas",
    # `techo` no cierra ninguna duda de la obra: la de cada planta repetida (T6n:nivel_hoja:pN) la abre el extractor
    # y se cierra al volver a extraer con el dato.
}
_RE_E = re.compile(r"^E-\d{1,2}$")
_RE_L = re.compile(r"^L\d{1,3}$")


class ErrorObra(Exception):
    """Error de negocio con su código HTTP (404 / 409 / 413 / 422)."""

    def __init__(self, mensaje: str, status: int = 422):
        super().__init__(mensaje)
        self.status = status


# ---------- Utilidades ----------

def _usuario() -> str:
    return getpass.getuser()


def _ahora() -> str:
    return datetime.now().isoformat()


def _slug(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-") or "obra"


def _nombre_seguro(nombre: str) -> str:
    base = Path(nombre or "").name
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", base)
    return " ".join(base.split()) or "plano.pdf"


def _auditar(conn, accion: str, entidad_id: str, detalle: dict, usuario: str):
    conn.execute("""
        INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (_ahora(), usuario, "OBRAS", accion, entidad_id, json.dumps(detalle, ensure_ascii=False)))


def _proyecto(conn, proyecto_id: str):
    fila = conn.execute("SELECT * FROM proyectos WHERE id = ?", (proyecto_id,)).fetchone()
    if fila is None:
        raise ErrorObra("Proyecto no encontrado.", 404)
    return fila


def _transaccion(conn):
    conn.isolation_level = None
    conn.execute("BEGIN IMMEDIATE")


# ---------- Crear la obra ----------

CAMPOS_OBRA = ("cliente", "supervisor", "no_solicitud", "no_licencia", "residente_obra", "direccion_obra",
               "provincia", "sector", "inicio_obra")


def crear_proyecto(datos: Dict, usuario: Optional[str] = None) -> Dict:
    """Crea la obra con sus datos generales. Los campos vacíos quedan vacíos (el generador los pone pendientes)."""
    usuario = usuario or _usuario()
    nombre = " ".join(str(datos.get("nombre") or "").split())
    if not nombre:
        raise ErrorObra("Falta el nombre de la obra.")
    tipo = datos.get("tipo") or "Supervisión"
    if tipo not in TIPOS_OBRA:
        raise ErrorObra(f"El tipo de obra debe ser uno de: {', '.join(TIPOS_OBRA)}.")
    valores = {c: " ".join(str(datos.get(c) or "").split()) for c in CAMPOS_OBRA}
    for c, v in valores.items():
        if len(v) > 300:
            raise ErrorObra(f"El campo '{c}' es demasiado largo.")
    if valores["inicio_obra"] and not _es_fecha_ddmmaaaa_valida(valores["inicio_obra"]):
        raise ErrorObra(f"El inicio de obra '{valores['inicio_obra']}' no está en formato DD/MM/AAAA.")
    conn = get_connection()
    try:
        _transaccion(conn)
        try:
            base = _slug(nombre)
            proyecto_id, n = base, 1
            while conn.execute("SELECT 1 FROM proyectos WHERE id = ?", (proyecto_id,)).fetchone():
                n += 1
                proyecto_id = f"{base}-{n}"
            columnas = ["id", "nombre", "tipo", "formato_defecto", "actualizado", *valores]
            conn.execute(f"INSERT INTO proyectos ({', '.join(columnas)}) VALUES ({', '.join('?' * len(columnas))})",
                         (proyecto_id, nombre, tipo, FORMATO_POR_TIPO[tipo], _ahora(), *valores.values()))
            _auditar(conn, "CREAR_PROYECTO", proyecto_id, {"nombre": nombre, "tipo": tipo, **valores}, usuario)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return dict(conn.execute("SELECT * FROM proyectos WHERE id = ?", (proyecto_id,)).fetchone())
    finally:
        conn.close()


# ---------- Subir / cambiar planos ----------

def _guardar_en_temporal(subida, carpeta: Path, etiqueta: str) -> Dict:
    """Copia el archivo subido a `carpeta` por trozos calculando su sha256; valida que sea un PDF legible."""
    nombre = _nombre_seguro(getattr(subida, "filename", ""))
    if not nombre.lower().endswith(".pdf"):
        raise ErrorObra(f"El archivo {etiqueta} debe ser un PDF ('{nombre}').")
    destino = carpeta / f"{etiqueta}.tmp"
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
            if total > MAX_BYTES_PLANO:
                raise ErrorObra(f"El archivo {etiqueta} pesa más de {MAX_BYTES_PLANO // (1024 * 1024)} MB.", 413)
            sha.update(trozo)
            f.write(trozo)
    if total == 0:
        raise ErrorObra(f"El archivo {etiqueta} está vacío.")
    try:
        with pymupdf.Document(stream=destino.read_bytes(), filetype="pdf") as doc:  # por bytes: no deja el archivo abierto
            if doc.needs_pass:
                raise ErrorObra(f"El PDF {etiqueta} está protegido con contraseña.")
            paginas = len(doc)
    except ErrorObra:
        raise
    except Exception as exc:  # noqa: BLE001 — cualquier PDF ilegible
        raise ErrorObra(f"El archivo {etiqueta} no es un PDF legible ({exc}).") from None
    if paginas == 0:
        raise ErrorObra(f"El PDF {etiqueta} no tiene hojas.")
    return {"nombre": nombre, "temporal": destino, "sha256": sha.hexdigest(), "bytes": total, "paginas": paginas}


def _mover_sin_sobrescribir(origen: Path, carpeta: Path, nombre: str) -> Path:
    """Mueve a `carpeta` con `nombre`; si ya existe agrega ' v2', ' v3'… Nunca sobrescribe."""
    destino, n = carpeta / nombre, 1
    while destino.exists():
        n += 1
        destino = carpeta / f"{Path(nombre).stem} v{n}{Path(nombre).suffix}"
    shutil.move(str(origen), str(destino))
    return destino


def _asegurar_duda(conn, proyecto_id: str, campo: str, descripcion: str) -> bool:
    ya = conn.execute("""
        SELECT 1 FROM dudas_y_hallazgos
        WHERE proyecto_id = ? AND visita_id IS NULL AND campo_afectado = ? AND resuelta = 0
    """, (proyecto_id, campo)).fetchone()
    if ya:
        return False
    conn.execute("""
        INSERT INTO dudas_y_hallazgos
        (proyecto_id, visita_id, id_elemento, categoria, campo_afectado, descripcion_pregunta, creado)
        VALUES (?, NULL, '(obra)', 'DUDA_BLOQUEANTE', ?, ?, ?)
    """, (proyecto_id, campo, descripcion, _ahora()))
    return True


def guardar_planos(proyecto_id: str, vectorial, sellado, certifico: bool, etiqueta_revision: str = "",
                   fecha_plano: str = "", notas: str = "", usuario: Optional[str] = None) -> Dict:
    """
    Sube el vectorial y el sellado de la obra como una revisión nueva, que queda VIGENTE; la anterior pasa a
    histórico y sus elementos de diseño se marcan 'plano cambiado: revisar'. `vectorial` y `sellado` son objetos
    con `.filename` y `.file` (UploadFile). Devuelve la fila del plano más los avisos.
    """
    usuario = usuario or _usuario()
    if not certifico:
        raise ErrorObra(f'Falta marcar la casilla "{TEXTO_CERTIFICACION}".')
    fecha_plano = (fecha_plano or "").strip()
    if fecha_plano and not _es_fecha_ddmmaaaa_valida(fecha_plano):
        raise ErrorObra(f"La fecha del plano '{fecha_plano}' no está en formato DD/MM/AAAA.")
    if vectorial is None or sellado is None:
        raise ErrorObra("Hacen falta los dos archivos: el vectorial y el sellado.")
    conn = get_connection()
    try:
        _proyecto(conn, proyecto_id)
    finally:
        conn.close()
    try:
        raiz = config.obtener_datos_raiz()
    except config.CarpetaDatosInvalida as exc:
        raise ErrorObra(str(exc), 409) from None

    carpeta_planos = raiz / proyecto_id / "planos"
    temporal = carpeta_planos / f".subida-{uuid.uuid4().hex[:8]}"
    temporal.mkdir(parents=True, exist_ok=True)
    final: Optional[Path] = None
    try:
        v = _guardar_en_temporal(vectorial, temporal, "vectorial")
        s = _guardar_en_temporal(sellado, temporal, "sellado")
        conn = get_connection()
        try:
            _transaccion(conn)
            try:
                previo = conn.execute("SELECT * FROM planos WHERE proyecto_id = ? AND estado = 'vigente'",
                                      (proyecto_id,)).fetchone()
                revision = conn.execute("SELECT COALESCE(MAX(revision), 0) + 1 FROM planos WHERE proyecto_id = ?",
                                        (proyecto_id,)).fetchone()[0]
                final = carpeta_planos / f"r{revision:02d}"
                final.mkdir(parents=True, exist_ok=False)
                ruta_v = _mover_sin_sobrescribir(v["temporal"], final, v["nombre"])
                ruta_s = _mover_sin_sobrescribir(s["temporal"], final, s["nombre"])
                ahora = _ahora()
                if previo is not None:
                    conn.execute("UPDATE planos SET estado = 'historico' WHERE id = ?", (previo["id"],))
                cur = conn.execute("""
                    INSERT INTO planos (proyecto_id, revision, etiqueta_revision, fecha_plano, estado,
                        vectorial_archivo, vectorial_ruta, vectorial_sha256, vectorial_bytes, vectorial_paginas,
                        sellado_archivo, sellado_ruta, sellado_sha256, sellado_bytes, sellado_paginas,
                        certificado_por, certificado_en, certificacion_texto, notas, subido_en)
                    VALUES (?, ?, ?, ?, 'vigente', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (proyecto_id, revision, (etiqueta_revision or "").strip(), fecha_plano,
                      ruta_v.name, str(ruta_v), v["sha256"], v["bytes"], v["paginas"],
                      ruta_s.name, str(ruta_s), s["sha256"], s["bytes"], s["paginas"],
                      usuario, ahora, TEXTO_CERTIFICACION, (notas or "").strip(), ahora))
                plano_id = cur.lastrowid
                marcados = 0
                if previo is not None:
                    marcados = conn.execute("""
                        UPDATE elementos_diseno SET revisar_motivo = 'plano cambiado: revisar'
                        WHERE proyecto_id = ? AND (plano_id IS NULL OR plano_id != ?)
                    """, (proyecto_id, plano_id)).rowcount
                dudas = []
                if _asegurar_duda(conn, proyecto_id, "emparejamiento_hojas",
                                  f"Emparejamiento de hojas vectorial ↔ sellado pendiente: el vectorial tiene "
                                  f"{v['paginas']} hojas y el sellado {s['paginas']}. Indica qué hoja del sellado corresponde "
                                  f"a cada hoja del vectorial, cuáles son las hojas de más y cuál de las plantas "
                                  f"repetidas (p. ej. dos 'DE TECHO') es cuál ({PENDIENTE})."):
                    dudas.append("emparejamiento_hojas")
                if _asegurar_duda(conn, proyecto_id, "equivalencias_en_nivel",
                                  f"Equivalencias E-n ↔ nivel pendientes (p. ej. E-1 = SOTANO S7): el plano no las trae "
                                  f"({PENDIENTE})."):
                    dudas.append("equivalencias_en_nivel")
                if _asegurar_duda(conn, proyecto_id, "losas_tipo",
                                  f"Asignación de losas L# → tipo (A/B/C) pendiente: el plano no la trae ({PENDIENTE})."):
                    dudas.append("losas_tipo")
                _auditar(conn, "SUBIR_PLANOS" if previo is None else "CAMBIAR_PLANO", proyecto_id, {
                    "plano_id": plano_id, "revision": revision, "plano_anterior_id": previo["id"] if previo else None,
                    "vectorial": {"archivo": ruta_v.name, "sha256": v["sha256"], "bytes": v["bytes"], "paginas": v["paginas"]},
                    "sellado": {"archivo": ruta_s.name, "sha256": s["sha256"], "bytes": s["bytes"], "paginas": s["paginas"]},
                    "certificacion": TEXTO_CERTIFICACION, "certificado_por": usuario, "certificado_en": ahora,
                    "fecha_plano": fecha_plano, "etiqueta_revision": (etiqueta_revision or "").strip(),
                    "elementos_marcados_para_revisar": marcados, "dudas_creadas": dudas}, usuario)
                conn.execute("COMMIT")
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                if final is not None and final.exists():
                    shutil.rmtree(final, ignore_errors=True)  # nada a medias: ni archivos ni filas
                raise
            fila = dict(conn.execute("SELECT * FROM planos WHERE id = ?", (plano_id,)).fetchone())
        finally:
            conn.close()
        fila["elementos_marcados"] = marcados
        fila["dudas_creadas"] = dudas
        fila["aviso_paginas"] = (None if v["paginas"] == s["paginas"] else
                                 f"El vectorial tiene {v['paginas']} hojas y el sellado {s['paginas']}: queda por emparejar.")
        return fila
    finally:
        shutil.rmtree(temporal, ignore_errors=True)


def listar_planos(proyecto_id: str) -> List[Dict]:
    conn = get_connection()
    try:
        _proyecto(conn, proyecto_id)
        return [dict(r) for r in conn.execute(
            "SELECT * FROM planos WHERE proyecto_id = ? ORDER BY revision DESC", (proyecto_id,))]
    finally:
        conn.close()


def planos_vigentes() -> Dict[str, Dict]:
    """Resumen del plano vigente de cada obra (para el tablero)."""
    conn = get_connection()
    try:
        filas = conn.execute("SELECT * FROM planos WHERE estado = 'vigente'").fetchall()
    finally:
        conn.close()
    return {f["proyecto_id"]: {"revision": f["revision"], "etiqueta_revision": f["etiqueta_revision"],
                               "fecha_plano": f["fecha_plano"], "vectorial_archivo": f["vectorial_archivo"],
                               "sellado_archivo": f["sellado_archivo"], "vectorial_sha256": f["vectorial_sha256"][:12],
                               "sellado_sha256": f["sellado_sha256"][:12], "certificado_por": f["certificado_por"],
                               "certificado_en": f["certificado_en"]} for f in filas}


# ---------- Datos que escribe el usuario ----------

def _validar_dato(tipo: str, clave: str, valor: str, plano) -> tuple:
    clave, valor = " ".join(str(clave).split()), " ".join(str(valor).split())
    if not clave or not valor:
        raise ErrorObra(f"Cada dato necesita clave y valor ('{clave}' = '{valor}').")
    if tipo == "equivalencia_nivel":
        clave = clave.upper()
        if not _RE_E.match(clave):
            raise ErrorObra(f"'{clave}' no es un entrepiso del plano (formato E-n, p. ej. E-1).")
    elif tipo == "losa_tipo":
        clave, valor = clave.upper(), valor.upper()
        if not _RE_L.match(clave):
            raise ErrorObra(f"'{clave}' no es una losa del plano (formato L#, p. ej. L13).")
        if valor not in ("A", "B", "C"):
            raise ErrorObra(f"El tipo de losa '{valor}' debe ser A, B o C.")
    elif tipo == "hoja_par":
        if plano is None:
            raise ErrorObra("Sube primero los planos de la obra para emparejar sus hojas.", 409)
        if not clave.isdigit() or not 1 <= int(clave) <= plano["vectorial_paginas"]:
            raise ErrorObra(f"La hoja del vectorial '{clave}' debe estar entre 1 y {plano['vectorial_paginas']}.")
        if valor.lower() != "sin pareja" and (not valor.isdigit() or not 1 <= int(valor) <= plano["sellado_paginas"]):
            raise ErrorObra(f"La hoja del sellado '{valor}' debe estar entre 1 y {plano['sellado_paginas']}, "
                            f"o ser 'sin pareja'.")
        valor = "sin pareja" if valor.lower() == "sin pareja" else str(int(valor))
        clave = str(int(clave))
    elif tipo == "techo":
        # página del vectorial vigente → nivel de esa planta (plantas con el mismo título impreso en varias hojas)
        if plano is None:
            raise ErrorObra("Sube primero los planos de la obra para decir qué nivel es cada planta.", 409)
        if not clave.isdigit() or not 1 <= int(clave) <= plano["vectorial_paginas"]:
            raise ErrorObra(f"La página del vectorial '{clave}' debe estar entre 1 y {plano['vectorial_paginas']}.")
        if len(valor) > 60:
            raise ErrorObra("El texto de la planta de techo es demasiado largo.")
        clave = str(int(clave))
    return clave, valor


def guardar_datos_usuario(proyecto_id: str, tipo: str, items: List[Dict], completo: bool = False,
                          usuario: Optional[str] = None) -> Dict:
    """
    Guarda como `confirmado` (la fuente es el usuario) los datos de un tipo, con una fila de auditoría con el valor
    anterior y el nuevo de cada uno. Con `completo=True` el usuario declara que ya dio todos los de ese tipo y se
    cierra la DUDA_BLOQUEANTE correspondiente; si no, la duda sigue abierta (lo que falta queda pendiente).
    """
    usuario = usuario or _usuario()
    if tipo not in TIPOS_DATO_USUARIO:
        raise ErrorObra(f"El tipo de dato debe ser uno de: {', '.join(TIPOS_DATO_USUARIO)}.")
    if not items:
        raise ErrorObra("No hay datos que guardar.")
    conn = get_connection()
    try:
        _proyecto(conn, proyecto_id)
        plano = conn.execute("SELECT * FROM planos WHERE proyecto_id = ? AND estado = 'vigente'",
                             (proyecto_id,)).fetchone()
        limpios = [_validar_dato(tipo, i.get("clave", ""), i.get("valor", ""), plano) for i in items]
        _transaccion(conn)
        try:
            ahora, cambios = _ahora(), []
            for clave, valor in limpios:
                previo = conn.execute("SELECT valor FROM obra_datos_usuario WHERE proyecto_id = ? AND tipo = ? AND clave = ?",
                                      (proyecto_id, tipo, clave)).fetchone()
                conn.execute("""
                    INSERT INTO obra_datos_usuario (proyecto_id, tipo, clave, valor, estado, fuente, actualizado_por, actualizado)
                    VALUES (?, ?, ?, ?, 'confirmado', 'usuario', ?, ?)
                    ON CONFLICT(proyecto_id, tipo, clave) DO UPDATE SET valor = excluded.valor, estado = 'confirmado',
                        actualizado_por = excluded.actualizado_por, actualizado = excluded.actualizado
                """, (proyecto_id, tipo, clave, valor, usuario, ahora))
                cambios.append({"clave": clave, "anterior": previo["valor"] if previo else None, "nuevo": valor})
            cerradas = 0
            campo = DUDA_DE_TIPO.get(tipo)
            if completo and campo:
                cerradas = conn.execute("""
                    UPDATE dudas_y_hallazgos SET resuelta = 1, respuesta_usuario = ?, resuelto_en = ?
                    WHERE proyecto_id = ? AND visita_id IS NULL AND campo_afectado = ? AND resuelta = 0
                """, (f"Confirmado por {usuario}: {len(limpios)} datos en esta entrega", ahora, proyecto_id, campo)).rowcount
            _auditar(conn, "GUARDAR_DATOS_OBRA", proyecto_id,
                     {"tipo": tipo, "datos": cambios, "completo": completo, "dudas_cerradas": cerradas}, usuario)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return {"tipo": tipo, "guardados": len(cambios), "completo": completo, "dudas_cerradas": cerradas}


def listar_datos_obra(proyecto_id: str) -> Dict:
    conn = get_connection()
    try:
        _proyecto(conn, proyecto_id)
        filas = [dict(r) for r in conn.execute(
            "SELECT tipo, clave, valor, estado, fuente, actualizado_por, actualizado FROM obra_datos_usuario "
            "WHERE proyecto_id = ? ORDER BY tipo, id", (proyecto_id,))]
        dudas = [dict(r) for r in conn.execute(
            "SELECT id, campo_afectado, descripcion_pregunta, resuelta FROM dudas_y_hallazgos "
            "WHERE proyecto_id = ? AND visita_id IS NULL AND resuelta = 0", (proyecto_id,))]
    finally:
        conn.close()
    por_tipo = {t: [f for f in filas if f["tipo"] == t] for t in TIPOS_DATO_USUARIO}
    return {"datos": por_tipo, "dudas_abiertas": dudas}


# ---------- API ----------

class ProyectoNuevo(BaseModel):
    nombre: str
    tipo: Optional[str] = None
    cliente: Optional[str] = None
    supervisor: Optional[str] = None
    no_solicitud: Optional[str] = None
    no_licencia: Optional[str] = None
    residente_obra: Optional[str] = None
    direccion_obra: Optional[str] = None
    provincia: Optional[str] = None
    sector: Optional[str] = None
    inicio_obra: Optional[str] = None


class DatoUsuario(BaseModel):
    clave: str
    valor: str


class DatosObra(BaseModel):
    tipo: str
    items: List[DatoUsuario]
    completo: bool = False


def _http(exc: ErrorObra) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=str(exc))


@router.post("/api/proyectos", status_code=201)
def api_crear_proyecto(cuerpo: ProyectoNuevo):
    try:
        return {"proyecto": crear_proyecto(cuerpo.model_dump())}
    except ErrorObra as exc:
        raise _http(exc)


@router.post("/api/proyectos/{proyecto_id}/planos", status_code=201)
def api_subir_planos(proyecto_id: str, vectorial: UploadFile = File(...), sellado: UploadFile = File(...),
                     certifico: str = Form("false"), etiqueta_revision: str = Form(""), fecha_plano: str = Form(""),
                     notas: str = Form("")):
    try:
        return {"plano": guardar_planos(proyecto_id, vectorial, sellado,
                                        certifico.strip().lower() in ("true", "1", "on", "si", "sí"),
                                        etiqueta_revision, fecha_plano, notas)}
    except ErrorObra as exc:
        raise _http(exc)


@router.get("/api/proyectos/{proyecto_id}/planos")
def api_listar_planos(proyecto_id: str):
    try:
        return {"planos": listar_planos(proyecto_id)}
    except ErrorObra as exc:
        raise _http(exc)


@router.put("/api/proyectos/{proyecto_id}/datos-obra")
def api_guardar_datos_obra(proyecto_id: str, cuerpo: DatosObra):
    try:
        return guardar_datos_usuario(proyecto_id, cuerpo.tipo, [i.model_dump() for i in cuerpo.items], cuerpo.completo)
    except ErrorObra as exc:
        raise _http(exc)


@router.get("/api/proyectos/{proyecto_id}/datos-obra")
def api_listar_datos_obra(proyecto_id: str):
    try:
        return listar_datos_obra(proyecto_id)
    except ErrorObra as exc:
        raise _http(exc)
