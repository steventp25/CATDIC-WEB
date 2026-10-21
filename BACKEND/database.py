# backend/database.py
import sqlite3
import json
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).parent / "catdic_local.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def inicializar_bd():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. TABLA PROYECTOS (Fuente única de estado - Control Taller)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proyectos (
        id TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('Supervisión', 'Levantamiento')),
        formato_defecto TEXT NOT NULL,
        cliente TEXT DEFAULT '',
        supervisor TEXT DEFAULT '',
        residente_obra TEXT DEFAULT '',
        no_solicitud TEXT DEFAULT '',
        no_licencia TEXT DEFAULT '',
        estado_obra TEXT DEFAULT '',
        avance_obra INTEGER DEFAULT 0,
        estado_informe TEXT DEFAULT '',
        avance_informe INTEGER DEFAULT 0,
        fecha_comprometida TEXT DEFAULT '',
        fecha_real TEXT DEFAULT '',
        prioridad TEXT DEFAULT 'Media' CHECK(prioridad IN ('Alta', 'Media', 'Baja')),
        proxima_accion TEXT DEFAULT '',
        observaciones TEXT DEFAULT '',
        carpeta_dropbox TEXT DEFAULT '',
        planos_sellados TEXT DEFAULT '',
        carpeta_salida TEXT DEFAULT 'INFORMES/2.DATA PROCESADA',
        version INTEGER DEFAULT 1,
        actualizado TEXT NOT NULL
    );
    """)

    # 2. CAPA 1: DATOS DE DISEÑO (Extraídos una vez por proyecto desde Planos Estructurales)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS elementos_diseno (
        uid TEXT PRIMARY KEY,
        proyecto_id TEXT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
        id_elemento TEXT NOT NULL,           -- Ej: 'C1', 'Z4', 'A (2-3)', 'L9'
        tipo_elemento TEXT NOT NULL,         -- Ej: 'COLUMNA RECTANGULAR', 'VIGA HORMIGON', 'LOSA ALIGERADA'
        nivel_rango TEXT NOT NULL,           -- Ej: 'FUNDACION', 'S-4', 'E3@E8' (según título impreso en hoja)
        ejes TEXT NOT NULL,                  -- Formateado según regla Archivo 02 ('—' en losas)
        hoja_plano_origen TEXT NOT NULL,     -- Ej: 'ES-05'
        archivo_plano_origen TEXT NOT NULL,  -- Ej: 'TERRA LIVING -ESTRUCTURALES.pdf'
        datos_diseno_json TEXT NOT NULL,     -- Dimensiones, acero, estribos, elementos de borde
        estado_campos_json TEXT NOT NULL,    -- Cada campo marcado 'confirmado' o 'pendiente_de_verificar'
        recorte_planta_json TEXT DEFAULT '{}',  -- Coordenadas del recuadro rojo en planta completa
        recorte_detalle_json TEXT DEFAULT '{}', -- Coordenadas del detalle/tabla en el plano
        actualizado TEXT NOT NULL
    );
    """)

    # 3. COLA DE VISITAS A OBRA
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS visitas (
        id TEXT PRIMARY KEY,
        proyecto_id TEXT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
        numero INTEGER NOT NULL,
        nombre_carpeta TEXT NOT NULL,
        ruta_carpeta TEXT NOT NULL,
        fecha_visita TEXT NOT NULL,          -- AAAA-MM-DD para ordenar cola cronológica
        clase TEXT NOT NULL CHECK(clase IN ('Parcial', 'Completivo')),
        estado TEXT NOT NULL CHECK(estado IN (
            'Sin procesar', 'En cola', 'En proceso', 'Con dudas', 'En revisión', 'Procesada'
        )),
        formatos_solicitados TEXT NOT NULL,  -- Ej: '["STP-MIVED", "MIVED-FI"]' o '["HV-LEV"]'
        salida_json TEXT DEFAULT '{}',       -- Rutas de PDFs generados (stp, mived, hv)
        nota TEXT DEFAULT '',
        version INTEGER DEFAULT 1,
        actualizado TEXT NOT NULL
    );
    """)

    # 4. CAPA 2: OBSERVACIONES Y MEDIDAS DE CAMPO (Lo que sale de la visita)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS elementos_visita (
        uid TEXT PRIMARY KEY,
        visita_id TEXT NOT NULL REFERENCES visitas(id) ON DELETE CASCADE,
        orden_en_log INTEGER NOT NULL,       -- Orden secuencial exacto del log fotográfico
        etiqueta_original TEXT NOT NULL,     -- Ej: 'C1 A4'
        id_elemento TEXT NOT NULL,
        tipo_elemento TEXT NOT NULL,
        nivel TEXT NOT NULL,
        ejes TEXT NOT NULL,
        fotos_json TEXT NOT NULL,            -- Lista secuencial de fotos que pertenecen al elemento
        medidas_acero_campo_json TEXT DEFAULT '{}', -- Medidas tomadas sobre el acero en obra
        escaneos_json TEXT DEFAULT '[]',     -- Capturas Profometer 650 / Proceq GP8000 (n = num foto)
        elemento_diseno_uid TEXT REFERENCES elementos_diseno(uid)
    );
    """)

    # 5. DUDAS (Bloqueantes para preguntar al usuario) Y HALLAZGOS INTERNOS (Nunca cajas en ficha)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dudas_y_hallazgos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id TEXT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
        visita_id TEXT REFERENCES visitas(id) ON DELETE CASCADE,
        id_elemento TEXT NOT NULL,
        categoria TEXT NOT NULL CHECK(categoria IN ('DUDA_BLOQUEANTE', 'HALLAZGO_INTERNO')),
        campo_afectado TEXT NOT NULL,
        descripcion_pregunta TEXT NOT NULL,
        respuesta_usuario TEXT DEFAULT '',
        resuelta INTEGER DEFAULT 0,          -- 0 = Pendiente, 1 = Confirmada por el usuario
        creado TEXT NOT NULL,
        resuelto_en TEXT DEFAULT ''
    );
    """)

    # 6. ÓRDENES DE TRABAJO (Kanban y Dependencias)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ordenes_trabajo (
        doc_id TEXT PRIMARY KEY,             -- Ej: 'OT-LEV-001', 'OT-SUP-001'
        tipo TEXT NOT NULL CHECK(tipo IN ('Supervisión', 'Levantamiento')),
        proyecto_id TEXT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
        seccion TEXT NOT NULL,
        formato TEXT NOT NULL,
        entregable TEXT NOT NULL,
        estado TEXT NOT NULL CHECK(estado IN (
            'Pendiente', 'Asignada', 'En proceso', 'Bloqueada', 'En revisión', 'Entregada'
        )),
        depende_de TEXT DEFAULT '',          -- doc_id de la OT previa obligatoria
        prioridad TEXT DEFAULT 'Media',
        fecha_comprometida TEXT DEFAULT '',
        nota TEXT DEFAULT '',
        version INTEGER DEFAULT 1,
        actualizado TEXT NOT NULL
    );
    """)

    # 7. BITÁCORA DE AUDITORÍA (Trazabilidad completa offline/multiusuario)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora TEXT NOT NULL,
        usuario TEXT NOT NULL DEFAULT 'steven',
        modulo TEXT NOT NULL,
        accion TEXT NOT NULL,
        entidad_id TEXT NOT NULL,
        detalle_json TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

def registrar_auditoria(modulo: str, accion: str, entidad_id: str, detalle: dict, usuario: str = "steven"):
    conn = get_connection()
    conn.execute("""
        INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), usuario, modulo, accion, entidad_id, json.dumps(detalle, ensure_ascii=False)))
    conn.commit()
    conn.close()

def sembrar_datos_iniciales_catdic():
    """Carga los 3 proyectos activos y la OT visible en las capturas del Control Taller."""
    conn = get_connection()
    ahora = datetime.now().isoformat()

    proyectos_base = [
        (
            "terra-living", "Terra Living", "Supervisión", "STP-MIVED + Formularios MIVED",
            "CONSTRUCTORA CEBALLOS", "Completa supervisor, estado y fechas.",
            r"C:\Users\Steve\CATDIC Dropbox\SUPERVISION\EN CURSO\TERRA LIVING",
            "TERRA LIVING -ESTRUCTURALES.pdf", ahora
        ),
        (
            "torre-p16", "Torre P16", "Supervisión", "STP-MIVED + Formularios MIVED",
            "", "Completar cliente, supervisor, estado y fechas.",
            r"C:\Users\Steve\CATDIC Dropbox\SUPERVISION\EN CURSO\TORRE P16",
            "", ahora
        ),
        (
            "hotel-zoetry-h2-h5", "Hotel Zoetry Cap Cana · H2 y H5", "Levantamiento", "HV",
            "", "Completar cliente, supervisor y fecha comprometida.",
            r"C:\Users\Steve\CATDIC Dropbox\LEVANTAMIENTO\HOTEL ZOETRY",
            "", ahora
        )
    ]

    for p in proyectos_base:
        conn.execute("""
            INSERT OR IGNORE INTO proyectos
            (id, nombre, tipo, formato_defecto, cliente, observaciones, carpeta_dropbox, planos_sellados, actualizado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, p)

    conn.execute("""
        INSERT OR IGNORE INTO ordenes_trabajo
        (doc_id, tipo, proyecto_id, seccion, formato, entregable, estado, prioridad, nota, actualizado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "OT-LEV-001", "Levantamiento", "hotel-zoetry-h2-h5",
        "Ensamble de informes H2 y H5", "HV-INFTEC",
        "Parte teórica + Informe completo H2 y H5", "En proceso", "Media",
        "Ensamblar parte teórica, luego informe completo", ahora
    ))

    conn.commit()
    conn.close()
    registrar_auditoria("SISTEMA", "INICIALIZACION_BD", "catdic_local.db", {"proyectos_sembrados": 3})

if __name__ == "__main__":
    inicializar_bd()
    sembrar_datos_iniciales_catdic()
    print(f"Base de datos creada y verificada en: {DB_PATH}")
