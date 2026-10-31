# BACKEND/procesador_cola.py
# Etapa 3 · T10a — Procesador de la cola de visitas (PLANES/etapa-3.md, T10 / T10a).
#
# Un TRABAJO procesa una o varias visitas en un hilo (la app es local) y deja eventos numerados en
# `trabajo_eventos` para la pantalla en vivo (T10b): visita_inicio, elemento_inicio, elemento_listo, duda, aviso,
# pdf_generado, visita_fin y fin. Por visita:
#   1. Lector T3 si la visita no fue leída.
#   2. Cruce de cada `elementos_visita` con `elementos_diseno` por ID + Nivel + Ejes (§4.2), sin adivinar:
#      cero o varios candidatos, un dato de diseño sin `confirmado` o un recuadro sin confirmar => DUDA_BLOQUEANTE y
#      el elemento queda EN ESPERA; el trabajo sigue con los demás. La "etiqueta" de la visita nunca es el ID.
#   3. Generación (STP-MIVED y FI-01/02/03 según `formatos_solicitados`; CATDIC-STP está aplazado) solo si todos los
#      elementos tienen ficha y la visita no tiene dudas propias abiertas. Se genera en una carpeta de paso dentro de
#      la salida de pruebas (P3) y se publica al cerrar: limpio con su nombre §5.2; con dudas, con " - CON DUDAS".
#   4. Cierre: auditor del PDF (§5.2, #15) y estado. `Procesada` solo sin dudas abiertas, sin excluidos, sin dudas de
#      OBRA y con todos los formatos generados; si no, `Con dudas`. Antes de cerrar se reintentan los elementos en
#      espera cuya duda ya respondió Steven en la Mesa (O4: la respuesta se lee y se aplica de forma estricta).
# Regla de Oro #1: nada se inventa; Dropbox es solo lectura; nunca se sobrescribe un archivo.
import json
import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import config
import pymupdf
from database import _respaldar_bd, get_connection, usuario_auditoria
from generators import fi_mived, stp_mived
from generators.comun import localizacion as m3_localizacion
from generators.comun import salida
from reglas_ingenieria import PENDIENTE, auditar_archivo_pdf_generado, obtener_ruta_salida_sin_sobrescribir
from sync import lector_visita
from sync.escaner_dropbox import SUBRUTA_INFORMES_PROCESADOS, _escanear_informes
from sync.parser_visitas import CLASE_COMPLETIVO, CLASE_PARCIAL, interpretar_nombre_carpeta_visita
from sync.sincronizador import (
    CAMPO_ESTADO,
    DUDA,
    ESTADO_CON_DUDAS,
    ESTADO_PROCESADA,
    ESTADO_SIN_PROCESAR,
    _descripcion_duda_estado,
    _origen_estado,
    evaluar_p3,
)

MODULO_AUDITORIA = "PROCESADOR"
CORRIENDO, TERMINADO, FALLIDO = "corriendo", "terminado", "fallido"
ESTADO_EN_PROCESO = "En proceso"
ESTADOS_COLA = ("Sin procesar", "En cola")
ESTADOS_PROCESABLES = ESTADOS_COLA + (ESTADO_CON_DUDAS,)
ORIGEN_ESTADO = "procesador"
CONFIRMADO = "confirmado"
EJE_LOSA = "—"
CARPETA_DE_PASO = "_en_proceso"           # dentro de la salida de pruebas; se vacía al publicar
SUFIJO_CON_DUDAS = " - CON DUDAS"
RESPUESTA_CIERRE = "resuelta por el procesador: la causa ya no existe"
RESPUESTA_ANTERIOR = "PERTENECE AL ANTERIOR"

FORMATO_STP, FORMATO_CATDIC = "STP-MIVED", "CATDIC-STP"
FORMATOS_FI = {"MIVED FI", "MIVED FI-01/02/03", "FI-01/02/03", "FORMULARIOS MIVED", "FI-01", "FI-02", "FI-03"}
FI_POR_FILA = {"losa": "FI-02", "viga": "FI-02", "col": "FI-03", "muro": "FI-03"}
SUBRUTA_FI_NO_FIRMADOS = Path("FORMULARIOS", "MIVED", "FORMULARIOS NO FIRMADOS")
SUBRUTA_FORMULARIOS = Path("FORMULARIOS")

# Campos de dudas que abre el lector (T3) y el procesador para UN elemento (sufijo pNNN = página que lo abre).
PREFIJO_LECTOR = "elemento_visita:"
_RE_CAMPO_ELEMENTO = re.compile(r"^(elemento_visita|cruce|diseno|obra|excluido|generacion):(p\d{3})(?::|$)")
# Dudas de la visita que abre el propio procesador: se recalculan en cada corrida (se cierran si la causa ya no está).
PREFIJOS_PROPIOS_VISITA = ("procesador:", "proyecto:", "generacion:", "auditor:")


def campo_de_elemento(campo: str) -> Optional[Tuple[str, str]]:
    """('cruce', 'p007') para una duda de un elemento; None para una duda de la visita."""
    m = _RE_CAMPO_ELEMENTO.match(campo or "")
    return (m.group(1), m.group(2)) if m else None


def es_propia_de_visita(campo: str) -> bool:
    return campo_de_elemento(campo) is None and (campo or "").startswith(PREFIJOS_PROPIOS_VISITA)

# De qué dato de diseño (datos_diseno_json) sale cada fila del STP-MIVED. PENDIENTE DE STEVEN: hoy NO hay ninguna
# correspondencia aprobada (p. ej. si "DIR. X" de la tabla de acero en losa es la fila h "Barras Top X-X" o la i
# "Barras Bot X-X"), así que el procesador no la deduce: el elemento queda en espera con una duda `diseno:pNNN:mapeo`.
# Forma: {fila_stp: {"filas": {letra: campo}, "medidas": {letra: campo en metros}, "barras": campo | None}}.
MAPEO_DISENO_A_STP: Dict[str, Dict] = {}

_cerrojo = threading.Lock()
_hilos: Dict[str, threading.Thread] = {}
_RE_PAGINA_TABLA = re.compile(r"^p(\d+):")
_RE_NIVEL_SOTANO = re.compile(r"^S-?(\d+)$")
_RE_UID = re.compile(r"^ed-[0-9a-f]+$", re.IGNORECASE)
_RE_ID = re.compile(r"^[A-Z]{1,3}\d{1,3}$")


class TrabajoEnCurso(RuntimeError):
    """Ya hay un trabajo corriendo (409): dos trabajos a la vez podrían tocar la misma visita."""


class VisitaNoProcesable(ValueError):
    """La visita no existe (LookupError aparte) o su estado no se procesa (409)."""


# ---------- Utilidades ----------

def _ahora() -> str:
    return datetime.now().isoformat()


def _json(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, default=str)


def _dict(texto) -> dict:
    try:
        valor = json.loads(texto or "{}")
    except (TypeError, ValueError):
        return {}
    return valor if isinstance(valor, dict) else {}


def _lista(texto) -> list:
    try:
        valor = json.loads(texto or "[]")
    except (TypeError, ValueError):
        return []
    return valor if isinstance(valor, list) else []


def _vacio(valor) -> bool:
    return valor is None or str(valor).strip() == "" or str(valor).strip().lower() == PENDIENTE


def _auditar(conn, accion: str, entidad_id: str, detalle: dict, usuario: str):
    conn.execute("""INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
                    VALUES (?, ?, ?, ?, ?, ?)""", (_ahora(), usuario, MODULO_AUDITORIA, accion, entidad_id, _json(detalle)))


def _con_conexion(funcion):
    """Ejecuta funcion(conn) en una transacción corta (BEGIN IMMEDIATE) y devuelve su resultado."""
    conn = get_connection()
    conn.isolation_level = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            resultado = funcion(conn)
            conn.execute("COMMIT")
            return resultado
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


# ---------- Niveles (S-4 de la visita ↔ SOTANO S4 del plano) ----------

def niveles_de_diseno(nivel_visita: str) -> set:
    """
    Rótulos de nivel del plano que corresponden al nivel de la visita. El lector solo da niveles 'S-n' (T3) y el
    extractor rotula los sótanos 'SOTANO Sn' (título impreso de la hoja). Solo se aceptan esas escrituras del MISMO
    sótano; cualquier otro nivel se compara literal. Nunca se expande un rango (NIVEL 4@8) por cuenta propia.
    """
    n = " ".join((nivel_visita or "").upper().split())
    m = _RE_NIVEL_SOTANO.fullmatch(n)
    if not m:
        return {n}
    k = int(m.group(1))
    return {f"S-{k}", f"SOTANO S{k}", f"SOTANO S-{k}", f"SOTANO -{k}"}


def clave_nivel_completa(nivel_visita: str) -> Optional[str]:
    """Clave de nivel para el FI (Evaluación 16): siempre completa, 'SOTANO -4', nunca '-4'."""
    m = _RE_NIVEL_SOTANO.fullmatch(" ".join((nivel_visita or "").upper().split()))
    return f"SOTANO -{int(m.group(1))}" if m else None


# ---------- Trabajos y eventos ----------

def _evento(trabajo_id: str, tipo: str, datos: dict) -> int:
    def escribir(conn):
        n = conn.execute("SELECT COALESCE(MAX(n), 0) + 1 FROM trabajo_eventos WHERE trabajo_id = ?",
                         (trabajo_id,)).fetchone()[0]
        conn.execute("INSERT INTO trabajo_eventos (trabajo_id, n, tipo, datos_json, creado) VALUES (?, ?, ?, ?, ?)",
                     (trabajo_id, n, tipo, _json(datos), _ahora()))
        return n
    return _con_conexion(escribir)


def obtener_trabajo(trabajo_id: str) -> Optional[Dict]:
    conn = get_connection()
    try:
        fila = conn.execute("SELECT * FROM trabajos WHERE id = ?", (trabajo_id,)).fetchone()
        if fila is None:
            return None
        n = conn.execute("SELECT COUNT(*) FROM trabajo_eventos WHERE trabajo_id = ?", (trabajo_id,)).fetchone()[0]
        d = dict(fila)
        d["visitas"] = _lista(d.pop("visitas_json"))
        d["resumen"] = _dict(d.pop("resumen_json"))
        d["eventos"] = n
        return d
    finally:
        conn.close()


def listar_eventos(trabajo_id: str, desde: int = 0) -> Dict:
    """Eventos con número MAYOR que `desde` (la pantalla pide desde el último que ya tiene)."""
    conn = get_connection()
    try:
        filas = conn.execute("""SELECT n, tipo, datos_json, creado FROM trabajo_eventos WHERE trabajo_id = ? AND n > ?
                                ORDER BY n""", (trabajo_id, desde)).fetchall()
        estado = conn.execute("SELECT estado FROM trabajos WHERE id = ?", (trabajo_id,)).fetchone()
    finally:
        conn.close()
    eventos = [{"n": f["n"], "tipo": f["tipo"], "creado": f["creado"], **_dict(f["datos_json"])} for f in filas]
    return {"trabajo_id": trabajo_id, "estado": estado["estado"] if estado else None, "eventos": eventos,
            "ultimo": eventos[-1]["n"] if eventos else desde}


def visitas_de_la_cola(proyecto_id: Optional[str] = None) -> List[str]:
    conn = get_connection()
    try:
        filtro, params = "", list(ESTADOS_COLA)
        if proyecto_id:
            filtro, params = " AND proyecto_id = ?", params + [proyecto_id]
        filas = conn.execute(f"""SELECT id FROM visitas WHERE estado IN (?, ?){filtro}
                                 ORDER BY fecha_visita, numero, id""", params).fetchall()
        return [f["id"] for f in filas]
    finally:
        conn.close()


def lanzar_trabajo(visita_ids: List[str], tipo: str = "visita", usuario: Optional[str] = None,
                   en_hilo: bool = True) -> Dict:
    """
    Crea el trabajo y lo arranca en un hilo. Comprueba que no haya otro corriendo y que cada visita exista y esté en
    un estado procesable (Sin procesar, En cola o Con dudas). Lanza TrabajoEnCurso, LookupError o VisitaNoProcesable.
    """
    usuario = usuario or usuario_auditoria()
    with _cerrojo:
        conn = get_connection()
        try:
            corriendo = conn.execute("SELECT id FROM trabajos WHERE estado = ?", (CORRIENDO,)).fetchone()
            if corriendo:
                raise TrabajoEnCurso(f"Ya hay un trabajo corriendo ({corriendo['id']}); espera a que termine.")
            for vid in visita_ids:
                fila = conn.execute("SELECT estado FROM visitas WHERE id = ?", (vid,)).fetchone()
                if fila is None:
                    raise LookupError(f"No existe la visita '{vid}'.")
                if fila["estado"] not in ESTADOS_PROCESABLES:
                    raise VisitaNoProcesable(f"La visita '{vid}' está '{fila['estado']}': solo se procesan las "
                                             f"visitas {', '.join(ESTADOS_PROCESABLES)}.")
            trabajo_id = f"trab-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
            conn.execute("""INSERT INTO trabajos (id, tipo, visitas_json, estado, usuario, creado)
                            VALUES (?, ?, ?, ?, ?, ?)""", (trabajo_id, tipo, _json(visita_ids), CORRIENDO, usuario, _ahora()))
            _auditar(conn, "LANZAR_TRABAJO", trabajo_id, {"tipo": tipo, "visitas": visita_ids}, usuario)
            conn.commit()
        finally:
            conn.close()
        hilo = threading.Thread(target=ejecutar_trabajo, args=(trabajo_id,), name=trabajo_id, daemon=True)
        _hilos[trabajo_id] = hilo
    if en_hilo:
        hilo.start()
    else:
        hilo.run()
    return obtener_trabajo(trabajo_id)


def esperar(trabajo_id: str, timeout: Optional[float] = None) -> Optional[Dict]:
    """Espera a que termine el hilo del trabajo (pruebas y línea de comandos)."""
    hilo = _hilos.get(trabajo_id)
    if hilo is not None and hilo.is_alive():
        hilo.join(timeout)
    return obtener_trabajo(trabajo_id)


def marcar_huerfanos(usuario: Optional[str] = None) -> Dict:
    """
    Al arrancar el servidor: un trabajo que quedó 'corriendo' (el servidor se cerró a mitad) pasa a 'fallido' y sus
    visitas 'En proceso' vuelven al estado que tenían antes de empezar. Idempotente.
    """
    usuario = usuario or usuario_auditoria()

    def corregir(conn):
        trabajos = [f["id"] for f in conn.execute("SELECT id FROM trabajos WHERE estado = ?", (CORRIENDO,))]
        restauradas = []
        for fila in conn.execute("SELECT id, origen_datos_json FROM visitas WHERE estado = ?", (ESTADO_EN_PROCESO,)).fetchall():
            origen = _dict(fila["origen_datos_json"])
            marca = origen.get("procesador") if isinstance(origen.get("procesador"), dict) else {}
            if marca.get("trabajo") in trabajos and marca.get("estado_anterior"):
                conn.execute("UPDATE visitas SET estado = ?, actualizado = ? WHERE id = ?",
                             (marca["estado_anterior"], _ahora(), fila["id"]))
                restauradas.append(fila["id"])
        for t in trabajos:
            conn.execute("UPDATE trabajos SET estado = ?, terminado = ?, error = ? WHERE id = ?",
                         (FALLIDO, _ahora(), "el servidor se cerró mientras el trabajo corría", t))
        if trabajos:
            _auditar(conn, "TRABAJOS_HUERFANOS", ",".join(trabajos), {"trabajos": trabajos, "visitas": restauradas}, usuario)
        return {"trabajos": trabajos, "visitas_restauradas": restauradas}
    return _con_conexion(corregir)


def ejecutar_trabajo(trabajo_id: str):
    """Cuerpo del hilo: procesa las visitas en orden y cierra el trabajo. Un error de una visita no detiene las demás."""
    trabajo = obtener_trabajo(trabajo_id)
    usuario = trabajo["usuario"]
    resumen = {"visitas": [], "pdf": [], "dudas": 0}
    estado, error = TERMINADO, ""
    try:
        conn = get_connection()
        try:  # un respaldo por trabajo (no uno por visita), antes de escribir nada
            respaldo = _respaldar_bd(conn, Path(config.obtener_db_path()))
        finally:
            conn.close()
        resumen["respaldo"] = respaldo.name
        for vid in trabajo["visitas"]:
            try:
                r = ProcesoVisita(trabajo_id, vid, usuario).ejecutar()
            except Exception as exc:  # noqa: BLE001 — se registra y se sigue con la siguiente visita
                r = {"visita_id": vid, "estado": None, "error": f"{type(exc).__name__}: {exc}"}
                estado, error = FALLIDO, r["error"]
                _evento(trabajo_id, "visita_fin", r)
            resumen["visitas"].append(r)
            resumen["pdf"].extend(r.get("pdf", []))
            resumen["dudas"] += len(r.get("dudas", []))
    except Exception as exc:  # noqa: BLE001
        estado, error = FALLIDO, f"{type(exc).__name__}: {exc}"
    _evento(trabajo_id, "fin", {"estado": estado, "error": error, "resumen": resumen})

    def cerrar(conn):
        conn.execute("UPDATE trabajos SET estado = ?, terminado = ?, resumen_json = ?, error = ? WHERE id = ?",
                     (estado, _ahora(), _json(resumen), error, trabajo_id))
        _auditar(conn, "TERMINAR_TRABAJO", trabajo_id, {"estado": estado, "error": error, "resumen": resumen}, usuario)
    _con_conexion(cerrar)


# ---------- Respuestas de Steven (O4) ----------

def interpretar_respuesta(texto: str) -> Optional[Dict]:
    """
    Lee la respuesta de Steven a una duda de identificación SIN interpretar más allá de lo estricto:
    - 'pertenece al anterior' -> {"anterior": True}
    - el uid de un elemento de diseño ('ed-…') -> {"uid"}
    - '<ID> <cruce>' (C1 A4, misma regla que el lector) o '<ID> —' -> {"id", "ejes"}
    - '<ID>' solo -> {"id", "ejes": None} (vale solo si en ese nivel hay un único elemento con ese ID y es de ejes '—')
    Cualquier otra cosa -> None (no se aplica y se pregunta de nuevo).
    """
    t = " ".join((texto or "").replace("’", "'").split())
    if not t:
        return None
    if t.upper().rstrip(".") == RESPUESTA_ANTERIOR:
        return {"anterior": True}
    if _RE_UID.fullmatch(t):
        return {"uid": t.lower()}
    tokens = t.upper().split()
    if len(tokens) == 2 and _RE_ID.fullmatch(tokens[0]) and tokens[1] in (EJE_LOSA, "-", "--"):
        return {"id": tokens[0], "ejes": EJE_LOSA}
    datos = lector_visita.interpretar_etiqueta(t)
    if datos["id_elemento"] != PENDIENTE and datos["ejes"] != PENDIENTE:
        return {"id": datos["id_elemento"], "ejes": datos["ejes"]}
    if len(tokens) == 1 and _RE_ID.fullmatch(tokens[0]):
        return {"id": tokens[0], "ejes": None}
    return None


# ---------- Proceso de una visita ----------

class ProcesoVisita:
    def __init__(self, trabajo_id: str, visita_id: str, usuario: str):
        self.trabajo_id, self.visita_id, self.usuario = trabajo_id, visita_id, usuario
        self.dudas: List[int] = []          # dudas (nuevas o ya abiertas) que esta corrida señaló
        self.campos: set = set()            # campos de esas dudas: lo que no se vuelva a señalar se cierra solo
        self.pdf: List[Dict] = []
        self.avisos: List[str] = []

    # --- BD ---
    def _visita(self, conn=None):
        if conn is not None:
            return conn.execute("SELECT * FROM visitas WHERE id = ?", (self.visita_id,)).fetchone()
        return _con_conexion(lambda c: c.execute("SELECT * FROM visitas WHERE id = ?", (self.visita_id,)).fetchone())

    def _dudas_abiertas(self, conn) -> List:
        return conn.execute("""SELECT * FROM dudas_y_hallazgos WHERE visita_id = ? AND categoria = ? AND resuelta = 0
                               ORDER BY id""", (self.visita_id, DUDA)).fetchall()

    def duda(self, campo: str, id_elemento: str, texto: str, refs: Optional[Dict] = None) -> int:
        """Abre una DUDA_BLOQUEANTE si no hay una ABIERTA del mismo campo; emite el evento `duda` en los dos casos."""
        def abrir(conn):
            v = self._visita(conn)
            fila = conn.execute("""SELECT id FROM dudas_y_hallazgos WHERE visita_id = ? AND campo_afectado = ?
                                   AND categoria = ? AND resuelta = 0""", (self.visita_id, campo, DUDA)).fetchone()
            if fila:
                return fila["id"], False
            cur = conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria,
                                  campo_afectado, descripcion_pregunta, creado) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                               (v["proyecto_id"], self.visita_id, id_elemento, DUDA, campo, texto, _ahora()))
            _auditar(conn, "ABRIR_DUDA", str(cur.lastrowid), {"visita_id": self.visita_id, "campo": campo,
                                                               "pregunta": texto, "trabajo": self.trabajo_id}, self.usuario)
            return cur.lastrowid, True
        duda_id, nueva = _con_conexion(abrir)
        self.campos.add(campo)
        self.dudas.append(duda_id)
        pregunta = _con_conexion(lambda c: c.execute("SELECT descripcion_pregunta FROM dudas_y_hallazgos WHERE id = ?",
                                                     (duda_id,)).fetchone()[0])
        _evento(self.trabajo_id, "duda", {"visita_id": self.visita_id, "duda_id": duda_id, "nueva": nueva,
                                          "campo": campo, "pregunta": pregunta, **(refs or {})})
        return duda_id

    def cerrar_propias(self, pagina: Optional[str], vigentes: set, clases: Tuple[str, ...]):
        """
        Cierra las dudas que abrió el procesador y cuya causa ya no existe en esta corrida. pagina='pNNN' y clases
        ('cruce', 'diseno') o ('obra', 'excluido', 'generacion') para un elemento; pagina=None para las de la visita.
        Nunca cierra una duda del lector, del sync ni de la Mesa.
        """
        def cerrar(conn):
            cerradas = []
            for d in self._dudas_abiertas(conn):
                campo = d["campo_afectado"]
                if campo in vigentes:
                    continue
                el = campo_de_elemento(campo)
                if pagina is None:
                    if not es_propia_de_visita(campo):
                        continue
                elif el is None or el[1] != pagina or el[0] not in clases:
                    continue
                conn.execute("UPDATE dudas_y_hallazgos SET resuelta = 1, respuesta_usuario = ?, resuelto_en = ? WHERE id = ?",
                             (RESPUESTA_CIERRE, _ahora(), d["id"]))
                _auditar(conn, "CERRAR_DUDA", str(d["id"]), {"visita_id": self.visita_id, "campo": campo,
                                                             "motivo": RESPUESTA_CIERRE, "trabajo": self.trabajo_id}, self.usuario)
                cerradas.append(d["id"])
            return cerradas
        return _con_conexion(cerrar)

    # --- Flujo ---
    def ejecutar(self) -> Dict:
        visita = self._visita()
        if visita is None:
            raise LookupError(f"No existe la visita '{self.visita_id}'.")
        estado_anterior = visita["estado"]
        _evento(self.trabajo_id, "visita_inicio", {"visita_id": self.visita_id, "numero": visita["numero"],
                                                   "carpeta": visita["nombre_carpeta"], "estado_anterior": estado_anterior})

        def empezar(conn):
            origen = _dict(conn.execute("SELECT origen_datos_json FROM visitas WHERE id = ?",
                                        (self.visita_id,)).fetchone()[0])
            origen["procesador"] = {"trabajo": self.trabajo_id, "estado_anterior": estado_anterior, "inicio": _ahora()}
            conn.execute("UPDATE visitas SET estado = ?, origen_datos_json = ?, actualizado = ? WHERE id = ?",
                         (ESTADO_EN_PROCESO, _json(origen), _ahora(), self.visita_id))
        _con_conexion(empezar)
        try:
            return self._procesar(visita)
        except Exception:
            _con_conexion(lambda c: c.execute("UPDATE visitas SET estado = ?, actualizado = ? WHERE id = ?",
                                              (estado_anterior, _ahora(), self.visita_id)))
            raise

    def _procesar(self, visita) -> Dict:
        self.pdf_visita = self._pdf_de_la_visita(visita)
        leida = _con_conexion(lambda c: c.execute("SELECT COUNT(*) FROM elementos_visita WHERE visita_id = ?",
                                                  (self.visita_id,)).fetchone()[0])
        if not leida:
            self._correr_lector(visita)
        self.contexto = self._contexto(visita)

        elementos = _con_conexion(lambda c: c.execute("""SELECT * FROM elementos_visita WHERE visita_id = ?
                                                         ORDER BY orden_en_log""", (self.visita_id,)).fetchall())
        resultados: Dict[str, Dict] = {}
        for ev in elementos:
            resultados[ev["uid"]] = self._elemento(ev)

        # Reintento antes de cerrar: los elementos en espera cuya duda ya respondió Steven en la Mesa (PATCH)
        cambio = True
        while cambio:
            cambio = False
            for ev in elementos:
                r = resultados[ev["uid"]]
                if r["estado"] == "espera" and r["esperando"] and self._todas_resueltas(r["esperando"]):
                    resultados[ev["uid"]] = self._elemento(ev, reintento=True)
                    cambio = cambio or resultados[ev["uid"]]["estado"] != "espera"

        fichas = self._fichas_en_orden(elementos, resultados)
        bloqueos = self._bloqueos_de_visita(visita)
        en_espera = [r for r in resultados.values() if r["estado"] == "espera"]
        if not elementos:
            self.duda("procesador:sin_elementos", "(visita)", "La visita no tiene elementos leídos: no hay nada que "
                      f"informar ({PENDIENTE}).")
            bloqueos.append("sin elementos")
        generado = {}
        if not bloqueos and not en_espera and fichas:
            generado = self._generar(visita, fichas)
        else:
            motivo = "; ".join(bloqueos + ([f"{len(en_espera)} elementos en espera"] if en_espera else []))
            self.avisos.append(f"No se generó ningún documento: {motivo}.")
            _evento(self.trabajo_id, "aviso", {"visita_id": self.visita_id, "texto": self.avisos[-1]})
        return self._cerrar(visita, resultados, generado)

    # --- 1. Lector ---
    def _pdf_de_la_visita(self, visita) -> Optional[str]:
        pdfs = [a for a in _lista(visita["archivos_json"]) if str(a.get("nombre", "")).lower().endswith(".pdf")]
        if len(pdfs) != 1:
            return None
        return str(pdfs[0].get("ruta") or Path(visita["ruta_carpeta"]) / pdfs[0]["nombre"])

    def _correr_lector(self, visita):
        if self.pdf_visita is None:
            self.duda(lector_visita.CAMPO_PDF_VISITA, "(visita)",
                      f"La visita '{visita['nombre_carpeta']}' no tiene un único PDF ({len(_lista(visita['archivos_json']))} "
                      "archivos): indica cuál leer; no se elige uno solo.")
            return
        try:
            r = lector_visita.cargar_visita(self.visita_id, usuario=self.usuario, respaldar=False)
            _evento(self.trabajo_id, "aviso", {"visita_id": self.visita_id,
                                               "texto": f"Visita leída: {r['grupos']} elementos y {r['paginas']} fotos."})
        except ValueError as exc:  # el lector ya dejó su duda `lector_visita`
            self.duda(lector_visita.CAMPO_PDF_VISITA, "(visita)", str(exc), {"visita_pdf": {"ruta": self.pdf_visita}})
        except (OSError, pymupdf.FileNotFoundError, pymupdf.FileDataError) as exc:  # PDF ausente o ilegible
            self.duda(lector_visita.CAMPO_PDF_VISITA, "(visita)",
                      f"No se pudo abrir el PDF de la visita '{Path(self.pdf_visita).name}': {exc}",
                      {"visita_pdf": {"ruta": self.pdf_visita}})

    # --- 2. Cruce ---
    def _contexto(self, visita) -> Dict:
        def leer(conn):
            proyecto = dict(conn.execute("SELECT * FROM proyectos WHERE id = ?", (visita["proyecto_id"],)).fetchone())
            plano = conn.execute("SELECT * FROM planos WHERE proyecto_id = ? AND estado = 'vigente'",
                                 (visita["proyecto_id"],)).fetchone()
            return {"proyecto": proyecto, "plano": dict(plano) if plano else None}
        return _con_conexion(leer)

    def _refs(self, ev, candidato=None) -> Dict:
        """Lo que la pantalla necesita para mostrar el plano y la página de la visita junto a la duda."""
        paginas = [f.get("pagina") for f in _lista(ev["fotos_json"])]
        refs = {"elemento": {"uid": ev["uid"], "orden_en_log": ev["orden_en_log"], "etiqueta": ev["etiqueta_original"],
                             "id_elemento": ev["id_elemento"], "nivel": ev["nivel"], "ejes": ev["ejes"]},
                "visita_pdf": {"ruta": self.pdf_visita, "pagina": ev["orden_en_log"], "paginas": paginas}}
        plano = self.contexto["plano"]
        refs["plano"] = {"plano_id": plano["id"] if plano else None, "pagina": None, "bbox": None, "recuadro": None}
        if candidato is not None:
            fuente = _dict(candidato["fuente_json"])
            pagina = None
            m = _RE_PAGINA_TABLA.match(str(fuente.get("tabla", "")))
            if m:
                pagina = int(m.group(1))
            recuadro = _dict(candidato["recorte_planta_json"]) or None
            refs["plano"] = {"plano_id": candidato["plano_id"], "pagina": pagina, "bbox": fuente.get("bbox_id"),
                             "recuadro": recuadro, "uid_diseno": candidato["uid"]}
        return refs

    def _respuesta_vigente(self, conn, pagina: str) -> Optional[Dict]:
        """La respuesta más reciente de Steven a una duda de identificación del elemento (lector o cruce)."""
        filas = conn.execute("""SELECT * FROM dudas_y_hallazgos WHERE visita_id = ? AND categoria = ? AND resuelta = 1
                                AND (campo_afectado = ? OR campo_afectado LIKE ?) AND respuesta_usuario != ?
                                ORDER BY id DESC""",
                             (self.visita_id, DUDA, f"{PREFIJO_LECTOR}{pagina}", f"cruce:{pagina}%", RESPUESTA_CIERRE)).fetchall()
        return dict(filas[0]) if filas else None

    def _todas_resueltas(self, ids: List[int]) -> bool:
        def leer(conn):
            marcas = ",".join("?" * len(ids))
            return conn.execute(f"SELECT COUNT(*) FROM dudas_y_hallazgos WHERE id IN ({marcas}) AND resuelta = 0",
                                ids).fetchone()[0] == 0
        return _con_conexion(leer)

    def _elemento(self, ev, reintento: bool = False) -> Dict:
        pagina = f"p{ev['orden_en_log']:03d}"
        etiqueta = ev["etiqueta_original"] or "(sin etiqueta)"
        _evento(self.trabajo_id, "elemento_inicio", {"visita_id": self.visita_id, "reintento": reintento,
                                                     **self._refs(ev)})
        vigentes: set = set()
        esperando: List[int] = []

        def espera(campo, texto, candidato=None):
            vigentes.add(campo)
            esperando.append(self.duda(campo, etiqueta, texto, self._refs(ev, candidato)))

        def fin(resultado):
            self.cerrar_propias(pagina, vigentes, ("cruce", "diseno"))
            if resultado["estado"] == "espera":
                resultado["esperando"] = esperando
            return resultado

        # Identificación: lo que dio el lector sin interpretar, o la respuesta de Steven (O4); nunca la etiqueta
        abiertas_lector = _con_conexion(lambda c: c.execute(
            """SELECT id FROM dudas_y_hallazgos WHERE visita_id = ? AND campo_afectado = ? AND categoria = ?
               AND resuelta = 0""", (self.visita_id, f"{PREFIJO_LECTOR}{pagina}", DUDA)).fetchall())
        if abiertas_lector:
            for f in abiertas_lector:  # la duda es del lector: se señala, no se duplica
                esperando.append(f["id"])
                self.dudas.append(f["id"])
                _evento(self.trabajo_id, "duda", {"visita_id": self.visita_id, "duda_id": f["id"], "nueva": False,
                                                  "campo": f"{PREFIJO_LECTOR}{pagina}", **self._refs(ev)})
            return fin({"estado": "espera"})

        ident = None
        if ev["id_elemento"] != PENDIENTE and ev["ejes"] != PENDIENTE:
            ident = {"id": ev["id_elemento"], "ejes": ev["ejes"]}
        else:
            respuesta = _con_conexion(lambda c: self._respuesta_vigente(c, pagina))
            if respuesta is None:
                espera(f"cruce:{pagina}", f"La etiqueta '{etiqueta}' no da ID y ejes sin interpretar: indica el elemento "
                                          "(ID y cruce, p. ej. 'C1 A4'; el uid del elemento de diseño; o 'pertenece al anterior').")
                return fin({"estado": "espera"})
            ident = interpretar_respuesta(respuesta["respuesta_usuario"])
            if ident is None:
                espera(f"cruce:{pagina}:respuesta",
                       f"La respuesta '{respuesta['respuesta_usuario']}' (duda {respuesta['id']}) no se puede aplicar sin "
                       "interpretar. Escribe el ID y el cruce ('C1 A4'), el ID y '—' para una losa ('L5 —'), el uid del "
                       "elemento de diseño ('ed-…') o 'pertenece al anterior'.")
                return fin({"estado": "espera"})
            if ident.get("anterior"):
                _evento(self.trabajo_id, "elemento_listo", {"visita_id": self.visita_id, "anterior": True,
                                                            **self._refs(ev)})
                return fin({"estado": "anterior"})

        if _vacio(ev["nivel"]):
            espera(f"cruce:{pagina}:nivel", f"El nivel del elemento '{etiqueta}' está {PENDIENTE}: no se cruza con el "
                                            "plano sin el nivel (§4.2).")
            return fin({"estado": "espera"})

        candidatos = self._candidatos(ev, ident)
        if len(candidatos) != 1:
            que = (f"el uid '{ident['uid']}'" if ident.get("uid") else
                   f"ID '{ident['id']}'" + (f", ejes '{ident['ejes']}'" if ident.get("ejes") else ""))
            if candidatos:
                texto = (f"Elemento '{etiqueta}': {len(candidatos)} elementos de diseño con {que} en el nivel "
                         f"{ev['nivel']} ({', '.join(c['uid'] + ' ' + c['ejes'] for c in candidatos)}). Indica el uid "
                         "del que corresponde; no se elige uno solo.")
            else:
                texto = (f"Elemento '{etiqueta}': ningún elemento de diseño con {que} en el nivel {ev['nivel']} "
                         "(ID + Nivel + Ejes, §4.2). Revisa el plano o indica el elemento.")
            espera(f"cruce:{pagina}", texto, candidatos[0] if len(candidatos) > 0 else None)
            return fin({"estado": "espera"})
        c = candidatos[0]
        if ident.get("ejes") is None and not ident.get("uid") and c["ejes"] != EJE_LOSA:
            espera(f"cruce:{pagina}", f"Elemento '{etiqueta}': la respuesta da solo el ID '{ident['id']}' y el elemento "
                                      f"de diseño tiene ejes '{c['ejes']}': indica también el cruce (§4.2).", c)
            return fin({"estado": "espera"})

        # Regla de Oro: solo se informa con datos confirmados
        estados = _dict(c["estado_campos_json"])
        pendientes = sorted(k for k, v in estados.items() if v != CONFIRMADO)
        if pendientes or c["revisar_motivo"]:
            lista = ", ".join(pendientes[:12]) + (f" y {len(pendientes) - 12} más" if len(pendientes) > 12 else "")
            texto = (f"El elemento de diseño {c['id_elemento']} ({c['nivel_rango']}, {c['uid']}) tiene datos sin "
                     f"confirmar: {lista or 'ninguno'}" + (f"; {c['revisar_motivo']}" if c["revisar_motivo"] else "") +
                     ". Confírmalos en el plano (lote o Mesa); no se informa con datos sin confirmar.")
            espera(f"diseno:{pagina}", texto, c)
            return fin({"estado": "espera"})

        ficha, faltas = self._ficha(ev, c)
        if faltas:
            for campo, texto in faltas:
                espera(campo, texto, c)
            return fin({"estado": "espera"})
        _evento(self.trabajo_id, "elemento_listo", {"visita_id": self.visita_id, "titulo": ficha["titulo"],
                                                    **self._refs(ev, c)})
        return fin({"estado": "listo", "ficha": ficha, "uid_diseno": c["uid"]})

    def _candidatos(self, ev, ident: Dict) -> List:
        proyecto_id = self.contexto["proyecto"]["id"]
        niveles = niveles_de_diseno(ev["nivel"])

        def leer(conn):
            if ident.get("uid"):
                filas = conn.execute("SELECT * FROM elementos_diseno WHERE proyecto_id = ? AND LOWER(uid) = ?",
                                     (proyecto_id, ident["uid"])).fetchall()
            else:
                filas = conn.execute("SELECT * FROM elementos_diseno WHERE proyecto_id = ? AND UPPER(id_elemento) = ?",
                                     (proyecto_id, ident["id"].upper())).fetchall()
            filas = [f for f in filas if " ".join(f["nivel_rango"].upper().split()) in niveles]
            if ident.get("uid"):
                return filas
            if ident.get("ejes") is None:  # solo el ID: _elemento exige que el único candidato sea de ejes '—'
                return filas
            return [f for f in filas if f["ejes"] == ident["ejes"]]
        return _con_conexion(leer)

    def _ficha(self, ev, c) -> Tuple[Optional[Dict], List[Tuple[str, str]]]:
        """Arma la ficha del generador (Capa 1 + Capa 2; la Capa 3 la calcula el generador). Devuelve (ficha, faltas)."""
        pagina = f"p{ev['orden_en_log']:03d}"
        faltas: List[Tuple[str, str]] = []
        datos = _dict(c["datos_diseno_json"])
        tipo = c["tipo_elemento"]
        fila = stp_mived._tipo_de_fila(tipo)
        ficha = {"titulo": f"{tipo}-{c['id_elemento']}" + ("" if c["ejes"] == EJE_LOSA else f"-{c['ejes']}"),
                 "tipo_elemento": tipo, "ejes": c["ejes"], "visita_id": self.visita_id, "fila_stp": fila,
                 "uid_diseno": c["uid"], "orden_en_log": ev["orden_en_log"], "plano": {}, "obra": {}, "medidas": {}}
        if fila is not None:  # un tipo no soportado lo excluye el propio STP (con su duda)
            mapeo = MAPEO_DISENO_A_STP.get(fila)
            if not mapeo:
                faltas.append((f"diseno:{pagina}:mapeo",
                               f"No está definido de qué datos del plano sale cada fila del STP-MIVED para '{tipo}' "
                               f"(p. ej. si 'DIR. X' es la fila de barras arriba o abajo): decisión pendiente de Steven "
                               f"({PENDIENTE})."))
            else:
                # Capa 2 (contrato de medidas_acero_campo_json): {letra: metros medidos sobre el acero, "obra": {letra:
                # texto de la columna OBRA}}. Hoy ningún módulo lo llena (la captura de OBRA es una decisión pendiente).
                medidas_obra = _dict(ev["medidas_acero_campo_json"])
                obra_txt = medidas_obra.get("obra") if isinstance(medidas_obra.get("obra"), dict) else {}
                ficha["obra"] = {k: str(v) for k, v in obra_txt.items() if not _vacio(v)}
                for letra, campo in mapeo.get("filas", {}).items():
                    if not _vacio(datos.get(campo)):
                        ficha["plano"][letra] = str(datos[campo])
                for letra, campo in mapeo.get("medidas", {}).items():
                    try:
                        valor = float(str(datos.get(campo)).replace(",", "."))
                    except (TypeError, ValueError):
                        continue  # el generador pide la dimensión que falte con su duda
                    medida = medidas_obra.get(letra)
                    ficha["medidas"][letra] = {"valor_plano_m": valor,
                                               "medida_acero_campo_m": medida if isinstance(medida, (int, float))
                                                and not isinstance(medida, bool) else None}
                if mapeo.get("barras"):
                    barras = datos.get(mapeo["barras"])
                    if isinstance(barras, list) and all(isinstance(b, list) and len(b) == 2 for b in barras):
                        ficha["barras"] = [(b[0], b[1]) for b in barras]
                    else:
                        faltas.append((f"diseno:{pagina}:barras", f"Las barras de {c['id_elemento']} no están como "
                                                                  f"lista [[n, diámetro], …] ({PENDIENTE})."))

        # M3 / M4: recuadros confirmados en el visor (T5n) sobre el plano vigente
        plano = self.contexto["plano"]
        for clave, columna, nombre in (("localizacion", "recorte_planta_json", "LOCALIZACION"),
                                       ("detalle", "recorte_detalle_json", "DETALLE")):
            r = _dict(c[columna])
            if not plano or r.get("estado") != CONFIRMADO or r.get("plano_id") != plano["id"] or not r.get("rect"):
                faltas.append((f"diseno:{pagina}:{clave}", f"El recuadro de {nombre} de {c['id_elemento']} no está "
                                                          "confirmado en el plano vigente (visor del plano)."))
                continue
            ruta = plano["vectorial_ruta"]
            if clave == "localizacion":
                dpi = m3_localizacion.DPI_PLANTA
                ficha[clave] = {"pdf": ruta, "pagina": r["pagina"] - 1, "caja": [v * dpi / 72.0 for v in r["rect"]]}
            else:
                ficha[clave] = {"pdf": ruta, "pagina": r["pagina"] - 1, "region": list(r["rect"])}

        # M1: fotos del log desde la caché del lector (nunca del plano)
        cache = lector_visita.obtener_cache_raiz()
        fotos = [str(cache / f["cache"]) for f in _lista(ev["fotos_json"]) if f.get("cache")]
        faltan = [Path(f).name for f in fotos if not Path(f).is_file()]
        if not fotos or faltan:
            faltas.append((f"diseno:{pagina}:fotos", f"Faltan fotos del elemento en la caché ({', '.join(faltan) or 'ninguna'}"
                                                    "): vuelve a leer la visita."))
        ficha["fotos"] = fotos
        return (None if faltas else ficha), faltas

    def _fichas_en_orden(self, elementos, resultados) -> List[Dict]:
        """Fichas en el orden del log; las fotos de un elemento 'pertenece al anterior' se suman a la ficha anterior."""
        fichas, ultima = [], None
        for ev in elementos:
            r = resultados[ev["uid"]]
            if r["estado"] == "listo":
                ultima = dict(r["ficha"])
                fichas.append(ultima)
            elif r["estado"] == "anterior" and ultima is not None:
                cache = lector_visita.obtener_cache_raiz()
                ultima["fotos"] = list(ultima["fotos"]) + [str(cache / f["cache"]) for f in _lista(ev["fotos_json"])
                                                           if f.get("cache")]
            elif r["estado"] == "anterior":
                r["estado"] = "espera"
                r["esperando"] = [self.duda(f"cruce:p{ev['orden_en_log']:03d}:anterior", ev["etiqueta_original"],
                                            "La respuesta dice 'pertenece al anterior', pero no hay un elemento anterior "
                                            "con ficha en esta visita.", self._refs(ev))]
        return fichas

    # --- Comprobaciones de la visita (fecha, clase, P3, cabecera, formatos) ---
    def _bloqueos_de_visita(self, visita) -> List[str]:
        visita = self._visita()
        bloqueos = []
        if visita["clase"] not in (CLASE_PARCIAL, CLASE_COMPLETIVO):
            if visita["clase"] != PENDIENTE:  # la clase pendiente ya tiene su duda del sync
                self.duda("procesador:clase", "(visita)",
                          f"La visita es '{visita['clase']}': el STP-MIVED y el FI se generan por clase (Parcial o "
                          "Completivo). Hay que separar los elementos de cada clase; no se decide solo.")
            bloqueos.append(f"clase {visita['clase']}")
        if visita["fecha_visita"] == PENDIENTE:
            bloqueos.append("fecha pendiente")
        if interpretar_nombre_carpeta_visita(visita["nombre_carpeta"])["descripcion"] == PENDIENTE:
            self.duda("procesador:elementos_txt", "(visita)", "El nombre de la carpeta no trae los elementos y el nivel "
                                                              f"para el nombre del informe ({PENDIENTE}).")
            bloqueos.append("elementos del nombre pendientes")
        bloqueos += self._p3(visita)
        formatos = _lista(visita["formatos_solicitados"])
        desconocidos = [f for f in formatos if f not in FORMATOS_FI | {FORMATO_STP, FORMATO_CATDIC}]
        if desconocidos:
            self.duda("procesador:formatos", "(visita)", f"Formatos que la fábrica de supervisión no genera: "
                                                         f"{', '.join(desconocidos)} ({PENDIENTE}).")
            bloqueos.append("formatos desconocidos")
        if FORMATO_CATDIC in formatos:
            self.avisos.append("CATDIC-STP está aplazado (Steven, 23/10/2026): se omite.")
            _evento(self.trabajo_id, "aviso", {"visita_id": self.visita_id, "texto": self.avisos[-1]})
        if not [f for f in formatos if f != FORMATO_CATDIC]:
            self.duda("procesador:formatos", "(visita)", "La visita no pide ningún formato que se pueda generar.")
            bloqueos.append("sin formatos")
        p = self.contexto["proyecto"]
        faltan = [c for c in stp_mived.CAMPOS_PROYECTO if c != "carpeta_planos" and _vacio(p.get(c))]
        if not self.contexto["plano"]:
            faltan.append("plano vigente")
        if faltan:
            self.duda("proyecto:cabecera", "(proyecto)", f"Faltan datos de la obra para la cabecera de los informes: "
                                                         f"{', '.join(faltan)} ({PENDIENTE}). Llénalos en los datos del proyecto.")
            bloqueos.append("cabecera del proyecto incompleta")
        # Dudas de la visita (no de un elemento) que siguen abiertas: fecha, clase, estado, archivos, lector…
        abiertas = _con_conexion(self._dudas_abiertas)
        propias = [d for d in abiertas if campo_de_elemento(d["campo_afectado"]) is None
                   and not es_propia_de_visita(d["campo_afectado"])]
        if propias:
            bloqueos.append(f"{len(propias)} dudas de la visita abiertas ({', '.join(sorted({d['campo_afectado'] for d in propias}))})")
        return bloqueos

    def _p3(self, visita) -> List[str]:
        """O5: antes de generar, ¿ya existe en INFORMES\\2.DATA PROCESADA un STP de esta visita? (solo lectura)"""
        origen = _dict(visita["origen_datos_json"])
        decidido = origen.get("estado_mesa") if isinstance(origen.get("estado_mesa"), dict) else {}
        if decidido.get("estado") == ESTADO_SIN_PROCESAR:
            return []  # Steven ya dijo "no corresponde" a los STP candidatos
        carpeta = (self.contexto["proyecto"].get("carpeta_dropbox") or "").strip()
        if not carpeta or visita["fecha_visita"] == PENDIENTE:
            return []
        informes = _escanear_informes(Path(carpeta) / SUBRUTA_INFORMES_PROCESADOS, [])
        evaluacion = evaluar_p3(informes, visita["fecha_visita"], visita["clase"])
        if evaluacion["estado"] == ESTADO_SIN_PROCESAR:
            return []

        def guardar_candidatos(conn):
            o = _dict(conn.execute("SELECT origen_datos_json FROM visitas WHERE id = ?", (self.visita_id,)).fetchone()[0])
            o.update(_origen_estado({**evaluacion, "estado": ESTADO_CON_DUDAS}))
            conn.execute("UPDATE visitas SET origen_datos_json = ? WHERE id = ?", (_json(o), self.visita_id))
        _con_conexion(guardar_candidatos)
        self.duda(CAMPO_ESTADO, "", _descripcion_duda_estado(visita["nombre_carpeta"], visita["fecha_visita"], evaluacion))
        return ["ya hay un STP de su fecha en INFORMES\\2.DATA PROCESADA (P3)"]

    # --- 3. Generación ---
    def _visita_para_generador(self, visita, fichas) -> Dict:
        aaaa, mm, dd = visita["fecha_visita"].split("-")
        return {"id": self.visita_id, "fecha": f"{dd}/{mm}/{aaaa}", "clase": visita["clase"],
                "elementos_txt": interpretar_nombre_carpeta_visita(visita["nombre_carpeta"])["descripcion"],
                "nivel": self._nivel_de_fichas(fichas), "numero_inspeccion": visita["numero"],
                "discrepancias_abiertas": []}

    def _nivel_de_fichas(self, fichas) -> Optional[str]:
        niveles = _con_conexion(lambda c: {f["nivel"] for f in c.execute(
            "SELECT nivel FROM elementos_visita WHERE visita_id = ?", (self.visita_id,))})
        return niveles.pop() if len(niveles) == 1 else None

    def _generar(self, visita, fichas) -> Dict:
        base = config.obtener_salida_pruebas()
        paso = base / CARPETA_DE_PASO / self.trabajo_id
        formatos = _lista(visita["formatos_solicitados"])
        datos_visita = self._visita_para_generador(visita, fichas)
        resultado = {"archivos": [], "limpio": True, "discrepancias": []}
        por_orden = {f["titulo"]: f["orden_en_log"] for f in fichas}

        if FORMATO_STP in formatos:
            proyecto = {**self.contexto["proyecto"],
                        "carpeta_planos": str(Path(self.contexto["plano"]["vectorial_ruta"]).parent.parent)}
            r = stp_mived.generar_stp_mived(proyecto, datos_visita, fichas, carpeta_salida=paso, usuario=self.usuario)
            resultado["discrepancias"] = list(r.get("discrepancias") or [])
            obra: Dict[int, List[str]] = {}
            for d in r["dudas"]:
                orden = por_orden.get(d.get("id_elemento"))
                pag = f"p{orden:03d}" if orden else None
                if d.get("excluido") and pag:
                    self.duda(f"excluido:{pag}", d["id_elemento"], d["descripcion_pregunta"])
                elif d.get("bloquea") is False and pag:
                    obra.setdefault(orden, []).append(d["campo_afectado"])
                else:
                    self.duda(f"generacion:{pag}" if pag else "generacion:STP-MIVED", d.get("id_elemento") or "(visita)",
                              d["descripcion_pregunta"])
            for orden, campos in obra.items():  # UNA duda de OBRA por elemento (la Mesa no se satura)
                titulo = next(t for t, o in por_orden.items() if o == orden)
                self.duda(f"obra:p{orden:03d}", titulo, f"{titulo}: faltan datos de OBRA de la visita ({', '.join(campos)}); "
                                                        f"las celdas quedan vacías en el STP ({PENDIENTE}).")
            for e in r["errores"]:
                self.duda("generacion:STP-MIVED", "(visita)", f"STP-MIVED: {e}")
            for f in fichas:  # las dudas de OBRA / excluido / generación que el STP ya no da, se cierran
                self.cerrar_propias(f"p{f['orden_en_log']:03d}", self.campos, ("obra", "excluido", "generacion"))
            if r["ok"]:
                resultado["archivos"].append({"formato": FORMATO_STP, "ruta": str(r["ruta"])})
            if not r["ok"] or r["dudas"] or r["errores"] or r.get("excluidos"):
                resultado["limpio"] = False

        if any(f in FORMATOS_FI for f in formatos):
            if resultado["limpio"]:
                self._generar_fi(visita, fichas, datos_visita, paso, resultado)
            else:
                self.avisos.append("El FI no se actualiza mientras la visita tenga dudas: es un documento acumulativo.")
                _evento(self.trabajo_id, "aviso", {"visita_id": self.visita_id, "texto": self.avisos[-1]})
        return resultado

    def _generar_fi(self, visita, fichas, datos_visita, paso, resultado):
        clave = clave_nivel_completa(datos_visita["nivel"] or "")
        carpeta = (self.contexto["proyecto"].get("carpeta_dropbox") or "").strip()
        por_fi: Dict[str, List[str]] = {}
        for f in fichas:
            tipo_fi = FI_POR_FILA.get(f["fila_stp"])
            if tipo_fi:
                por_fi.setdefault(tipo_fi, []).append(f["titulo"])
        for tipo_fi, elementos in sorted(por_fi.items()):
            if clave is None or not carpeta:
                self.duda(f"generacion:{tipo_fi}", "(visita)", f"{tipo_fi}: falta la clave de nivel completa o la carpeta "
                                                               f"de Dropbox de la obra ({PENDIENTE}).")
                resultado["limpio"] = False
                continue
            existente, en_blanco, problema = self._fi_de_partida(Path(carpeta), tipo_fi, clave)
            if problema:
                self.duda(f"generacion:{tipo_fi}", "(visita)", problema)
                resultado["limpio"] = False
                continue
            nivel_txt = f"{datos_visita['elementos_txt']} {datos_visita['clase'].upper()}"
            r = fi_mived.actualizar_fi(tipo_fi, self.contexto["proyecto"],
                                       {**datos_visita, "discrepancias_abiertas": resultado["discrepancias"]},
                                       nivel_txt, clave, elementos, existente=existente, en_blanco=en_blanco,
                                       carpeta_salida=paso, usuario=self.usuario)
            if r["ok"]:
                resultado["archivos"].append({"formato": tipo_fi, "ruta": str(r["ruta"]),
                                              "partida": str(existente or en_blanco)})
            else:
                resultado["limpio"] = False
                for e in r["errores"]:
                    self.duda(f"generacion:{tipo_fi}", "(visita)", f"{tipo_fi}: {e}")

    def _fi_de_partida(self, carpeta: Path, tipo_fi: str, clave: str) -> Tuple[Optional[Path], Optional[Path], Optional[str]]:
        """
        P5: el FI existente de ESTE nivel y tipo en FORMULARIOS NO FIRMADOS (Dropbox, solo lectura), en su última
        versión; si no hay, el FI en blanco del proyecto en FORMULARIOS. Nunca el de otro nivel; si hay varios
        documentos distintos del mismo nivel y tipo, no se elige uno.
        """
        grupos: Dict[str, List[Tuple[int, Path]]] = {}
        no_firmados = carpeta / SUBRUTA_FI_NO_FIRMADOS
        for ruta in sorted(no_firmados.glob("*.pdf")) + sorted(no_firmados.glob("*.PDF")) if no_firmados.is_dir() else []:
            if tipo_fi not in ruta.name.upper():
                continue
            try:
                doc = pymupdf.open(str(ruta))
                try:
                    nivel = fi_mived._texto_nivel_existente(doc[0])
                finally:
                    doc.close()
            except Exception:  # noqa: BLE001 — un PDF ilegible no es candidato
                continue
            if nivel is None or fi_mived._clave_en_nivel(clave, nivel) is not None:
                continue
            m = re.match(r"^(?P<base>.*?)(?:\s+v(?P<v>\d+))?\.pdf$", ruta.name, re.IGNORECASE)
            grupos.setdefault(m.group("base").casefold(), []).append((int(m.group("v") or 1), ruta))
        if len(grupos) > 1:
            nombres = "; ".join(sorted(max(g)[1].name for g in grupos.values()))
            return None, None, (f"{tipo_fi}: hay varios formularios distintos de {clave} en FORMULARIOS NO FIRMADOS "
                                f"({nombres}); indica cuál se actualiza.")
        if grupos:
            return max(next(iter(grupos.values())))[1], None, None
        blancos = sorted(p for p in (carpeta / SUBRUTA_FORMULARIOS).glob(f"{tipo_fi}-*.pdf"))
        if len(blancos) != 1:
            return None, None, (f"{tipo_fi}: no hay FI de {clave} en FORMULARIOS NO FIRMADOS y hay {len(blancos)} FI en "
                                f"blanco del proyecto en FORMULARIOS ({PENDIENTE}).")
        return None, blancos[0], None

    # --- 4. Cierre ---
    def _publicar(self, archivo: Dict, con_dudas: bool) -> Dict:
        """Mueve el PDF de la carpeta de paso a la salida de pruebas sin sobrescribir; con dudas lleva ' - CON DUDAS'."""
        origen = Path(archivo["ruta"])
        base = salida.resolver_carpeta_salida()
        nombre = origen.name
        m = re.match(r"^(?P<base>.*?)(?:\s+v\d+)?(?P<ext>\.pdf)$", nombre, re.IGNORECASE)
        nombre = f"{m.group('base')}{SUFIJO_CON_DUDAS if con_dudas else ''}{m.group('ext')}"
        destino = obtener_ruta_salida_sin_sobrescribir(base, nombre)
        os.rename(origen, destino)  # en Windows falla si el destino existe: nunca se sobrescribe
        errores = auditar_archivo_pdf_generado(destino, False)
        detalle = {**archivo, "ruta_de_paso": str(origen), "ruta": str(destino), "con_dudas": con_dudas,
                   "bytes": destino.stat().st_size, "auditor": errores, "trabajo": self.trabajo_id}
        _con_conexion(lambda c: _auditar(c, "PUBLICAR_PDF", self.visita_id, detalle, self.usuario))
        if errores:
            self.duda(f"auditor:{archivo['formato']}", "(visita)", f"{destino.name}: {'; '.join(errores)}")
        _evento(self.trabajo_id, "pdf_generado", {"visita_id": self.visita_id, "formato": archivo["formato"],
                                                  "ruta": str(destino), "con_dudas": con_dudas,
                                                  "bytes": detalle["bytes"]})
        return detalle

    def _cerrar(self, visita, resultados: Dict[str, Dict], generado: Dict) -> Dict:
        formatos = [f for f in _lista(visita["formatos_solicitados"]) if f != FORMATO_CATDIC]
        self.cerrar_propias(None, self.campos, ())  # dudas propias de la visita de corridas anteriores ya sin causa
        abiertas = _con_conexion(self._dudas_abiertas)
        limpio = (bool(generado) and generado["limpio"] and not abiertas
                  and all(r["estado"] in ("listo", "anterior") for r in resultados.values()))
        hechos = {a["formato"] for a in generado.get("archivos", [])}
        if limpio and FORMATO_STP in formatos and FORMATO_STP not in hechos:
            limpio = False
        if limpio and any(f in FORMATOS_FI for f in formatos) and not any(h.startswith("FI-") for h in hechos):
            limpio = False
        publicados = [self._publicar(a, con_dudas=not limpio) for a in generado.get("archivos", [])]
        if any(p["auditor"] for p in publicados):
            limpio = False
        paso = config.obtener_salida_pruebas() / CARPETA_DE_PASO / self.trabajo_id
        for carpeta in (paso, paso.parent):
            try:
                carpeta.rmdir()  # solo si quedó vacía
            except OSError:
                pass
        abiertas = _con_conexion(self._dudas_abiertas)
        if limpio and abiertas:
            limpio = False
        if not limpio and not abiertas:
            # Toda visita 'Con dudas' necesita al menos una duda abierta para que la Mesa la devuelva a la cola
            self.duda("procesador:cierre", "(visita)", "La visita no quedó completa (" +
                      ("; ".join(self.avisos) or "sin documentos generados") + "). Revisa y vuelve a procesar.")
        nuevo = ESTADO_PROCESADA if limpio else ESTADO_CON_DUDAS

        def cerrar(conn):
            v = self._visita(conn)
            origen = _dict(v["origen_datos_json"])
            marca = origen.pop("procesador", {})
            origen["estado"] = ORIGEN_ESTADO
            origen["procesador_ultimo"] = {"trabajo": self.trabajo_id, "estado_anterior": marca.get("estado_anterior"),
                                           "fin": _ahora(), "pdf": [p["ruta"] for p in publicados]}
            salida_json = _dict(v["salida_json"])
            if limpio:
                salida_json = {"procesador": [{"formato": p["formato"], "ruta": p["ruta"]} for p in publicados]}
            conn.execute("UPDATE visitas SET estado = ?, salida_json = ?, origen_datos_json = ?, actualizado = ? WHERE id = ?",
                         (nuevo, _json(salida_json), _json(origen), _ahora(), self.visita_id))
            dudas = [d["id"] for d in self._dudas_abiertas(conn)]
            _auditar(conn, "PROCESAR_VISITA", self.visita_id, {
                "trabajo": self.trabajo_id, "estado_anterior": marca.get("estado_anterior"), "estado_nuevo": nuevo,
                "elementos": {k: r["estado"] for k, r in resultados.items()}, "dudas_abiertas": dudas,
                "pdf": [{"formato": p["formato"], "ruta": p["ruta"], "con_dudas": p["con_dudas"]} for p in publicados],
                "avisos": self.avisos}, self.usuario)
            return dudas
        dudas_abiertas = _con_conexion(cerrar)
        cuenta = {e: sum(1 for r in resultados.values() if r["estado"] == e) for e in ("listo", "espera", "anterior")}
        res = {"visita_id": self.visita_id, "estado": nuevo, "elementos": cuenta, "dudas": dudas_abiertas,
               "pdf": [{"formato": p["formato"], "ruta": p["ruta"], "con_dudas": p["con_dudas"]} for p in publicados],
               "avisos": self.avisos}
        _evento(self.trabajo_id, "visita_fin", res)
        return res
