# backend/pedidos.py
# Fundación F2 (contrato §2, §3 y §5): API mínima del pedido (el «trabajo» de la Fundación) para probar las
# ediciones simultáneas. Toda mutación lleva `version`: si otro la cambió antes, 409 y no se escribe nada. El
# cambio, su versión y su fila de auditoría van en la misma transacción.
#
# Fuentes: en F2 solo revisiones de plano (planos.id). Las versiones de documento (documento_version_id) llegan en F3.
# Antes de pasar a `preparado` o `aprobado` se comprueba que los dos archivos de cada plano fuente siguen siendo los
# de su sha256; si no, se detiene con su motivo y se audita (contrato §2.3). La copia conservada es de F3.
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import config
from database import get_connection
from identidad import contexto
from identidad.guardia import exigir_en_obra
from identidad.permisos import PREPARAR, REVISAR_AUTORIZAR

router = APIRouter()
MODULO = "PEDIDOS"

# Transición -> función que la autoriza. Preparar y autorizar son actos distintos, cada uno con su función.
TRANSICIONES = {
    ("borrador", "solicitado"): PREPARAR,
    ("solicitado", "preparado"): PREPARAR,
    ("preparado", "en_revision"): PREPARAR,
    ("en_revision", "corregir"): REVISAR_AUTORIZAR,
    ("corregir", "en_revision"): PREPARAR,
    ("en_revision", "aprobado"): REVISAR_AUTORIZAR,
}
ACCION_ESTADO = {"solicitado": "SOLICITAR", "preparado": "PREPARAR", "en_revision": "ENVIAR_A_REVISION",
                 "corregir": "PEDIR_CORRECCION", "aprobado": "APROBAR"}
COMPRUEBAN_FUENTES = {"preparado", "aprobado"}


def _ahora() -> str:
    return datetime.now().isoformat()


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _auditar(conn, accion: str, pedido_id, detalle: dict) -> None:
    u = contexto.actual()
    conn.execute("""INSERT INTO auditoria (fecha_hora, usuario, usuario_id, modulo, accion, entidad_id, detalle_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (_ahora(), u.usuario, u.id, MODULO, accion, str(pedido_id), _json(detalle)))


def _transaccion(conn):
    conn.isolation_level = None
    conn.execute("BEGIN IMMEDIATE")


def _leer(conn, pedido_id: int) -> Optional[Dict]:
    f = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    if f is None:
        return None
    p = dict(f)
    p["progreso"] = json.loads(p.pop("progreso_json") or "{}")
    p["fuentes"] = [dict(r) for r in conn.execute(
        """SELECT pf.plano_id, pf.documento_version_id, pf.seleccionado_por, pf.seleccionado_en, pl.revision,
                  pl.vectorial_sha256, pl.sellado_sha256 FROM pedido_fuentes pf
           LEFT JOIN planos pl ON pl.id = pf.plano_id WHERE pf.pedido_id = ? ORDER BY pf.id""", (pedido_id,))]
    return p


def _responsable_valido(conn, obra_id: str, usuario_id: int) -> None:
    f = conn.execute("""SELECT 1 FROM membresias m JOIN usuarios u ON u.id = m.usuario_id
                        WHERE m.usuario_id = ? AND m.obra_id = ? AND u.activo = 1""", (usuario_id, obra_id)).fetchone()
    if f is None:
        raise HTTPException(status_code=422, detail="El responsable debe ser un usuario activo con acceso a la obra.")


# ---------- Comprobación de las fuentes (§2.3, parte de F2) ----------

def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def problemas_de_fuentes(conn, pedido: Dict) -> List[str]:
    """Motivos por los que una fuente ya no es la versión elegida (vacío si todas están bien)."""
    problemas = []
    if not pedido["fuentes"]:
        problemas.append("El pedido no tiene fuentes seleccionadas.")
    try:
        raiz = config.obtener_datos_raiz().resolve()
    except config.CarpetaDatosInvalida as exc:
        return [str(exc)]
    for fuente in pedido["fuentes"]:
        if fuente["plano_id"] is None:
            problemas.append("Fuente de documento sin revisión de plano: llega con F3.")
            continue
        plano = conn.execute("SELECT * FROM planos WHERE id = ?", (fuente["plano_id"],)).fetchone()
        for lado in ("vectorial", "sellado"):
            ruta = Path(plano[f"{lado}_ruta"])
            try:
                dentro = raiz in ruta.resolve().parents
            except OSError:
                dentro = False
            if not dentro:
                problemas.append(f"Plano rev. {plano['revision']}: el {lado} está fuera de la carpeta de datos.")
            elif not ruta.is_file():
                problemas.append(f"Plano rev. {plano['revision']}: falta el archivo {lado} '{ruta.name}'.")
            elif _sha256(ruta) != plano[f"{lado}_sha256"]:
                problemas.append(f"Plano rev. {plano['revision']}: el {lado} cambió (otro sha256).")
    return problemas


# ---------- API ----------

class PedidoNuevo(BaseModel):
    proposito: str
    responsable_id: Optional[int] = None


class CambioPedido(BaseModel):
    version: int
    proposito: Optional[str] = None
    responsable_id: Optional[int] = None
    progreso: Optional[Dict] = None
    estado: Optional[str] = None


class Fuente(BaseModel):
    plano_id: Optional[int] = None
    documento_version_id: Optional[int] = None


class CambioFuentes(BaseModel):
    version: int
    fuentes: List[Fuente]


def _limpiar_proposito(texto: str) -> str:
    texto = " ".join((texto or "").split())
    if not texto or len(texto) > 500:
        raise HTTPException(status_code=422, detail="Escribe el propósito del pedido (hasta 500 caracteres).")
    return texto


@router.post("/api/obras/{obra_id}/pedidos", status_code=201)
def api_crear_pedido(obra_id: str, cuerpo: PedidoNuevo):
    proposito = _limpiar_proposito(cuerpo.proposito)
    yo = contexto.actual()
    conn = get_connection()
    try:
        _transaccion(conn)
        try:
            responsable = cuerpo.responsable_id or yo.id
            _responsable_valido(conn, obra_id, responsable)
            ahora = _ahora()
            cur = conn.execute("""INSERT INTO pedidos (obra_id, proposito, responsable_id, estado, progreso_json, version,
                                  creado_por, creado_en, actualizado_en) VALUES (?, ?, ?, 'borrador', '{}', 1, ?, ?, ?)""",
                               (obra_id, proposito, responsable, yo.id, ahora, ahora))
            _auditar(conn, "CREAR", cur.lastrowid, {"obra_id": obra_id, "proposito": proposito,
                                                    "responsable_id": responsable})
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return {"pedido": _leer(conn, cur.lastrowid)}
    finally:
        conn.close()


@router.get("/api/obras/{obra_id}/pedidos")
def api_listar_pedidos(obra_id: str):
    conn = get_connection()
    try:
        ids = [f["id"] for f in conn.execute("SELECT id FROM pedidos WHERE obra_id = ? ORDER BY id", (obra_id,))]
        return {"pedidos": [_leer(conn, i) for i in ids]}
    finally:
        conn.close()


@router.get("/api/pedidos/{pedido_id}")
def api_pedido(pedido_id: int):
    conn = get_connection()
    try:
        return {"pedido": _leer(conn, pedido_id)}
    finally:
        conn.close()


def _detener(pedido: Dict, destino: str, problemas: List[str]) -> None:
    """Deja la parada y su motivo en la auditoría (transacción propia) y responde 409. El pedido no cambia."""
    conn = get_connection()
    try:
        _transaccion(conn)
        _auditar(conn, "DETENIDO", pedido["id"], {"estado": pedido["estado"], "destino": destino,
                                                  "motivos": problemas})
        conn.execute("COMMIT")
    finally:
        conn.close()
    raise HTTPException(status_code=409, detail={"mensaje": "Las fuentes del pedido no son las elegidas.",
                                                 "motivos": problemas})


@router.patch("/api/pedidos/{pedido_id}")
def api_cambiar_pedido(pedido_id: int, cuerpo: CambioPedido):
    cambios = cuerpo.model_dump(exclude_unset=True, exclude={"version"})
    if not cambios:
        raise HTTPException(status_code=400, detail="No hay cambios.")
    conn = get_connection()
    try:
        pedido = _leer(conn, pedido_id)
    finally:
        conn.close()
    destino = cambios.get("estado")
    if destino is not None and destino != pedido["estado"]:
        funcion = TRANSICIONES.get((pedido["estado"], destino))
        if funcion is None:
            raise HTTPException(status_code=409, detail=f"No se puede pasar de '{pedido['estado']}' a '{destino}'.")
    else:
        funcion = PREPARAR
    exigir_en_obra(pedido["obra_id"], funcion)
    if pedido["estado"] == "aprobado":
        raise HTTPException(status_code=409, detail="Un pedido aprobado no se edita.")
    if cuerpo.version != pedido["version"]:
        raise HTTPException(status_code=409, detail="Otra persona cambió este pedido antes; recarga y vuelve a intentarlo.")
    if destino in COMPRUEBAN_FUENTES and destino != pedido["estado"]:
        conn = get_connection()
        try:
            problemas = problemas_de_fuentes(conn, pedido)
        finally:
            conn.close()
        if problemas:
            _detener(pedido, destino, problemas)

    sets, params, detalle = [], [], {"funcion": funcion}
    if "proposito" in cambios:
        nuevo = _limpiar_proposito(cambios["proposito"])
        sets.append("proposito = ?"), params.append(nuevo)
        detalle["proposito"] = {"anterior": pedido["proposito"], "nuevo": nuevo}
    if "progreso" in cambios:
        sets.append("progreso_json = ?"), params.append(_json(cambios["progreso"] or {}))
        detalle["progreso"] = {"anterior": pedido["progreso"], "nuevo": cambios["progreso"] or {}}
    if destino is not None and destino != pedido["estado"]:
        sets.append("estado = ?"), params.append(destino)
        detalle["estado"] = {"anterior": pedido["estado"], "nuevo": destino}
    conn = get_connection()
    try:
        _transaccion(conn)
        try:
            if "responsable_id" in cambios and cambios["responsable_id"] is not None:
                _responsable_valido(conn, pedido["obra_id"], cambios["responsable_id"])
                sets.append("responsable_id = ?"), params.append(cambios["responsable_id"])
                detalle["responsable_id"] = {"anterior": pedido["responsable_id"], "nuevo": cambios["responsable_id"]}
            if not sets:
                conn.execute("ROLLBACK")
                raise HTTPException(status_code=400, detail="No hay cambios.")
            cur = conn.execute(f"UPDATE pedidos SET {', '.join(sets)}, version = version + 1, actualizado_en = ? "
                               f"WHERE id = ? AND version = ?", (*params, _ahora(), pedido_id, cuerpo.version))
            if cur.rowcount == 0:   # otro escribió entre la lectura y este UPDATE: no se pisa su cambio
                conn.execute("ROLLBACK")
                raise HTTPException(status_code=409, detail="Otra persona cambió este pedido antes; recarga y vuelve "
                                                            "a intentarlo.")
            accion = ACCION_ESTADO.get(destino, "EDITAR") if "estado" in detalle else "EDITAR"
            _auditar(conn, accion, pedido_id, {**detalle, "version": cuerpo.version + 1})
            conn.execute("COMMIT")
        except HTTPException:
            raise
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return {"pedido": _leer(conn, pedido_id)}
    finally:
        conn.close()


@router.put("/api/pedidos/{pedido_id}/fuentes")
def api_fijar_fuentes(pedido_id: int, cuerpo: CambioFuentes):
    yo = contexto.actual()
    conn = get_connection()
    try:
        _transaccion(conn)
        try:
            pedido = _leer(conn, pedido_id)
            if pedido["estado"] == "aprobado":
                raise HTTPException(status_code=409, detail="Un pedido aprobado no cambia de fuentes.")
            planos = []
            for f in cuerpo.fuentes:
                if f.documento_version_id is not None or f.plano_id is None:
                    raise HTTPException(status_code=422, detail="En esta versión las fuentes son revisiones de plano "
                                                                "(plano_id); los demás documentos llegan con F3.")
                fila = conn.execute("SELECT id FROM planos WHERE id = ? AND proyecto_id = ?",
                                    (f.plano_id, pedido["obra_id"])).fetchone()
                if fila is None:   # un plano de otra obra no se distingue de uno que no existe
                    raise HTTPException(status_code=404, detail=f"Plano {f.plano_id} no encontrado en esta obra.")
                planos.append(f.plano_id)
            planos = list(dict.fromkeys(planos))
            cur = conn.execute("UPDATE pedidos SET version = version + 1, actualizado_en = ? WHERE id = ? AND version = ?",
                               (_ahora(), pedido_id, cuerpo.version))
            if cur.rowcount == 0:
                raise HTTPException(status_code=409, detail="Otra persona cambió este pedido antes; recarga y vuelve a "
                                                            "intentarlo.")
            anteriores = [x["plano_id"] for x in pedido["fuentes"]]
            conn.execute("DELETE FROM pedido_fuentes WHERE pedido_id = ?", (pedido_id,))
            ahora = _ahora()
            for pid in planos:
                conn.execute("""INSERT INTO pedido_fuentes (pedido_id, plano_id, seleccionado_por, seleccionado_en)
                                VALUES (?, ?, ?, ?)""", (pedido_id, pid, yo.id, ahora))
            _auditar(conn, "FIJAR_FUENTES", pedido_id, {"funcion": PREPARAR, "anteriores": anteriores,
                                                        "nuevas": planos, "version": cuerpo.version + 1})
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return {"pedido": _leer(conn, pedido_id)}
    finally:
        conn.close()
