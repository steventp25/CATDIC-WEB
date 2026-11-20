# backend/identidad/rutas.py
# Fundación F2 (contrato §5): sesión, usuarios (es_admin), obras autorizadas y membresías por obra.
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from database import get_connection
from identidad import contexto, permisos, sesiones
from identidad.permisos import ADMINISTRAR_OBRA
from migracion_fundacion import FUNCIONES_OBRA

router = APIRouter()


def _ahora() -> str:
    return datetime.now().isoformat()


def _auditar(conn, modulo: str, accion: str, entidad: str, detalle: dict) -> None:
    u = contexto.actual()
    conn.execute("""INSERT INTO auditoria (fecha_hora, usuario, usuario_id, modulo, accion, entidad_id, detalle_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (_ahora(), u.usuario, u.id, modulo, accion, entidad, json.dumps(detalle, ensure_ascii=False)))


def _transaccion(conn):
    conn.isolation_level = None
    conn.execute("BEGIN IMMEDIATE")


# ---------- Sesión ----------

class Entrada(BaseModel):
    usuario: str
    contrasena: str


@router.post("/api/sesion")
def api_entrar(cuerpo: Entrada, request: Request, response: Response):
    direccion = request.client.host if request.client else "desconocida"
    try:
        token, usuario = sesiones.entrar(cuerpo.usuario, cuerpo.contrasena, direccion)
    except sesiones.EntradaRechazada as exc:
        cabeceras = {"Retry-After": str(exc.espera_segundos)} if exc.espera_segundos else None
        raise HTTPException(status_code=exc.status, detail=str(exc), headers=cabeceras) from None
    # HttpOnly + SameSite=Strict. Sin Secure: el servidor solo escucha en 127.0.0.1 (abrirlo a la red exige HTTPS
    # y Secure, y no lo hace F2: contrato §4.1).
    response.set_cookie(sesiones.COOKIE, token, max_age=int(sesiones.DURACION_TOTAL.total_seconds()),
                        httponly=True, samesite="strict", path="/")
    return {"usuario": _yo(usuario)}


def _yo(usuario) -> dict:
    conn = get_connection()
    try:
        filas = conn.execute("""SELECT m.obra_id, m.funciones, p.nombre FROM membresias m
                                JOIN proyectos p ON p.id = m.obra_id WHERE m.usuario_id = ? ORDER BY p.nombre""",
                             (usuario.id,)).fetchall()
        obras = []
        for f in filas:
            efectivas = permisos.componer(json.loads(f["funciones"] or "[]"))
            if efectivas:
                obras.append({"obra_id": f["obra_id"], "nombre": f["nombre"], "funciones": sorted(efectivas)})
    finally:
        conn.close()
    return {"id": usuario.id, "usuario": usuario.usuario, "nombre_visible": usuario.nombre_visible,
            "es_admin": usuario.es_admin, "obras": obras}


@router.get("/api/sesion")
def api_quien_soy():
    return {"usuario": _yo(contexto.actual())}


@router.delete("/api/sesion")
def api_salir(response: Response):
    sesiones.salir(contexto.actual())
    response.delete_cookie(sesiones.COOKIE, path="/", samesite="strict", httponly=True)
    return {"status": "ok"}


# ---------- Usuarios (solo es_admin) ----------

class UsuarioNuevo(BaseModel):
    usuario: str
    nombre_visible: str
    contrasena: str
    es_admin: bool = False


class CambioUsuario(BaseModel):
    version: int
    activo: Optional[bool] = None
    es_admin: Optional[bool] = None


def _http_usuarios(exc: sesiones.ErrorUsuarios) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=str(exc))


@router.get("/api/usuarios")
def api_listar_usuarios():
    conn = get_connection()
    try:
        return {"usuarios": sesiones.listar_usuarios(conn)}
    finally:
        conn.close()


@router.post("/api/usuarios", status_code=201)
def api_crear_usuario(cuerpo: UsuarioNuevo):
    conn = get_connection()
    try:
        _transaccion(conn)
        try:
            u = sesiones.crear_usuario(conn, cuerpo.usuario, cuerpo.nombre_visible, cuerpo.contrasena,
                                       cuerpo.es_admin, contexto.actual())
            conn.execute("COMMIT")
        except sesiones.ErrorUsuarios as exc:
            conn.execute("ROLLBACK")
            raise _http_usuarios(exc) from None
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return {"usuario": u}
    finally:
        conn.close()


@router.patch("/api/usuarios/{usuario_id}")
def api_cambiar_usuario(usuario_id: int, cuerpo: CambioUsuario):
    conn = get_connection()
    try:
        _transaccion(conn)
        try:
            u = sesiones.cambiar_usuario(conn, usuario_id, cuerpo.version,
                                         cuerpo.model_dump(exclude_unset=True, exclude={"version"}), contexto.actual())
            conn.execute("COMMIT")
        except sesiones.ErrorUsuarios as exc:
            conn.execute("ROLLBACK")
            raise _http_usuarios(exc) from None
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return {"usuario": u}
    finally:
        conn.close()


@router.delete("/api/usuarios/{usuario_id}/sesiones")
def api_cerrar_sesiones(usuario_id: int):
    conn = get_connection()
    try:
        _transaccion(conn)
        try:
            if conn.execute("SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,)).fetchone() is None:
                conn.execute("ROLLBACK")
                raise HTTPException(status_code=404, detail="Usuario no encontrado.")
            n = sesiones.cerrar_todas(conn, usuario_id, "cerradas_por_admin")
            _auditar(conn, "SESION", "CERRAR_SESIONES", str(usuario_id), {"sesiones_cerradas": n})
            conn.execute("COMMIT")
        except HTTPException:
            raise
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return {"sesiones_cerradas": n}
    finally:
        conn.close()


# ---------- Obras autorizadas ----------

def _servicios(conn, obra_id: str) -> List[dict]:
    return [dict(f) for f in conn.execute("""SELECT servicio, formato_defecto, activo, origen FROM obra_servicios
                                             WHERE obra_id = ? ORDER BY id""", (obra_id,))]


@router.get("/api/obras")
def api_obras():
    """Solo las obras autorizadas: las ajenas no aparecen, ni su nombre."""
    usuario = contexto.actual()
    conn = get_connection()
    try:
        ids = permisos.obras_con(conn, usuario)
        obras = []
        for f in conn.execute("SELECT id, nombre, tipo, formato_defecto FROM proyectos ORDER BY nombre").fetchall():
            if f["id"] in ids:
                obras.append({**dict(f), "servicios": _servicios(conn, f["id"]),
                              "funciones": sorted(permisos.funciones_efectivas(conn, usuario, f["id"]))})
        return {"obras": obras}
    finally:
        conn.close()


@router.get("/api/obras/{obra_id}")
def api_obra(obra_id: str):
    usuario = contexto.actual()
    conn = get_connection()
    try:
        f = conn.execute("SELECT * FROM proyectos WHERE id = ?", (obra_id,)).fetchone()
        return {"obra": {**dict(f), "servicios": _servicios(conn, obra_id),
                         "funciones": sorted(permisos.funciones_efectivas(conn, usuario, obra_id))}}
    finally:
        conn.close()


# ---------- Membresías de una obra (administrar_obra) ----------

class CambioMembresia(BaseModel):
    funciones: List[str]
    version: Optional[int] = None   # None solo para crear una membresía nueva


@router.get("/api/obras/{obra_id}/membresias")
def api_membresias(obra_id: str):
    conn = get_connection()
    try:
        filas = conn.execute("""SELECT m.usuario_id, u.usuario, u.nombre_visible, u.activo, m.funciones, m.version,
                                       m.actualizada FROM membresias m JOIN usuarios u ON u.id = m.usuario_id
                                WHERE m.obra_id = ? ORDER BY u.usuario""", (obra_id,)).fetchall()
        return {"membresias": [{**dict(f), "funciones": json.loads(f["funciones"]), "activo": bool(f["activo"])}
                               for f in filas]}
    finally:
        conn.close()


def asignar_membresia(conn, obra_id: str, usuario_id: int, funciones: List[str], version: Optional[int],
                      motivo: str = "") -> dict:
    """Crea, cambia o (con funciones vacías) revoca una membresía, con control de versión y auditoría.
    Corre dentro de la transacción del llamador."""
    desconocidas = [f for f in funciones if f not in FUNCIONES_OBRA]
    if desconocidas:
        # Contrato §4 (rev. 3): 'administrar' (o cualquier otra) se rechaza; no se traduce a otra función
        raise HTTPException(status_code=422, detail=f"Función de obra no permitida: {', '.join(desconocidas)}. "
                                                    f"Las funciones son: {', '.join(FUNCIONES_OBRA)}.")
    if conn.execute("SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    nuevas = sorted(set(funciones))
    previa = conn.execute("SELECT * FROM membresias WHERE usuario_id = ? AND obra_id = ?",
                          (usuario_id, obra_id)).fetchone()
    ahora = _ahora()
    if previa is None:
        if version not in (None, 0):
            raise HTTPException(status_code=409, detail="La membresía cambió (ya no existe); recarga.")
        if not nuevas:
            raise HTTPException(status_code=404, detail="Ese usuario no tiene membresía en esta obra.")
        conn.execute("""INSERT INTO membresias (usuario_id, obra_id, funciones, version, creada, actualizada)
                        VALUES (?, ?, ?, 1, ?, ?)""", (usuario_id, obra_id, json.dumps(nuevas), ahora, ahora))
        accion, anterior, nueva_version = "ASIGNAR", [], 1
    else:
        if version != previa["version"]:
            raise HTTPException(status_code=409, detail="Otra persona cambió esta membresía antes; recarga.")
        anterior = json.loads(previa["funciones"])
        if nuevas:
            cur = conn.execute("""UPDATE membresias SET funciones = ?, version = version + 1, actualizada = ?
                                  WHERE id = ? AND version = ?""", (json.dumps(nuevas), ahora, previa["id"], version))
            accion, nueva_version = "CAMBIAR", version + 1
        else:
            cur = conn.execute("DELETE FROM membresias WHERE id = ? AND version = ?", (previa["id"], version))
            accion, nueva_version = "REVOCAR", None
        if cur.rowcount == 0:
            raise HTTPException(status_code=409, detail="Otra persona cambió esta membresía antes; recarga.")
    _auditar(conn, "MEMBRESIAS", accion, f"{obra_id}:{usuario_id}",
             {"obra_id": obra_id, "usuario_id": usuario_id, "anterior": anterior, "nuevo": nuevas,
              **({"motivo": motivo} if motivo else {})})
    return {"obra_id": obra_id, "usuario_id": usuario_id, "funciones": nuevas, "version": nueva_version}


@router.put("/api/obras/{obra_id}/membresias/{usuario_id}")
def api_asignar_membresia(obra_id: str, usuario_id: int, cuerpo: CambioMembresia):
    if usuario_id == contexto.usuario_id():
        # Sin esto, administrar_obra podría darse a sí mismo preparar o revisar_autorizar (rev. 3)
        raise HTTPException(status_code=403, detail="No puedes cambiar tus propias funciones en una obra.")
    conn = get_connection()
    try:
        _transaccion(conn)
        try:
            r = asignar_membresia(conn, obra_id, usuario_id, cuerpo.funciones, cuerpo.version)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return {"membresia": r}
    finally:
        conn.close()


FUNCIONES_CREADOR = [ADMINISTRAR_OBRA, "preparar", "revisar_autorizar"]
