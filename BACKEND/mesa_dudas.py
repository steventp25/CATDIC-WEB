# BACKEND/mesa_dudas.py
# Etapa 3 · T4 — API de la Mesa de Dudas (GET /api/dudas, PATCH /api/dudas/{id}).
#
# Steven es fuente válida: su respuesta se VALIDA y se APLICA a la visita (no solo se marca
# resuelta), porque el sincronizador deja de pedir un campo cuando su duda está resuelta
# pero no escribe el valor. Regla de Oro #1: una respuesta inválida no cambia nada (422);
# nada se deduce ni se inventa. Todo va en una transacción con una fila en `auditoria` (§1.5).
import json
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_connection
from plano import confirmacion
from reglas_ingenieria import PENDIENTE, _es_fecha_ddmmaaaa_valida
from sync.escaner_dropbox import SUBRUTA_INFORMES_PROCESADOS
from sync.parser_visitas import CAMPO_CLASE, CAMPO_FECHA, CLASE_COMPLETIVO, CLASE_PARCIAL
from sync.sincronizador import (
    CAMPO_ARCHIVOS,
    CAMPO_ESTADO,
    DUDA,
    ESTADO_CON_DUDAS,
    ESTADO_PROCESADA,
    ESTADO_SIN_PROCESAR,
    HALLAZGO,
    ORIGEN_ESTADO_MESA,
    estado_tras_cerrar_bloqueantes,
)

MODULO_AUDITORIA = "MESA_DUDAS"
ACCION_AUDITORIA = "RESPONDER_DUDA"
USUARIO = "steven"
ORIGEN_MESA = ORIGEN_ESTADO_MESA

# T4b (e), decisión de Steven: la Mesa no acepta Mixta; solo Parcial o Completivo
CLASES_VALIDAS = (CLASE_PARCIAL, CLASE_COMPLETIVO)
RESPUESTA_CORRESPONDE = "corresponde"
RESPUESTA_NO_CORRESPONDE = "no corresponde"
MENSAJE_ARCHIVOS = ("Esta duda no se responde con texto: se cierra sola al sincronizar "
                    "cuando el PDF esté en la carpeta de la visita.")


class DudaNoEncontrada(LookupError):
    """No existe una duda con ese id (404)."""


class DudaYaResuelta(RuntimeError):
    """La duda ya fue respondida (409)."""


class RespuestaInvalida(ValueError):
    """La respuesta no es válida para el campo; no se cambió nada (422)."""


class RespuestaDuda(BaseModel):
    respuesta: str
    # Solo para estado = "corresponde" con varios STP candidatos: nombres del STP elegido
    stp: Optional[List[str]] = None


def _ahora() -> str:
    return datetime.now().isoformat()


def _json(valor) -> str:
    return json.dumps(valor, ensure_ascii=False)


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto)
                         if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def _lista_json(texto) -> list:
    try:
        valor = json.loads(texto or "[]")
    except (TypeError, ValueError):
        return []
    return valor if isinstance(valor, list) else []


def _dict_json(texto) -> dict:
    try:
        valor = json.loads(texto or "{}")
    except (TypeError, ValueError):
        return {}
    return valor if isinstance(valor, dict) else {}


# ---------- Lectura ----------

def listar_dudas(proyecto_id: Optional[str] = None, visita_id: Optional[str] = None,
                 resuelta: Optional[bool] = None, categoria: Optional[str] = None,
                 sin_visita: bool = False) -> List[Dict]:
    """
    Dudas con el número y la carpeta de su visita. Solo lectura. `sin_visita`: solo las de la obra (visita_id NULL),
    p. ej. las del extractor del plano (T6n:). Una duda T6n: que apunta a un único campo de un elemento trae
    `campo_confirmable` (elemento, campo, valor y estado actuales): responderla confirma ese campo (T7n).
    """
    condiciones, params = [], []
    if sin_visita:
        condiciones.append("d.visita_id IS NULL")
    if proyecto_id is not None:
        condiciones.append("d.proyecto_id = ?")
        params.append(proyecto_id)
    if visita_id is not None:
        condiciones.append("d.visita_id = ?")
        params.append(visita_id)
    if resuelta is not None:
        condiciones.append("d.resuelta = ?")
        params.append(1 if resuelta else 0)
    if categoria is not None:
        condiciones.append("d.categoria = ?")
        params.append(categoria)
    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    conn = get_connection()
    try:
        filas = conn.execute(f"""
            SELECT d.id, d.proyecto_id, d.visita_id, d.id_elemento, d.categoria,
                   d.campo_afectado, d.descripcion_pregunta AS pregunta, d.respuesta_usuario AS respuesta,
                   d.resuelta, d.creado, d.resuelto_en,
                   v.numero AS visita_numero, v.nombre_carpeta AS visita_carpeta,
                   v.estado AS visita_estado
            FROM dudas_y_hallazgos d LEFT JOIN visitas v ON v.id = d.visita_id
            {where} ORDER BY d.id
        """, params).fetchall()
        out = []
        for f in filas:
            d = dict(f)
            if d["visita_id"] is None and not d["resuelta"] and d["campo_afectado"].startswith("T6n:"):
                d["campo_confirmable"] = confirmacion.describir_campo(conn, d["proyecto_id"], d["id_elemento"],
                                                                      d["campo_afectado"])
            out.append(d)
        return out
    finally:
        conn.close()


# ---------- Validación de la respuesta (sin tocar la BD) ----------

def _validar_fecha(respuesta: str) -> str:
    if not _es_fecha_ddmmaaaa_valida(respuesta):
        raise RespuestaInvalida(
            "La fecha debe ser DD/MM/AAAA y existir en el calendario (ej. 05/03/2026).")
    return datetime.strptime(respuesta, "%d/%m/%Y").strftime("%Y-%m-%d")


def _validar_clase(respuesta: str) -> str:
    for clase in CLASES_VALIDAS:
        if respuesta.casefold() == clase.casefold():
            return clase
    raise RespuestaInvalida(f"La clase debe ser una de: {', '.join(CLASES_VALIDAS)}.")


def _validar_estado(respuesta: str, stp: Optional[List[str]], origen: dict, carpeta_dropbox: str) -> dict:
    """Devuelve {"estado": ..., "stp": [rutas]} (stp solo si corresponde)."""
    norm = _normalizar(respuesta)
    if norm == RESPUESTA_NO_CORRESPONDE:
        return {"estado": ESTADO_SIN_PROCESAR, "stp": []}
    if norm != RESPUESTA_CORRESPONDE:
        raise RespuestaInvalida(f"Responde '{RESPUESTA_CORRESPONDE}' o '{RESPUESTA_NO_CORRESPONDE}'.")
    grupos = [g for g in origen.get("stp_candidatos", [])
              if isinstance(g, list) and g and all(isinstance(n, str) for n in g)]
    if not grupos:
        raise RespuestaInvalida("La visita no tiene STP candidatos guardados; no se puede citar "
                                "ninguno (no se inventa).")
    if stp is None:
        if len(grupos) != 1:
            raise RespuestaInvalida("Hay varios STP candidatos: indica cuál corresponde en 'stp'.")
        elegido = grupos[0]
    else:
        elegido = next((g for g in grupos if sorted(g) == sorted(stp)), None)
        if elegido is None:
            raise RespuestaInvalida("El STP indicado no es uno de los candidatos de la visita.")
    if not (carpeta_dropbox or "").strip():
        raise RespuestaInvalida(f"El proyecto no tiene carpeta_dropbox: {PENDIENTE}.")
    carpeta = Path(carpeta_dropbox) / SUBRUTA_INFORMES_PROCESADOS
    rutas = [carpeta / nombre for nombre in elegido]
    # T4b (d): comprobación en solo lectura de que el STP sigue en 2.DATA PROCESADA
    faltan = [r.name for r in rutas if not r.exists()]
    if faltan:
        raise RespuestaInvalida(
            f"El STP ya no está en INFORMES\\2.DATA PROCESADA: {', '.join(faltan)}. No se cambió nada.")
    return {"estado": ESTADO_PROCESADA, "stp": [str(r) for r in rutas]}


# ---------- Escritura ----------

def responder_duda(duda_id: int, respuesta: str, stp: Optional[List[str]] = None) -> Dict:
    """
    Valida y aplica la respuesta de Steven. Una transacción: o se aplica todo (valor, duda
    resuelta, estado de la visita y auditoría) o nada. Lanza DudaNoEncontrada (404),
    DudaYaResuelta (409) o RespuestaInvalida (422).
    """
    conn = get_connection()
    conn.isolation_level = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            resultado = _responder(conn, duda_id, (respuesta or "").strip(), stp)
            conn.execute("COMMIT")
            return resultado
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def _responder(conn, duda_id: int, respuesta: str, stp: Optional[List[str]]) -> Dict:
    duda = conn.execute("SELECT * FROM dudas_y_hallazgos WHERE id = ?", (duda_id,)).fetchone()
    if duda is None:
        raise DudaNoEncontrada(f"No existe la duda {duda_id}.")
    if duda["resuelta"]:
        raise DudaYaResuelta(f"La duda {duda_id} ya está resuelta.")
    if not respuesta:
        raise RespuestaInvalida("La respuesta no puede estar vacía.")

    campo, visita_id = duda["campo_afectado"], duda["visita_id"]
    visita = None
    if visita_id:
        visita = conn.execute("SELECT * FROM visitas WHERE id = ?", (visita_id,)).fetchone()
    cambios_visita: Dict[str, object] = {}
    origen = _dict_json(visita["origen_datos_json"]) if visita else {}
    anterior = nuevo = None

    if duda["categoria"] == HALLAZGO:
        # Se marca revisado sin aplicar valor. Ya no hace falta bloquearlo cuando hay una duda
        # bloqueante abierta del mismo campo: desde T4b el sync solo cuenta bloqueantes resueltas.
        pass
    elif duda["id_elemento"]:
        # T7n: una duda del extractor (T6n:) que apunta a un único campo de un elemento confirma ese campo con el
        # valor que escribe Steven (validado; auditoría por campo). Las demás dudas de elemento solo guardan la respuesta.
        try:
            aplicado = confirmacion.aplicar_respuesta(conn, duda, respuesta, USUARIO)
        except confirmacion.ValorInvalido as e:
            raise RespuestaInvalida(str(e)) from None
        if aplicado:
            anterior, nuevo = aplicado["anterior"], aplicado["nuevo"]
    elif campo == CAMPO_ARCHIVOS:
        raise RespuestaInvalida(MENSAJE_ARCHIVOS)
    elif campo in (CAMPO_FECHA, CAMPO_CLASE, CAMPO_ESTADO):
        if visita is None:
            raise RespuestaInvalida(f"La duda '{campo}' no tiene visita asociada.")
        if campo == CAMPO_FECHA:
            nuevo = _validar_fecha(respuesta)
            anterior = visita["fecha_visita"]
            cambios_visita["fecha_visita"] = nuevo
            origen["fecha"] = ORIGEN_MESA
        elif campo == CAMPO_CLASE:
            nuevo = _validar_clase(respuesta)
            anterior = visita["clase"]
            cambios_visita["clase"] = nuevo
            origen["clase"] = ORIGEN_MESA
        else:
            proyecto = conn.execute("SELECT carpeta_dropbox FROM proyectos WHERE id = ?",
                                    (visita["proyecto_id"],)).fetchone()
            nuevo = _validar_estado(respuesta, stp, origen, proyecto["carpeta_dropbox"] if proyecto else "")
            anterior = visita["estado"]
            # La decisión se guarda; se aplica cuando la visita no tenga más bloqueantes abiertos
            origen["estado_mesa"] = nuevo
        if campo in (CAMPO_FECHA, CAMPO_CLASE):
            pendientes = [c for c in _lista_json(visita["campos_pendientes_json"]) if c != campo]
            cambios_visita["campos_pendientes_json"] = _json(pendientes)
    else:
        raise RespuestaInvalida(f"El campo '{campo}' no se puede responder desde la Mesa de Dudas.")

    ahora = _ahora()
    conn.execute("""UPDATE dudas_y_hallazgos SET resuelta = 1, respuesta_usuario = ?, resuelto_en = ?
                    WHERE id = ?""", (respuesta, ahora, duda_id))

    estado_anterior = estado_nuevo = None
    if visita is not None:
        estado_anterior = visita["estado"]
        estado_nuevo = estado_anterior
        # Visita sin bloqueantes abiertos: Sin procesar, o el estado que Steven eligió.
        # Nunca Procesada por su cuenta: solo si Steven respondió "corresponde" y citó el STP.
        cambios_visita.update(
            estado_tras_cerrar_bloqueantes(conn, visita_id, estado_anterior, origen))
        estado_nuevo = cambios_visita.get("estado", estado_anterior)
        if origen != _dict_json(visita["origen_datos_json"]):
            cambios_visita["origen_datos_json"] = _json(origen)
        if cambios_visita:
            sets = ", ".join(f"{k} = ?" for k in cambios_visita)
            conn.execute(f"UPDATE visitas SET {sets}, actualizado = ? WHERE id = ?",
                         (*cambios_visita.values(), ahora, visita_id))

    detalle = {
        "duda_id": duda_id, "visita_id": visita_id, "id_elemento": duda["id_elemento"],
        "categoria": duda["categoria"], "campo": campo, "respuesta": respuesta,
        "valor_anterior": anterior, "valor_nuevo": nuevo,
        "estado_anterior": estado_anterior, "estado_nuevo": estado_nuevo,
    }
    conn.execute("""
        INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ahora, USUARIO, MODULO_AUDITORIA, ACCION_AUDITORIA, str(duda_id), _json(detalle)))
    return {"duda_id": duda_id, "resuelta": True, "campo": campo, "valor_aplicado": nuevo,
            "visita_id": visita_id, "estado_visita": estado_nuevo}


# ---------- Rutas ----------

router = APIRouter()


@router.get("/api/dudas")
def api_listar_dudas(proyecto_id: Optional[str] = None, visita_id: Optional[str] = None,
                     resuelta: Optional[bool] = None, categoria: Optional[str] = None, sin_visita: bool = False):
    return listar_dudas(proyecto_id, visita_id, resuelta, categoria, sin_visita)


@router.patch("/api/dudas/{duda_id}")
def api_responder_duda(duda_id: int, cuerpo: RespuestaDuda):
    try:
        return responder_duda(duda_id, cuerpo.respuesta, cuerpo.stp)
    except DudaNoEncontrada as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DudaYaResuelta as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RespuestaInvalida as e:
        raise HTTPException(status_code=422, detail=str(e))
