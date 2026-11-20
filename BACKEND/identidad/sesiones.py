# backend/identidad/sesiones.py
# Fundación F2 (contrato §4.1): entrada, sesiones, caducidad, bloqueo por intentos y desactivación de usuarios.
#
# - El token de sesión es aleatorio (secrets) y solo viaja en la cookie; la base guarda su sha256.
# - Caducidad: 12 h sin uso o 7 días en total, comprobada en el servidor en cada petición.
# - 5 fallos seguidos (por usuario y dirección) -> espera de 15 min, que se duplica con cada fallo nuevo (tope 24 h).
#   Cada intento queda en la auditoría, sin la contraseña.
# - Desactivar a un usuario cierra todas sus sesiones en la misma transacción; su próxima petición recibe 401.
import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from database import get_connection
from identidad import contrasenas
from identidad.contexto import Usuario

COOKIE = "catdic_sesion"
INACTIVIDAD = timedelta(hours=12)
DURACION_TOTAL = timedelta(days=7)
REFRESCO_ULTIMO_USO = timedelta(seconds=60)   # no se escribe en la base en cada lectura
MAX_FALLOS = 5
ESPERA_INICIAL = timedelta(minutes=15)
ESPERA_MAXIMA = timedelta(hours=24)
MODULO = "SESION"
_RE_LOGIN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")


class EntradaRechazada(Exception):
    def __init__(self, mensaje: str, status: int = 401, espera_segundos: int = 0):
        super().__init__(mensaje)
        self.status = status
        self.espera_segundos = espera_segundos


class ErrorUsuarios(Exception):
    def __init__(self, mensaje: str, status: int = 422):
        super().__init__(mensaje)
        self.status = status


def _ahora() -> datetime:
    return datetime.now()   # las pruebas lo sustituyen para simular el paso del tiempo


def _iso(t: datetime) -> str:
    return t.isoformat()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _auditar(conn, accion: str, entidad: str, detalle: dict, usuario: str, usuario_id: Optional[int]) -> None:
    conn.execute("""INSERT INTO auditoria (fecha_hora, usuario, usuario_id, modulo, accion, entidad_id, detalle_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (_iso(_ahora()), usuario, usuario_id, MODULO, accion, entidad, json.dumps(detalle, ensure_ascii=False)))


def normalizar_login(texto: str) -> str:
    return (texto or "").strip().lower()


# ---------- Bloqueo por intentos ----------

def bloqueado_hasta(conn, login: str, direccion: str, ahora: datetime) -> Optional[datetime]:
    """Si hay 5+ fallos seguidos para (usuario, dirección), hasta cuándo dura la espera; None si se puede intentar."""
    filas = conn.execute("""SELECT exito, en FROM intentos_entrada WHERE usuario = ? AND direccion = ?
                            ORDER BY id DESC LIMIT 64""", (login, direccion)).fetchall()
    fallos, ultimo = 0, None
    for f in filas:
        if f["exito"]:
            break
        fallos += 1
        ultimo = ultimo or datetime.fromisoformat(f["en"])
    if fallos < MAX_FALLOS:
        return None
    espera = min(ESPERA_INICIAL * (2 ** min(fallos - MAX_FALLOS, 10)), ESPERA_MAXIMA)
    hasta = ultimo + espera
    return hasta if hasta > ahora else None


# ---------- Entrar / salir ----------

def entrar(usuario_texto: str, contrasena: str, direccion: str) -> Tuple[str, Usuario]:
    """Devuelve (token, usuario) o lanza EntradaRechazada (401 genérico o 429 con la espera)."""
    login = normalizar_login(usuario_texto)[:80]
    direccion = (direccion or "desconocida")[:80]
    ahora = _ahora()
    conn = get_connection()
    try:
        hasta = bloqueado_hasta(conn, login, direccion, ahora)
        if hasta is not None:
            conn.isolation_level = None
            conn.execute("BEGIN IMMEDIATE")
            _auditar(conn, "ENTRADA_BLOQUEADA", login or "-", {"usuario": login, "direccion": direccion,
                                                                "hasta": _iso(hasta)}, "anonimo", None)
            conn.execute("COMMIT")
            raise EntradaRechazada("Demasiados intentos fallidos. Espera antes de volver a intentarlo.", 429,
                                   int((hasta - ahora).total_seconds()) + 1)
        fila = conn.execute("SELECT * FROM usuarios WHERE usuario = ?", (login,)).fetchone() if login else None
        # Se verifica siempre (con un hash de relleno si el usuario no existe) para no revelar qué usuarios existen
        correcta = contrasenas.verificar(contrasena or "", fila["hash_contrasena"] if fila else contrasenas.hash_relleno())
        ok = bool(fila) and correcta and fila["activo"] == 1
        motivo = "ok" if ok else ("usuario_desactivado" if fila and correcta else "credenciales")
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute("INSERT INTO intentos_entrada (usuario, direccion, exito, en) VALUES (?, ?, ?, ?)",
                         (login, direccion, 1 if ok else 0, _iso(ahora)))
            if not ok:
                _auditar(conn, "ENTRADA_FALLIDA", login or "-", {"usuario": login, "direccion": direccion,
                                                                  "motivo": motivo}, "anonimo", None)
                conn.execute("COMMIT")
                raise EntradaRechazada("Usuario o contraseña incorrectos.")
            token = secrets.token_urlsafe(32)
            cur = conn.execute("""INSERT INTO sesiones (token_hash, usuario_id, creada, ultimo_uso, expira, direccion)
                                  VALUES (?, ?, ?, ?, ?, ?)""",
                               (_hash_token(token), fila["id"], _iso(ahora), _iso(ahora),
                                _iso(ahora + DURACION_TOTAL), direccion))
            _auditar(conn, "ENTRADA", str(cur.lastrowid), {"direccion": direccion}, fila["usuario"], fila["id"])
            conn.execute("COMMIT")
        except EntradaRechazada:
            raise
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return token, Usuario(fila["id"], fila["usuario"], fila["nombre_visible"], bool(fila["es_admin"]), cur.lastrowid)
    finally:
        conn.close()


def _cerrar(conn, sesion_id: int, motivo: str, ahora: datetime) -> None:
    conn.execute("UPDATE sesiones SET cerrada = ?, motivo_cierre = ? WHERE id = ? AND cerrada IS NULL",
                 (_iso(ahora), motivo, sesion_id))


def validar(token: Optional[str]) -> Optional[Usuario]:
    """El usuario de una sesión vigente, o None. Cierra la sesión si caducó o si el usuario está desactivado."""
    if not token or len(token) > 200:
        return None
    ahora = _ahora()
    conn = get_connection()
    try:
        f = conn.execute("""
            SELECT s.id, s.usuario_id, s.creada, s.ultimo_uso, s.expira, s.cerrada,
                   u.usuario, u.nombre_visible, u.activo, u.es_admin
            FROM sesiones s JOIN usuarios u ON u.id = s.usuario_id WHERE s.token_hash = ?
        """, (_hash_token(token),)).fetchone()
        if f is None or f["cerrada"] is not None:
            return None
        motivo = None
        if f["activo"] != 1:
            motivo = "usuario_desactivado"
        elif ahora >= datetime.fromisoformat(f["expira"]):
            motivo = "caducada_7_dias"
        elif ahora - datetime.fromisoformat(f["ultimo_uso"]) >= INACTIVIDAD:
            motivo = "caducada_12_h_sin_uso"
        if motivo:
            _cerrar(conn, f["id"], motivo, ahora)
            conn.commit()
            return None
        if ahora - datetime.fromisoformat(f["ultimo_uso"]) >= REFRESCO_ULTIMO_USO:
            conn.execute("UPDATE sesiones SET ultimo_uso = ? WHERE id = ?", (_iso(ahora), f["id"]))
            conn.commit()
        return Usuario(f["usuario_id"], f["usuario"], f["nombre_visible"], bool(f["es_admin"]), f["id"])
    finally:
        conn.close()


def salir(usuario: Usuario) -> None:
    conn = get_connection()
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        _cerrar(conn, usuario.sesion_id, "salida", _ahora())
        _auditar(conn, "SALIR", str(usuario.sesion_id), {}, usuario.usuario, usuario.id)
        conn.execute("COMMIT")
    finally:
        conn.close()


def cerrar_todas(conn, usuario_id: int, motivo: str) -> int:
    """Cierra todas las sesiones abiertas del usuario (dentro de la transacción del llamador)."""
    return conn.execute("UPDATE sesiones SET cerrada = ?, motivo_cierre = ? WHERE usuario_id = ? AND cerrada IS NULL",
                        (_iso(_ahora()), motivo, usuario_id)).rowcount


# ---------- Usuarios (solo es_admin por la API; el alta inicial es local) ----------

def _publico(f) -> Dict:
    return {"id": f["id"], "usuario": f["usuario"], "nombre_visible": f["nombre_visible"], "activo": bool(f["activo"]),
            "es_admin": bool(f["es_admin"]), "creado_en": f["creado_en"], "version": f["version"]}


def crear_usuario(conn, login: str, nombre_visible: str, contrasena: str, es_admin: bool,
                  hecho_por: Optional[Usuario]) -> Dict:
    """Crea un usuario dentro de la transacción del llamador. La contraseña la escribe la persona."""
    login = normalizar_login(login)
    if not _RE_LOGIN.match(login):
        raise ErrorUsuarios("El usuario debe tener 3–40 caracteres: letras minúsculas, números, punto, guion o guion bajo.")
    nombre_visible = " ".join((nombre_visible or "").split())
    if not nombre_visible or len(nombre_visible) > 80:
        raise ErrorUsuarios("Escribe el nombre visible (hasta 80 caracteres).")
    try:
        h = contrasenas.generar_hash(contrasena)
    except contrasenas.ContrasenaInvalida as exc:
        raise ErrorUsuarios(str(exc)) from None
    if conn.execute("SELECT 1 FROM usuarios WHERE usuario = ?", (login,)).fetchone():
        raise ErrorUsuarios("Ese usuario ya existe.", 409)
    ahora = _iso(_ahora())
    cur = conn.execute("""INSERT INTO usuarios (usuario, nombre_visible, hash_contrasena, activo, es_admin, creado_en,
                          actualizado) VALUES (?, ?, ?, 1, ?, ?, ?)""",
                       (login, nombre_visible, h, 1 if es_admin else 0, ahora, ahora))
    _auditar(conn, "CREAR_USUARIO", str(cur.lastrowid), {"usuario": login, "es_admin": bool(es_admin)},
             hecho_por.usuario if hecho_por else "local", hecho_por.id if hecho_por else None)
    return _publico(conn.execute("SELECT * FROM usuarios WHERE id = ?", (cur.lastrowid,)).fetchone())


def listar_usuarios(conn) -> List[Dict]:
    return [_publico(f) for f in conn.execute("SELECT * FROM usuarios ORDER BY id")]


def cambiar_usuario(conn, usuario_id: int, version: int, cambios: Dict, hecho_por: Usuario) -> Dict:
    """Activa/desactiva o cambia es_admin con control de versión. Desactivar cierra todas sus sesiones."""
    f = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if f is None:
        raise ErrorUsuarios("Usuario no encontrado.", 404)
    if usuario_id == hecho_por.id and (cambios.get("activo") is False or cambios.get("es_admin") is False):
        raise ErrorUsuarios("No puedes desactivarte ni quitarte la administración a ti mismo.", 409)
    sets, params, detalle = [], [], {}
    for campo in ("activo", "es_admin"):
        if campo in cambios and cambios[campo] is not None:
            nuevo = 1 if cambios[campo] else 0
            sets.append(f"{campo} = ?")
            params.append(nuevo)
            detalle[campo] = {"anterior": bool(f[campo]), "nuevo": bool(nuevo)}
    if not sets:
        raise ErrorUsuarios("No hay cambios.")
    cur = conn.execute(f"UPDATE usuarios SET {', '.join(sets)}, version = version + 1, actualizado = ? "
                       f"WHERE id = ? AND version = ?", (*params, _iso(_ahora()), usuario_id, version))
    if cur.rowcount == 0:
        raise ErrorUsuarios("Otra persona cambió este usuario antes; recarga y vuelve a intentarlo.", 409)
    if cambios.get("activo") is False:
        detalle["sesiones_cerradas"] = cerrar_todas(conn, usuario_id, "usuario_desactivado")
    _auditar(conn, "CAMBIAR_USUARIO", str(usuario_id), detalle, hecho_por.usuario, hecho_por.id)
    return _publico(conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone())
