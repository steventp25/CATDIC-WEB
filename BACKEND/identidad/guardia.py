# backend/identidad/guardia.py
# Fundación F2: la guardia común de la API. Es una dependencia GLOBAL de la aplicación (main.py), así que corre en
# TODA ruta /api, también en las del tablero clásico, antes del código de la ruta:
#   1. mutaciones (POST/PUT/PATCH/DELETE): encabezado propio X-CATDIC-Peticion y Origin del mismo servidor -> si no, 403;
#   2. sesión vigente (cookie) -> si no, 401;
#   3. la política de la ruta (tabla POLITICAS): función mínima en la obra que toca la ruta -> 404 si la obra es
#      ajena o no existe, 403 si falta la función. Las rutas de listado reciben el usuario y filtran (filtra=True).
# Una ruta /api sin política se rechaza (403): una ruta nueva no puede quedar abierta por olvido, y la prueba
# test_f2_permisos.py::test_toda_ruta_api_tiene_politica lo comprueba.
import json
import os
from dataclasses import dataclass
from typing import Callable, List, Optional
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

from database import get_connection
from identidad import contexto, permisos, sesiones
from identidad.permisos import ADMINISTRAR_OBRA, CONSULTAR, PREPARAR, REVISAR_AUTORIZAR

ENCABEZADO_PROPIO = "X-CATDIC-Peticion"
MUTACIONES = {"POST", "PUT", "PATCH", "DELETE"}
HOSTS_LOCALES = {"localhost", "127.0.0.1", "[::1]", "::1"}
ENV_HOSTS = "CATDIC_HOSTS_PERMITIDOS"   # nombres de servidor adicionales (p. ej. 'testserver' en las pruebas)


# ---------- Resolución de la obra de cada ruta ----------

def _de_ruta(nombre: str) -> Callable:
    return lambda req, conn: [req.path_params.get(nombre)]


def _una(conn, sql: str, valor) -> List[Optional[str]]:
    fila = conn.execute(sql, (valor,)).fetchone()
    return [fila[0] if fila else None]


def _visita(req, conn):
    return _una(conn, "SELECT proyecto_id FROM visitas WHERE id = ?", req.path_params.get("visita_id"))


def _duda(req, conn):
    return _una(conn, "SELECT proyecto_id FROM dudas_y_hallazgos WHERE id = ?", req.path_params.get("duda_id"))


def _pedido(req, conn):
    return _una(conn, "SELECT obra_id FROM pedidos WHERE id = ?", req.path_params.get("pedido_id"))


def _trabajo(req, conn):
    """Todas las obras de las visitas del trabajo: hace falta la función en cada una."""
    fila = conn.execute("SELECT visitas_json FROM trabajos WHERE id = ?", (req.path_params.get("trabajo_id"),)).fetchone()
    if fila is None:
        return [None]
    try:
        ids = json.loads(fila[0] or "[]")
    except ValueError:
        return [None]
    obras = []
    for vid in ids:
        obras.extend(_una(conn, "SELECT proyecto_id FROM visitas WHERE id = ?", vid))
    return obras or [None]


def _consulta_opcional(req, conn):
    """?proyecto_id= opcional: si viene se comprueba; si no, la ruta filtra por las obras del usuario."""
    pid = req.query_params.get("proyecto_id")
    return [pid] if pid else []


def _filtro_dudas(req, conn):
    obras = _consulta_opcional(req, conn)
    vid = req.query_params.get("visita_id")
    if vid:
        obras += _una(conn, "SELECT proyecto_id FROM visitas WHERE id = ?", vid)
    return obras


@dataclass(frozen=True)
class Politica:
    funcion: Optional[str] = None          # función mínima en la obra
    obras: Optional[Callable] = None       # (request, conn) -> lista de obra_id (None = no existe)
    admin: bool = False                    # solo usuarios.es_admin
    publica: bool = False                  # sin sesión (solo la entrada)
    filtra: bool = False                   # la ruta filtra su resultado por las obras del usuario


_P = _de_ruta("proyecto_id")
_O = _de_ruta("obra_id")

POLITICAS = {
    # Sesión y administración global
    ("POST", "/api/sesion"): Politica(publica=True),
    ("GET", "/api/sesion"): Politica(),
    ("DELETE", "/api/sesion"): Politica(),
    ("GET", "/api/usuarios"): Politica(admin=True),
    ("POST", "/api/usuarios"): Politica(admin=True),
    ("PATCH", "/api/usuarios/{usuario_id}"): Politica(admin=True),
    ("DELETE", "/api/usuarios/{usuario_id}/sesiones"): Politica(admin=True),
    # Obras (API nueva)
    ("GET", "/api/obras"): Politica(filtra=True),
    ("GET", "/api/obras/{obra_id}"): Politica(CONSULTAR, _O),
    ("GET", "/api/obras/{obra_id}/membresias"): Politica(ADMINISTRAR_OBRA, _O),
    ("PUT", "/api/obras/{obra_id}/membresias/{usuario_id}"): Politica(ADMINISTRAR_OBRA, _O),
    # Pedidos (contrato §5): la ruta exige además preparar o revisar_autorizar según el cambio
    ("POST", "/api/obras/{obra_id}/pedidos"): Politica(PREPARAR, _O),
    ("GET", "/api/obras/{obra_id}/pedidos"): Politica(CONSULTAR, _O),
    ("GET", "/api/pedidos/{pedido_id}"): Politica(CONSULTAR, _pedido),
    ("PATCH", "/api/pedidos/{pedido_id}"): Politica(CONSULTAR, _pedido),
    ("PUT", "/api/pedidos/{pedido_id}/fuentes"): Politica(PREPARAR, _pedido),
    # Tablero clásico (main.py)
    ("GET", "/api/dashboard"): Politica(filtra=True),
    ("PATCH", "/api/proyectos/{proyecto_id}"): Politica(PREPARAR, _P),
    ("POST", "/api/dropbox/sync"): Politica(PREPARAR, _consulta_opcional, filtra=True),
    ("POST", "/api/visitas/procesar-cola"): Politica(PREPARAR, _consulta_opcional, filtra=True),
    ("POST", "/api/visitas/{visita_id}/procesar"): Politica(PREPARAR, _visita),
    ("GET", "/api/trabajos/{trabajo_id}"): Politica(CONSULTAR, _trabajo),
    ("GET", "/api/trabajos/{trabajo_id}/eventos"): Politica(CONSULTAR, _trabajo),
    # Mesa de Dudas: responder confirma datos o cierra dudas bloqueantes
    ("GET", "/api/dudas"): Politica(CONSULTAR, _filtro_dudas, filtra=True),
    ("PATCH", "/api/dudas/{duda_id}"): Politica(REVISAR_AUTORIZAR, _duda),
    # Obras y planos (obras.py). Subir planos certifica la revisión: revisar_autorizar (rev. 3)
    ("POST", "/api/proyectos"): Politica(admin=True),
    ("POST", "/api/proyectos/{proyecto_id}/planos"): Politica(REVISAR_AUTORIZAR, _P),
    ("GET", "/api/proyectos/{proyecto_id}/planos"): Politica(CONSULTAR, _P),
    ("PUT", "/api/proyectos/{proyecto_id}/datos-obra"): Politica(REVISAR_AUTORIZAR, _P),   # se guardan 'confirmado'
    ("GET", "/api/proyectos/{proyecto_id}/datos-obra"): Politica(CONSULTAR, _P),
    # Visor (visor.py): hojas, vista previa y archivos
    ("GET", "/api/proyectos/{proyecto_id}/visor/indice"): Politica(CONSULTAR, _P),
    ("GET", "/api/proyectos/{proyecto_id}/visor/hojas/{pagina}/info"): Politica(CONSULTAR, _P),
    ("GET", "/api/proyectos/{proyecto_id}/visor/hojas/{pagina}.png"): Politica(CONSULTAR, _P),
    ("GET", "/api/proyectos/{proyecto_id}/elementos"): Politica(CONSULTAR, _P),
    ("POST", "/api/proyectos/{proyecto_id}/elementos/{uid}/propuesta"): Politica(CONSULTAR, _P),
    ("PUT", "/api/proyectos/{proyecto_id}/elementos/{uid}/recuadro"): Politica(REVISAR_AUTORIZAR, _P),  # se guarda 'confirmado'
    ("POST", "/api/proyectos/{proyecto_id}/visor/vista-previa"): Politica(CONSULTAR, _P),
    # Lectura del plano (plano/extractor.py y plano/confirmacion.py)
    ("POST", "/api/proyectos/{proyecto_id}/extraer-diseno"): Politica(PREPARAR, _P),
    ("GET", "/api/proyectos/{proyecto_id}/tablas-extraidas"): Politica(CONSULTAR, _P),
    ("GET", "/api/proyectos/{proyecto_id}/tablas-extraidas/{tabla_id}"): Politica(CONSULTAR, _P),
    ("POST", "/api/proyectos/{proyecto_id}/tablas-extraidas/{tabla_id}/confirmar"): Politica(REVISAR_AUTORIZAR, _P),
    ("POST", "/api/proyectos/{proyecto_id}/tablas-extraidas/{tabla_id}/certificar-notas"): Politica(REVISAR_AUTORIZAR, _P),
    # Visitas (visitas_obra.py)
    ("POST", "/api/proyectos/{proyecto_id}/visitas"): Politica(PREPARAR, _P),
    ("POST", "/api/proyectos/{proyecto_id}/dropbox"): Politica(PREPARAR, _P),
}


# ---------- Comprobaciones ----------

def hosts_permitidos() -> set:
    extra = {h.strip().lower() for h in os.environ.get(ENV_HOSTS, "").split(",") if h.strip()}
    return HOSTS_LOCALES | extra


def _nombre_host(valor: str) -> str:
    valor = (valor or "").strip().lower()
    if valor.startswith("["):
        return valor.split("]")[0] + "]"
    return valor.rsplit(":", 1)[0] if ":" in valor else valor


def verificar_mutacion(request: Request) -> None:
    """403 si falta el encabezado propio o el Origin no es este mismo servidor local (contrato §4.1)."""
    if request.headers.get(ENCABEZADO_PROPIO) != "1":
        raise HTTPException(status_code=403, detail="Petición rechazada: falta el encabezado de la aplicación.")
    host = request.headers.get("host", "")
    origen = request.headers.get("origin")
    if not origen or _nombre_host(host) not in hosts_permitidos():
        raise HTTPException(status_code=403, detail="Petición rechazada: origen no permitido.")
    partes = urlsplit(origen)
    if partes.scheme not in ("http", "https") or partes.netloc.lower() != host.lower():
        raise HTTPException(status_code=403, detail="Petición rechazada: origen no permitido.")


def _comprobar_obras(politica: Politica, request: Request, usuario) -> None:
    conn = get_connection()
    try:
        obras = politica.obras(request, conn) if politica.obras else []
        for obra_id in obras:
            permisos.exigir(conn, usuario, obra_id, politica.funcion)
    finally:
        conn.close()


async def guardia(request: Request) -> None:
    ruta = request.scope.get("route")
    plantilla = getattr(ruta, "path", None)
    if plantilla is None or not plantilla.startswith("/api"):
        return
    metodo = request.method.upper()
    if metodo in MUTACIONES:
        verificar_mutacion(request)
    politica = POLITICAS.get((metodo, plantilla))
    if politica is None:
        raise HTTPException(status_code=403, detail="Ruta sin política de permisos.")
    if politica.publica:
        contexto.fijar(None)
        return
    usuario = await run_in_threadpool(sesiones.validar, request.cookies.get(sesiones.COOKIE))
    if usuario is None:
        contexto.fijar(None)
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar.")
    contexto.fijar(usuario)        # lo ve el código de la ruta y los disparadores de auditoría
    request.state.usuario = usuario
    if politica.admin and not usuario.es_admin:
        raise HTTPException(status_code=403, detail="Solo un administrador puede hacer esto.")
    if politica.funcion:
        try:
            await run_in_threadpool(_comprobar_obras, politica, request, usuario)
        except permisos.SinAcceso:
            raise HTTPException(status_code=404, detail="No encontrado.") from None
        except permisos.FuncionInsuficiente as exc:
            raise HTTPException(status_code=403, detail=f"Te falta la función '{exc}' en esta obra.") from None


# ---------- Ayudas para las rutas que filtran ----------

def usuario_de_la_peticion():
    return contexto.actual()


def obras_del_usuario(funcion: str = CONSULTAR) -> set:
    conn = get_connection()
    try:
        return permisos.obras_con(conn, contexto.actual(), funcion)
    finally:
        conn.close()


def exigir_en_obra(obra_id: str, funcion: str) -> None:
    """Para rutas que deciden la función según el cambio pedido (p. ej. PATCH de un pedido)."""
    conn = get_connection()
    try:
        permisos.exigir(conn, contexto.actual(), obra_id, funcion)
    except permisos.SinAcceso:
        raise HTTPException(status_code=404, detail="No encontrado.") from None
    except permisos.FuncionInsuficiente as exc:
        raise HTTPException(status_code=403, detail=f"Te falta la función '{exc}' en esta obra.") from None
    finally:
        conn.close()
