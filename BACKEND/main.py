# backend/main.py
import getpass
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import get_connection, inicializar_bd, sembrar_datos_iniciales_catdic
from obras import planos_vigentes, router as router_obras
from visor import router as router_visor
from sync.sincronizador import ProyectoNoEncontrado, sincronizar

RUTA_FRONTEND = Path(__file__).resolve().parent.parent / "FRONTEND"

app = FastAPI(title="CATDIC Web API", version="2.0.0")

# Permitir conexiones locales desde el frontend abierto directamente durante la transición.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    inicializar_bd()
    sembrar_datos_iniciales_catdic()


# --- MODELOS PYDANTIC ---
class ProyectoUpdate(BaseModel):
    cliente: Optional[str] = None
    supervisor: Optional[str] = None
    estado_obra: Optional[str] = None
    avance_obra: Optional[int] = None
    estado_informe: Optional[str] = None
    avance_informe: Optional[int] = None
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
    conn = get_connection()

    proyectos = [dict(row) for row in conn.execute("SELECT * FROM proyectos").fetchall()]
    visitas = [dict(row) for row in conn.execute("SELECT * FROM visitas ORDER BY fecha_visita ASC").fetchall()]
    ot = [dict(row) for row in conn.execute("SELECT * FROM ordenes_trabajo").fetchall()]

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
        "planos_vigentes": planos_vigentes(),   # Etapa 2 · T4n: resumen del plano vigente de cada obra
    }


@app.patch("/api/proyectos/{proyecto_id}")
def actualizar_proyecto(proyecto_id: str, data: ProyectoUpdate):
    cambios = data.model_dump(exclude_unset=True)
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
        campos = ", ".join(f"{k} = ?" for k in cambios)
        conn.execute(f"UPDATE proyectos SET {campos}, actualizado = CURRENT_TIMESTAMP WHERE id = ?",
                     (*cambios.values(), proyecto_id))
        detalle = {k: {"anterior": anterior[k], "nuevo": v} for k, v in cambios.items()}
        conn.execute("""
            INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), getpass.getuser(), "PROYECTOS", "ACTUALIZAR_PROYECTO",
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
        return sincronizar(proyecto_id)
    except ProyectoNoEncontrado:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")


MENSAJE_PROCESAR_COLA_DESACTIVADO = (
    "Procesar Cola se habilita en la Etapa 3 (generadores). No se cambió ninguna visita."
)


@app.post("/api/visitas/procesar-cola")
def procesar_cola():
    """Desactivado (Etapa 1 · T9): se conectará a los generadores en la Etapa 3. No toca la BD."""
    raise HTTPException(status_code=409, detail=MENSAJE_PROCESAR_COLA_DESACTIVADO)


app.include_router(router_obras)  # Etapa 2 · T4n: crear obra, planos y datos del usuario
app.include_router(router_visor)  # Etapa 2 · T5n: visor del vectorial y recuadros


# Se monta al final para que /api/* conserve prioridad. Un solo servidor local entrega
# la interfaz y la API en http://localhost:8000.
app.mount("/", StaticFiles(directory=RUTA_FRONTEND, html=True), name="frontend")
