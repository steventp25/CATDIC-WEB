# backend/main.py
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import procesador_cola
from database import get_connection, inicializar_bd, sembrar_datos_iniciales_catdic, usuario_auditoria
from identidad.guardia import guardia, obras_del_usuario
from identidad.permisos import PREPARAR
from identidad.rutas import router as router_identidad
from pedidos import router as router_pedidos
from mesa_dudas import router as router_mesa_dudas
from obras import planos_vigentes, router as router_obras
from plano.confirmacion import router as router_confirmacion
from plano.extractor import router as router_extractor
from visor import router as router_visor
from visitas_obra import router as router_visitas_obra
from sync.sincronizador import ProyectoNoEncontrado, sincronizar

RUTA_FRONTEND = Path(__file__).resolve().parent.parent / "FRONTEND"

# Fundación F2: la guardia (sesión + permiso por obra) corre en TODA ruta de la API (identidad/guardia.py).
# Sin CORS: la interfaz y la API salen del mismo servidor local, así que otras páginas no pueden usar la sesión.
# Esto no sustituye a la autenticación ni a los permisos, que se comprueban en cada ruta (contrato §1, rev. 2).
app = FastAPI(title="CATDIC Web API", version="2.0.0", dependencies=[Depends(guardia)])


@app.on_event("startup")
def startup_event():
    inicializar_bd()
    sembrar_datos_iniciales_catdic()
    procesador_cola.marcar_huerfanos()  # Etapa 3 · T10a: trabajos que quedaron corriendo si el servidor se cerró


# --- MODELOS PYDANTIC ---
class ProyectoUpdate(BaseModel):
    cliente: Optional[str] = None
    supervisor: Optional[str] = None
    estado_obra: Optional[str] = None
    avance_obra: Optional[int] = None
    estado_informe: Optional[str] = None
    avance_informe: Optional[int] = None
    version: Optional[int] = None  # Fundación F2: si viene y otro cambió la obra antes, 409
    fecha_comprometida: Optional[str] = None
    prioridad: Optional[str] = None
    observaciones: Optional[str] = None
    # Etapa 3 · T7a: datos de cabecera de los informes (los llena Steven, P11)
    no_solicitud: Optional[str] = None
    no_licencia: Optional[str] = None
    residente_obra: Optional[str] = None
    direccion_obra: Optional[str] = None
    provincia: Optional[str] = None
    sector: Optional[str] = None
    inicio_obra: Optional[str] = None  # Etapa 2 · T4n


# --- ENDPOINTS API ---
@app.get("/api/dashboard")
def obtener_dashboard():
    visibles = obras_del_usuario()  # Fundación F2: solo las obras del usuario; las ajenas no aparecen
    conn = get_connection()

    proyectos = [dict(row) for row in conn.execute("SELECT * FROM proyectos").fetchall() if row["id"] in visibles]
    visitas = [dict(row) for row in conn.execute("SELECT * FROM visitas ORDER BY fecha_visita ASC").fetchall()
               if row["proyecto_id"] in visibles]
    ot = [dict(row) for row in conn.execute("SELECT * FROM ordenes_trabajo").fetchall()
          if row["proyecto_id"] in visibles]

    total_proyectos = len(proyectos)
    ordenes_abiertas = len([o for o in ot if o["estado"] != "Entregada"])
    visitas_cola = len([v for v in visitas if v["estado"] in ("Sin procesar", "En cola")])
    visitas_dudas = len([v for v in visitas if v["estado"] == "Con dudas"])

    conn.close()

    return {
        "stats": {
            "proyectos_activos": total_proyectos,
            "ordenes_abiertas": ordenes_abiertas,
            "bloqueadas": 0,
            "vencen_7_dias": 0,
            "visitas_en_cola": visitas_cola,
            "visitas_con_dudas": visitas_dudas,
        },
        "proyectos": proyectos,
        "visitas": visitas,
        "ordenes": ot,
        # Etapa 2 · T4n: resumen del plano vigente de cada obra (F2: solo las visibles)
        "planos_vigentes": {k: v for k, v in planos_vigentes().items() if k in visibles},
    }


@app.patch("/api/proyectos/{proyecto_id}")
def actualizar_proyecto(proyecto_id: str, data: ProyectoUpdate):
    cambios = data.model_dump(exclude_unset=True)
    version = cambios.pop("version", None)
    if not cambios:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar.")

    # Una transacción: el UPDATE y su fila de auditoría (valor anterior y nuevo) van juntos (§1.5)
    conn = get_connection()
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        anterior = conn.execute("SELECT * FROM proyectos WHERE id = ?", (proyecto_id,)).fetchone()
        if anterior is None:
            conn.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail="Proyecto no encontrado.")
        if version is not None and version != anterior["version"]:
            conn.execute("ROLLBACK")
            raise HTTPException(status_code=409, detail="Otra persona cambió esta obra antes; recarga y vuelve a intentarlo.")
        campos = ", ".join(f"{k} = ?" for k in cambios)
        conn.execute(f"UPDATE proyectos SET {campos}, version = COALESCE(version, 1) + 1, "
                     f"actualizado = CURRENT_TIMESTAMP WHERE id = ?", (*cambios.values(), proyecto_id))
        detalle = {k: {"anterior": anterior[k], "nuevo": v} for k, v in cambios.items()}
        conn.execute("""
            INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), usuario_auditoria(), "PROYECTOS", "ACTUALIZAR_PROYECTO",
              proyecto_id, json.dumps(detalle, ensure_ascii=False)))
        conn.execute("COMMIT")
    except HTTPException:
        raise
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()

    return {"status": "ok", "mensaje": "Proyecto actualizado correctamente."}


@app.post("/api/dropbox/sync")
def sincronizar_dropbox(proyecto_id: Optional[str] = None):
    """Lee Dropbox (solo lectura) y sincroniza la cola de visitas (Etapa 1 · T5)."""
    try:
        if proyecto_id is not None:
            return sincronizar(proyecto_id)   # la guardia ya comprobó 'preparar' en esa obra
        # Sin obra: solo las obras donde el usuario puede preparar (Fundación F2)
        resumenes = []
        for pid in sorted(obras_del_usuario(PREPARAR)):
            resumenes.extend(sincronizar(pid)["proyectos"])
        return {"status": "ok", "proyectos": resumenes}
    except ProyectoNoEncontrado:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")


# --- Etapa 3 · T10a: procesador de la cola (trabajo en segundo plano con eventos para la pantalla en vivo) ---
def _lanzar(visita_ids, tipo: str):
    try:
        return procesador_cola.lanzar_trabajo(visita_ids, tipo, usuario=usuario_auditoria())
    except procesador_cola.TrabajoEnCurso as e:
        raise HTTPException(status_code=409, detail=str(e))
    except procesador_cola.VisitaNoProcesable as e:
        raise HTTPException(status_code=409, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/visitas/procesar-cola", status_code=202)
def procesar_cola(proyecto_id: Optional[str] = None):
    """Lanza un trabajo con las visitas 'Sin procesar' y 'En cola' (de una obra o de todas), por fecha."""
    visitas = procesador_cola.visitas_de_la_cola(proyecto_id)
    if proyecto_id is None:  # Fundación F2: sin obra, solo las visitas de las obras donde el usuario puede preparar
        permitidas = obras_del_usuario(PREPARAR)
        conn = get_connection()
        try:
            obra_de = {f["id"]: f["proyecto_id"] for f in conn.execute("SELECT id, proyecto_id FROM visitas")}
        finally:
            conn.close()
        visitas = [v for v in visitas if obra_de.get(v) in permitidas]
    if not visitas:
        return {"trabajo": None, "mensaje": "No hay visitas Sin procesar ni En cola."}
    return {"trabajo": _lanzar(visitas, "cola"), "mensaje": f"Trabajo lanzado con {len(visitas)} visitas."}


@app.post("/api/visitas/{visita_id}/procesar", status_code=202)
def procesar_visita(visita_id: str):
    """Lanza un trabajo para una visita 'Sin procesar', 'En cola' o 'Con dudas'."""
    return {"trabajo": _lanzar([visita_id], "visita"), "mensaje": "Trabajo lanzado."}


@app.get("/api/trabajos/{trabajo_id}")
def obtener_trabajo(trabajo_id: str):
    trabajo = procesador_cola.obtener_trabajo(trabajo_id)
    if trabajo is None:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado.")
    return trabajo


@app.get("/api/trabajos/{trabajo_id}/eventos")
def eventos_trabajo(trabajo_id: str, desde: int = 0):
    """Eventos con número mayor que `desde` (la pantalla en vivo pide desde el último que ya tiene)."""
    if procesador_cola.obtener_trabajo(trabajo_id) is None:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado.")
    return procesador_cola.listar_eventos(trabajo_id, max(0, desde))


app.include_router(router_identidad)  # Fundación F2: sesión, usuarios, obras autorizadas y membresías
app.include_router(router_pedidos)    # Fundación F2: pedidos con control de versión (409)
app.include_router(router_mesa_dudas)
app.include_router(router_obras)  # Etapa 2 · T4n: crear obra, planos y datos del usuario
app.include_router(router_visor)  # Etapa 2 · T5n: visor del vectorial y recuadros
app.include_router(router_extractor)  # Etapa 2 · T6n: extractor de las tablas de aplicación del vectorial
app.include_router(router_confirmacion)  # Etapa 2 · T7n: confirmación de los datos extraídos del plano
app.include_router(router_visitas_obra)  # Etapa 2 · T4v: subir visita o conectar la obra con Dropbox


# Se monta al final para que /api/* conserve prioridad. Un solo servidor local entrega
# la interfaz y la API en http://localhost:8000.
app.mount("/", StaticFiles(directory=RUTA_FRONTEND, html=True), name="frontend")
