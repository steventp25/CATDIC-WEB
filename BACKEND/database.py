# backend/database.py
import sqlite3
import json
from datetime import datetime, date
from pathlib import Path

import config
from reglas_ingenieria import PENDIENTE

# Esquema vigente de la cola de visitas (Etapa 1 · T2). Fuente única: lo usan la creación
# de una BD nueva y la reconstrucción de una tabla vieja. Se usa con _sql_tabla_visitas(nombre).
_SQL_TABLA_VISITAS = """
    CREATE TABLE IF NOT EXISTS {tabla} (
        id TEXT PRIMARY KEY,
        proyecto_id TEXT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
        numero INTEGER NOT NULL,
        nombre_carpeta TEXT NOT NULL,
        ruta_carpeta TEXT NOT NULL,
        fecha_visita TEXT NOT NULL CHECK(
            fecha_visita = '{pendiente}'
            OR fecha_visita GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        ),                                   -- AAAA-MM-DD para ordenar cola cronológica, o pendiente
        clase TEXT NOT NULL CHECK(clase IN ('Parcial', 'Completivo', 'Mixta', '{pendiente}')),
        estado TEXT NOT NULL CHECK(estado IN (
            'Sin procesar', 'En cola', 'En proceso', 'Con dudas', 'En revisión', 'Procesada'
        )),
        formatos_solicitados TEXT NOT NULL,  -- Ej: '["STP-MIVED"]' o '["HV-LEV"]'
        salida_json TEXT DEFAULT '{{}}',       -- Rutas de PDFs generados (stp, mived, hv)
        nota TEXT DEFAULT '',
        version INTEGER DEFAULT 1,
        actualizado TEXT NOT NULL,
        clase_detalle_json TEXT DEFAULT '[]',     -- Clase 'Mixta': lista de grupos elementos/clase (P2)
        archivos_json TEXT DEFAULT '[]',          -- PDFs de la visita: nombre, tamaño, mtime
        campos_pendientes_json TEXT DEFAULT '[]', -- Campos que quedaron 'pendiente de verificar'
        origen_datos_json TEXT DEFAULT '{{}}',      -- De dónde salió fecha/clase/estado (T8)
        UNIQUE(proyecto_id, ruta_carpeta)
    );
"""

def _sql_tabla_visitas(tabla: str) -> str:
    return _SQL_TABLA_VISITAS.format(tabla=tabla, pendiente=PENDIENTE)

COLUMNAS_NUEVAS_VISITAS = ("clase_detalle_json", "archivos_json", "campos_pendientes_json")
# Etapa 1 · T8: columna añadida con ALTER TABLE (no destructiva, sin reconstruir la tabla)
COLUMNA_ORIGEN_VISITAS = "origen_datos_json"

def get_connection():
    # La ruta se resuelve en cada llamada (config / CATDIC_DB_PATH) para poder probar con BD temporal
    conn = sqlite3.connect(config.obtener_db_path())
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
        actualizado TEXT NOT NULL,
        direccion_obra TEXT DEFAULT '',      -- Etapa 3 · T7a: datos de cabecera de los informes
        provincia TEXT DEFAULT '',
        sector TEXT DEFAULT ''
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
        ejes TEXT NOT NULL,                  -- Formato CLAUDE.md §4.4 ('—' en losas, nunca deducido)
        hoja_plano_origen TEXT NOT NULL,     -- Ej: 'ES-05'
        archivo_plano_origen TEXT NOT NULL,  -- Ej: 'TERRA LIVING -ESTRUCTURALES.pdf'
        datos_diseno_json TEXT NOT NULL,     -- Dimensiones, acero, estribos, elementos de borde
        estado_campos_json TEXT NOT NULL,    -- Cada campo marcado 'confirmado' o 'pendiente_de_verificar'
        recorte_planta_json TEXT DEFAULT '{}',  -- Coordenadas del recuadro rojo en planta completa
        recorte_detalle_json TEXT DEFAULT '{}', -- Coordenadas del detalle/tabla en el plano
        actualizado TEXT NOT NULL,
        fuente_json TEXT DEFAULT '{}',       -- Etapa 2 · T1: documento fuente, sección/línea y SHA-256
        pendientes_json TEXT DEFAULT '[]',   -- Etapa 2 · T1: campos 'pendiente de verificar'
        UNIQUE(proyecto_id, id_elemento, nivel_rango, ejes)
    );
    """)

    # 3. COLA DE VISITAS A OBRA (si existe con el esquema viejo, la migra migrar_visitas())
    cursor.execute(_sql_tabla_visitas("visitas"))

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

    # Migraciones idempotentes de tablas ya existentes
    migrar_visitas()
    agregar_columna_origen_visitas()
    migrar_elementos_diseno()
    migrar_proyectos_cabecera()

# ---------- Migración de 'visitas' (Etapa 1 · T2) ----------

def _visitas_esta_migrada(conn) -> bool:
    """True si 'visitas' ya tiene el esquema vigente (columnas nuevas, CHECK y UNIQUE)."""
    fila = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='visitas'").fetchone()
    sql = fila[0]
    columnas = {r[1] for r in conn.execute("PRAGMA table_info(visitas)")}
    if not set(COLUMNAS_NUEVAS_VISITAS) <= columnas:
        return False
    if "'Mixta'" not in sql or f"'{PENDIENTE}'" not in sql:
        return False
    for idx in conn.execute("PRAGMA index_list(visitas)").fetchall():
        if idx[2]:  # unique
            cols = [r[2] for r in conn.execute(f"PRAGMA index_info('{idx[1]}')")]
            if cols == ["proyecto_id", "ruta_carpeta"]:
                return True
    return False

def _ruta_respaldo(db_path: Path, ahora: datetime) -> Path:
    """catdic_local.backup-AAAAMMDD-HHMMSS.db junto a la BD; nunca pisa uno existente (v2, v3...)."""
    base = f"{db_path.stem}.backup-{ahora.strftime('%Y%m%d-%H%M%S')}"
    destino = db_path.with_name(f"{base}.db")
    n = 2
    while destino.exists():
        destino = db_path.with_name(f"{base} v{n}.db")
        n += 1
    return destino

def _respaldar_bd(conn, db_path: Path) -> Path:
    """Copia consistente de la BD (API de respaldo de SQLite) a un archivo nuevo."""
    destino = _ruta_respaldo(db_path, datetime.now())
    copia = sqlite3.connect(destino)
    try:
        conn.backup(copia)
    finally:
        copia.close()
    return destino

def migrar_visitas() -> dict:
    """
    Reconstruye 'visitas' con el esquema vigente si todavía tiene el viejo
    (SQLite no permite alterar un CHECK). Idempotente: si ya está migrada no hace nada.
    Conserva todas las filas y columnas; respalda la BD antes y lo registra en auditoría.
    """
    db_path = Path(config.obtener_db_path())
    conn = get_connection()
    try:
        existe = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='visitas'").fetchone()
        if not existe:
            return {"migrada": False, "motivo": "tabla visitas no existe", "respaldo": None}
        if _visitas_esta_migrada(conn):
            return {"migrada": False, "motivo": "ya migrada", "respaldo": None}

        respaldo = _respaldar_bd(conn, db_path)

        # Procedimiento oficial de SQLite para cambiar el esquema: FK desactivadas fuera
        # de la transacción, tabla nueva, copia, DROP de la vieja y RENAME de la nueva.
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys = OFF;")
        try:
            conn.execute("BEGIN")
            cols_viejas = [r[1] for r in conn.execute("PRAGMA table_info(visitas)")]
            filas_antes = conn.execute("SELECT COUNT(*) FROM visitas").fetchone()[0]
            hijos_antes = {
                t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("elementos_visita", "dudas_y_hallazgos")
            }

            conn.execute("DROP TABLE IF EXISTS visitas_nueva")
            conn.execute(_sql_tabla_visitas("visitas_nueva"))
            cols_nuevas = [r[1] for r in conn.execute("PRAGMA table_info(visitas_nueva)")]
            comunes = [c for c in cols_viejas if c in cols_nuevas]
            lista = ", ".join(comunes)
            conn.execute(f"INSERT INTO visitas_nueva ({lista}) SELECT {lista} FROM visitas")
            conn.execute("DROP TABLE visitas")
            conn.execute("ALTER TABLE visitas_nueva RENAME TO visitas")

            filas_despues = conn.execute("SELECT COUNT(*) FROM visitas").fetchone()[0]
            hijos_despues = {
                t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in hijos_antes
            }
            violaciones = conn.execute("PRAGMA foreign_key_check").fetchall()
            if filas_despues != filas_antes or hijos_despues != hijos_antes or violaciones:
                raise sqlite3.IntegrityError(
                    f"Migración de visitas abortada: filas {filas_antes}->{filas_despues}, "
                    f"hijos {hijos_antes}->{hijos_despues}, violaciones FK {len(violaciones)}")

            detalle = {
                "respaldo": respaldo.name,
                "filas_conservadas": filas_despues,
                "filas_hijas": hijos_despues,
                "columnas_copiadas": comunes,
                "columnas_nuevas": [c for c in cols_nuevas if c not in cols_viejas],
                "columnas_descartadas": [c for c in cols_viejas if c not in cols_nuevas],
            }
            # Auditoría dentro de la misma transacción: o se migra y se registra, o nada
            conn.execute("""
                INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), "steven", "SISTEMA", "MIGRACION_VISITAS",
                  "visitas", json.dumps(detalle, ensure_ascii=False)))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.execute("PRAGMA foreign_keys = ON;")
        return {"migrada": True, "respaldo": str(respaldo), **detalle}
    finally:
        conn.close()

def agregar_columna_origen_visitas() -> dict:
    """
    Etapa 1 · T8: añade visitas.origen_datos_json si falta (ALTER TABLE ADD COLUMN).
    Idempotente y no destructiva (no necesita respaldo). Solo se audita cuando se añade.
    """
    conn = get_connection()
    try:
        existe = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='visitas'").fetchone()
        if not existe:
            return {"agregada": False, "motivo": "tabla visitas no existe"}
        columnas = {r[1] for r in conn.execute("PRAGMA table_info(visitas)")}
        if COLUMNA_ORIGEN_VISITAS in columnas:
            return {"agregada": False, "motivo": "ya existe"}
        filas = conn.execute("SELECT COUNT(*) FROM visitas").fetchone()[0]
        # La sentencia DDL y la auditoría van en la misma transacción explícita
        conn.isolation_level = None
        conn.execute("BEGIN")
        conn.execute(
            f"ALTER TABLE visitas ADD COLUMN {COLUMNA_ORIGEN_VISITAS} TEXT DEFAULT '{{}}'")
        detalle = {"columna": COLUMNA_ORIGEN_VISITAS, "valor_por_defecto": "{}",
                   "filas_existentes": filas}
        conn.execute("""
            INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), "steven", "SISTEMA", "MIGRACION_VISITAS_ORIGEN",
              "visitas", json.dumps(detalle, ensure_ascii=False)))
        conn.execute("COMMIT")
        return {"agregada": True, **detalle}
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()

# ---------- Migración de 'elementos_diseno' (Etapa 2 · T1) ----------
COLUMNAS_NUEVAS_DISENO = (("fuente_json", "'{}'"), ("pendientes_json", "'[]'"))
CLAVE_UNICA_DISENO = ["proyecto_id", "id_elemento", "nivel_rango", "ejes"]
INDICE_UNICO_DISENO = "ux_elementos_diseno_clave"

def _diseno_tiene_unico(conn) -> bool:
    for idx in conn.execute("PRAGMA index_list(elementos_diseno)").fetchall():
        if idx[2]:  # unique
            cols = [r[2] for r in conn.execute(f"PRAGMA index_info('{idx[1]}')")]
            if cols == CLAVE_UNICA_DISENO:
                return True
    return False

def migrar_elementos_diseno() -> dict:
    """
    Etapa 2 · T1: añade fuente_json y pendientes_json y el UNIQUE
    (proyecto_id, id_elemento, nivel_rango, ejes) a una 'elementos_diseno' vieja.
    Se hace con ALTER TABLE ADD COLUMN + CREATE UNIQUE INDEX: no reconstruye la tabla,
    así conserva las filas y las FK de elementos_visita.elemento_diseno_uid.
    Idempotente; respalda la BD antes y audita en la misma transacción.
    Si hay duplicados previos, el índice falla, se revierte todo y no se borra nada.
    """
    db_path = Path(config.obtener_db_path())
    conn = get_connection()
    try:
        existe = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='elementos_diseno'").fetchone()
        if not existe:
            return {"migrada": False, "motivo": "tabla elementos_diseno no existe", "respaldo": None}
        columnas = {r[1] for r in conn.execute("PRAGMA table_info(elementos_diseno)")}
        faltan = [(c, d) for c, d in COLUMNAS_NUEVAS_DISENO if c not in columnas]
        falta_unico = not _diseno_tiene_unico(conn)
        if not faltan and not falta_unico:
            return {"migrada": False, "motivo": "ya migrada", "respaldo": None}

        respaldo = _respaldar_bd(conn, db_path)
        conn.isolation_level = None
        try:
            conn.execute("BEGIN")
            for c, d in faltan:
                conn.execute(f"ALTER TABLE elementos_diseno ADD COLUMN {c} TEXT DEFAULT {d}")
            if falta_unico:
                conn.execute(
                    f"CREATE UNIQUE INDEX {INDICE_UNICO_DISENO} ON elementos_diseno "
                    f"({', '.join(CLAVE_UNICA_DISENO)})")
            filas = conn.execute("SELECT COUNT(*) FROM elementos_diseno").fetchone()[0]
            violaciones = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violaciones:
                raise sqlite3.IntegrityError(
                    f"Migración de elementos_diseno abortada: {len(violaciones)} violaciones FK")
            detalle = {
                "respaldo": respaldo.name,
                "filas_conservadas": filas,
                "columnas_nuevas": [c for c, _ in faltan],
                "unique_creado": CLAVE_UNICA_DISENO if falta_unico else None,
            }
            conn.execute("""
                INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), "steven", "SISTEMA", "MIGRACION_ELEMENTOS_DISENO",
                  "elementos_diseno", json.dumps(detalle, ensure_ascii=False)))
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return {"migrada": True, **detalle, "respaldo": str(respaldo)}
    finally:
        conn.close()

# ---------- Migración de 'proyectos' (Etapa 3 · T7a) ----------
COLUMNAS_CABECERA_PROYECTO = ("direccion_obra", "provincia", "sector")

def migrar_proyectos_cabecera() -> dict:
    """
    Etapa 3 · T7a: añade direccion_obra, provincia y sector a 'proyectos' (TEXT, por defecto '').
    ALTER TABLE ADD COLUMN: no reconstruye la tabla ni toca las filas. Idempotente; respalda la BD
    antes y audita en la misma transacción. Los valores NO se siembran: los llena Steven (P11),
    mientras tanto el generador pone "pendiente de verificar".
    """
    db_path = Path(config.obtener_db_path())
    conn = get_connection()
    try:
        existe = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='proyectos'").fetchone()
        if not existe:
            return {"migrada": False, "motivo": "tabla proyectos no existe", "respaldo": None}
        columnas = {r[1] for r in conn.execute("PRAGMA table_info(proyectos)")}
        faltan = [c for c in COLUMNAS_CABECERA_PROYECTO if c not in columnas]
        if not faltan:
            return {"migrada": False, "motivo": "ya migrada", "respaldo": None}

        respaldo = _respaldar_bd(conn, db_path)
        conn.isolation_level = None
        try:
            conn.execute("BEGIN")
            for c in faltan:
                conn.execute(f"ALTER TABLE proyectos ADD COLUMN {c} TEXT DEFAULT ''")
            filas = conn.execute("SELECT COUNT(*) FROM proyectos").fetchone()[0]
            detalle = {"respaldo": respaldo.name, "filas_conservadas": filas, "columnas_nuevas": faltan}
            conn.execute("""
                INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), "steven", "SISTEMA", "MIGRACION_PROYECTOS_CABECERA",
                  "proyectos", json.dumps(detalle, ensure_ascii=False)))
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return {"migrada": True, **detalle, "respaldo": str(respaldo)}
    finally:
        conn.close()

def registrar_auditoria(modulo: str, accion: str, entidad_id: str, detalle: dict, usuario: str = "steven"):
    conn = get_connection()
    conn.execute("""
        INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), usuario, modulo, accion, entidad_id, json.dumps(detalle, ensure_ascii=False)))
    conn.commit()
    conn.close()

# ---------- Rutas de Dropbox de los proyectos sembrados (Etapa 1 · T6) ----------
# Partes relativas a la raíz de Dropbox (config.obtener_dropbox_raiz()); la raíz no se quema aquí.
RUTAS_PROYECTOS = {
    "terra-living": ("SUPERVISION", "EN CURSO", "TERRA LIVING"),
    "torre-p16": ("SUPERVISION", "EN CURSO", "PROYECTO P16"),                     # P5
    "hotel-zoetry-h2-h5": ("LEVANTAMIENTO", "LEV Y EVA", "EN CURSO", "ZOETRY CAP CANA"),  # P5
}

# Rutas sembradas antes de T6 (no existen en disco, D3/D4). Solo se corrigen si siguen idénticas.
RUTAS_PROYECTOS_VIEJAS = {
    "torre-p16": ("SUPERVISION", "EN CURSO", "TORRE P16"),
    "hotel-zoetry-h2-h5": ("LEVANTAMIENTO", "HOTEL ZOETRY"),
}

def ruta_proyecto(partes: tuple) -> str:
    return str(config.obtener_dropbox_raiz().joinpath(*partes))

def corregir_rutas_proyectos(conn) -> list:
    """
    Corrige carpeta_dropbox de filas ya sembradas con la ruta vieja (INSERT OR IGNORE no lo hace).
    Idempotente: solo cambia la fila si el valor es exactamente el viejo (no pisa ediciones a mano).
    Cada corrección se registra en auditoría dentro de la misma transacción. No hace commit.
    """
    ahora = datetime.now().isoformat()
    correcciones = []
    for proyecto_id, partes_viejas in RUTAS_PROYECTOS_VIEJAS.items():
        vieja = ruta_proyecto(partes_viejas)
        nueva = ruta_proyecto(RUTAS_PROYECTOS[proyecto_id])
        cur = conn.execute("""
            UPDATE proyectos SET carpeta_dropbox = ?, actualizado = ?
            WHERE id = ? AND carpeta_dropbox = ?
        """, (nueva, ahora, proyecto_id, vieja))
        if cur.rowcount:
            detalle = {"ruta_vieja": vieja, "ruta_nueva": nueva}
            conn.execute("""
                INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ahora, "steven", "SISTEMA", "CORREGIR_RUTA_PROYECTO", proyecto_id,
                  json.dumps(detalle, ensure_ascii=False)))
            correcciones.append({"proyecto_id": proyecto_id, **detalle})
    return correcciones

def sembrar_datos_iniciales_catdic():
    """Carga los 3 proyectos activos y la OT visible en las capturas del Control Taller."""
    conn = get_connection()
    ahora = datetime.now().isoformat()

    proyectos_base = [
        (
            "terra-living", "Terra Living", "Supervisión", "STP-MIVED + Formularios MIVED",
            "CONSTRUCTORA CEBALLOS", "Completa supervisor, estado y fechas.",
            ruta_proyecto(RUTAS_PROYECTOS["terra-living"]),
            "TERRA LIVING -ESTRUCTURALES.pdf", ahora
        ),
        (
            "torre-p16", "Torre P16", "Supervisión", "STP-MIVED + Formularios MIVED",
            "", "Completar cliente, supervisor, estado y fechas.",
            ruta_proyecto(RUTAS_PROYECTOS["torre-p16"]),
            "", ahora
        ),
        (
            "hotel-zoetry-h2-h5", "Hotel Zoetry Cap Cana · H2 y H5", "Levantamiento", "HV",
            "", "Completar cliente, supervisor y fecha comprometida.",
            ruta_proyecto(RUTAS_PROYECTOS["hotel-zoetry-h2-h5"]),
            "", ahora
        )
    ]

    for p in proyectos_base:
        conn.execute("""
            INSERT OR IGNORE INTO proyectos
            (id, nombre, tipo, formato_defecto, cliente, observaciones, carpeta_dropbox, planos_sellados, actualizado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, p)

    # BD existentes sembradas con las rutas viejas de P16 y Zoetry (D3/D4)
    corregir_rutas_proyectos(conn)

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
    print(f"Base de datos creada y verificada en: {config.obtener_db_path()}")
