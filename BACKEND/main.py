# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from pathlib import Path
from database import get_connection, inicializar_bd, sembrar_datos_iniciales_catdic
from sync.sincronizador import ProyectoNoEncontrado, sincronizar

app = FastAPI(title="CATDIC Web API", version="2.0.0")

# Permitir conexiones locales desde el frontend
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

# --- ENDPOINTS API ---

@app.get("/api/dashboard")
def obtener_dashboard():
    conn = get_connection()
    
    # 1. Proyectos activos
    proyectos = [dict(row) for row in conn.execute("SELECT * FROM proyectos").fetchall()]
    
    # 2. Cola de visitas
    visitas = [dict(row) for row in conn.execute("SELECT * FROM visitas ORDER BY fecha_visita ASC").fetchall()]
    
    # 3. Órdenes de trabajo (Kanban)
    ot = [dict(row) for row in conn.execute("SELECT * FROM ordenes_trabajo").fetchall()]
    
    # 4. Estadísticas de resumen
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
            "visitas_con_dudas": visitas_dudas
        },
        "proyectos": proyectos,
        "visitas": visitas,
        "ordenes": ot
    }

@app.patch("/api/proyectos/{proyecto_id}")
def actualizar_proyecto(proyecto_id: str, data: ProyectoUpdate):
    conn = get_connection()
    campos = []
    valores = []
    
    for k, v in data.dict(exclude_unset=True).items():
        campos.append(f"{k} = ?")
        valores.append(v)
        
    if not campos:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar.")
        
    valores.append(proyecto_id)
    query = f"UPDATE proyectos SET {', '.join(campos)}, actualizado = CURRENT_TIMESTAMP WHERE id = ?"
    
    cursor = conn.execute(query, valores)
    conn.commit()
    conn.close()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")
        
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
