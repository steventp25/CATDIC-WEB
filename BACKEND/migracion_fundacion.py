# backend/migracion_fundacion.py
# Fundación F2 (contrato §1 y §2): migración conservadora. Solo AÑADE tablas, columnas, índices y disparadores;
# no reconstruye ni borra nada, y conserva los id existentes (proyectos.id, planos.id, visitas.id,
# elementos_diseno.uid). Idempotente: si ya está aplicada no hace nada (ni respaldo). Antes de cambiar algo
# respalda la base con la API de respaldo de SQLite y todo el cambio, con su fila de auditoría, va en UNA
# transacción: o se aplica entero o no se aplica.
#
# No crea usuarios ni contraseñas: el alta inicial la hace Steven en local (identidad/alta_inicial.py).
# Las filas históricas de `auditoria` (usuario='steven') no se tocan.
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import config

FUNCIONES_OBRA = ("administrar_obra", "preparar", "revisar_autorizar", "consultar")
SERVICIOS = ("Supervisión", "Levantamiento")
ESTADOS_PEDIDO = ("borrador", "solicitado", "preparado", "en_revision", "corregir", "aprobado")
ORIGENES_DUDA = ("programa", "ia", "persona")

_LISTA_FUNCIONES = ", ".join(f"'{f}'" for f in FUNCIONES_OBRA)

TABLAS = {
    "usuarios": """
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,     -- nombre de entrada; lo escribe la persona
            nombre_visible TEXT NOT NULL,
            hash_contrasena TEXT NOT NULL,                   -- scrypt$n$r$p$sal$hash (identidad/contrasenas.py)
            activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0, 1)),
            es_admin INTEGER NOT NULL DEFAULT 0 CHECK(es_admin IN (0, 1)),
            creado_en TEXT NOT NULL,
            actualizado TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1
        )""",
    "sesiones": """
        CREATE TABLE sesiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT NOT NULL UNIQUE,                 -- sha256 del token; el token solo va en la cookie
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            creada TEXT NOT NULL,
            ultimo_uso TEXT NOT NULL,
            expira TEXT NOT NULL,                            -- creada + 7 días (caducidad total)
            cerrada TEXT DEFAULT NULL,
            motivo_cierre TEXT DEFAULT '',
            direccion TEXT DEFAULT ''
        )""",
    "membresias": f"""
        CREATE TABLE membresias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            obra_id TEXT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
            funciones TEXT NOT NULL CHECK(json_valid(funciones) AND json_type(funciones) = 'array'),
            version INTEGER NOT NULL DEFAULT 1,
            creada TEXT NOT NULL,
            actualizada TEXT NOT NULL,
            UNIQUE(usuario_id, obra_id)
        )""",
    "obra_servicios": """
        CREATE TABLE obra_servicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            obra_id TEXT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
            servicio TEXT NOT NULL CHECK(servicio IN ('Supervisión', 'Levantamiento')),
            formato_defecto TEXT NOT NULL DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0, 1)),
            origen TEXT NOT NULL DEFAULT 'proyectos.tipo',  -- servicio principal heredado de proyectos.tipo
            creado TEXT NOT NULL,
            UNIQUE(obra_id, servicio)
        )""",
    "intentos_entrada": """
        CREATE TABLE intentos_entrada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,                           -- lo escrito al entrar (en minúsculas); nunca la contraseña
            direccion TEXT NOT NULL,
            exito INTEGER NOT NULL CHECK(exito IN (0, 1)),
            en TEXT NOT NULL
        )""",
    "pedidos": f"""
        CREATE TABLE pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            obra_id TEXT NOT NULL REFERENCES proyectos(id),
            proposito TEXT NOT NULL,
            responsable_id INTEGER REFERENCES usuarios(id),
            estado TEXT NOT NULL DEFAULT 'borrador' CHECK(estado IN ({", ".join(f"'{e}'" for e in ESTADOS_PEDIDO)})),
            progreso_json TEXT NOT NULL DEFAULT '{{}}',
            version INTEGER NOT NULL DEFAULT 1,
            creado_por INTEGER REFERENCES usuarios(id),
            creado_en TEXT NOT NULL,
            actualizado_en TEXT NOT NULL
        )""",
    "pedido_fuentes": """
        CREATE TABLE pedido_fuentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
            plano_id INTEGER REFERENCES planos(id),          -- revisión de plano (contrato §2.2)
            documento_version_id INTEGER,                    -- F3 añade documento_versiones; hasta entonces vacío
            seleccionado_por INTEGER REFERENCES usuarios(id),
            seleccionado_en TEXT NOT NULL,
            CHECK(plano_id IS NOT NULL OR documento_version_id IS NOT NULL)
        )""",
}

COLUMNAS = {  # tabla -> [(columna, definición)]
    "auditoria": [("usuario_id", "INTEGER")],
    "trabajos": [("usuario_id", "INTEGER")],
    "dudas_y_hallazgos": [
        ("origen", "TEXT CHECK(origen IS NULL OR origen IN ('programa', 'ia', 'persona'))"),
        ("autor_id", "INTEGER"),
        ("pedido_id", "INTEGER"),
    ],
}

INDICES = {
    "ix_sesiones_usuario": "CREATE INDEX ix_sesiones_usuario ON sesiones(usuario_id)",
    "ix_membresias_obra": "CREATE INDEX ix_membresias_obra ON membresias(obra_id)",
    "ix_intentos_clave": "CREATE INDEX ix_intentos_clave ON intentos_entrada(usuario, direccion, id)",
    "ix_pedidos_obra": "CREATE INDEX ix_pedidos_obra ON pedidos(obra_id)",
    "ix_pedido_fuentes_pedido": "CREATE INDEX ix_pedido_fuentes_pedido ON pedido_fuentes(pedido_id)",
}

# El origen de una duda: hoy va como prefijo «IA:» en el texto. Se conserva el texto y se copia a la columna.
_CASE_ORIGEN = ("CASE WHEN {p}campo_afectado LIKE 'IA:%' OR {p}descripcion_pregunta LIKE 'IA:%' "
                "THEN 'ia' ELSE 'programa' END")

_RECHAZO_FUNCION = (f"WHEN EXISTS (SELECT 1 FROM json_each(NEW.funciones) "
                    f"WHERE type != 'text' OR value NOT IN ({_LISTA_FUNCIONES})) "
                    "BEGIN SELECT RAISE(ABORT, 'funcion de obra no permitida'); END")

DISPARADORES = {
    # Contrato §4 (rev. 3): no existe ninguna función 'administrar'; la base rechaza cualquier función desconocida.
    "membresias_funciones_ins": f"CREATE TRIGGER membresias_funciones_ins BEFORE INSERT ON membresias {_RECHAZO_FUNCION}",
    "membresias_funciones_upd": f"CREATE TRIGGER membresias_funciones_upd BEFORE UPDATE OF funciones ON membresias "
                                f"{_RECHAZO_FUNCION}",
    # Toda obra nueva recibe su servicio principal (el de proyectos.tipo), sin duplicar la obra.
    "proyectos_servicio_inicial": """
        CREATE TRIGGER proyectos_servicio_inicial AFTER INSERT ON proyectos
        BEGIN
            INSERT OR IGNORE INTO obra_servicios (obra_id, servicio, formato_defecto, creado)
            VALUES (NEW.id, NEW.tipo, NEW.formato_defecto, strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime'));
        END""",
    "dudas_origen": f"""
        CREATE TRIGGER dudas_origen AFTER INSERT ON dudas_y_hallazgos WHEN NEW.origen IS NULL
        BEGIN
            UPDATE dudas_y_hallazgos SET origen = {_CASE_ORIGEN.format(p='NEW.')} WHERE id = NEW.id;
        END""",
}


# Columnas que necesita cada disparador o relleno. Una base real siempre las tiene; algunas bases sintéticas de las
# pruebas antiguas no, y entonces el disparador no aplica (y no se cuenta como pendiente: la migración sigue idempotente).
REQUIERE = {
    "proyectos_servicio_inicial": ("proyectos", ("tipo", "formato_defecto")),
    "dudas_origen": ("dudas_y_hallazgos", ("campo_afectado", "descripcion_pregunta")),
    "membresias_funciones_ins": ("membresias", ("funciones",)),
    "membresias_funciones_upd": ("membresias", ("funciones",)),
}


def _aplicable(conn, disparador: str, tablas_nuevas=()) -> bool:
    tabla, cols = REQUIERE[disparador]
    if tabla in tablas_nuevas:
        return True
    return _existe(conn, "table", tabla) and set(cols) <= _columnas(conn, tabla)


def _existe(conn, tipo: str, nombre: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = ? AND name = ?", (tipo, nombre)).fetchone() is not None


def _columnas(conn, tabla: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({tabla})")}


def pendiente(conn) -> dict:
    """Qué falta por aplicar (vacío si la migración ya está hecha)."""
    falta = {
        "tablas": [t for t in TABLAS if not _existe(conn, "table", t)],
        "columnas": {t: [c for c, _ in cols if c not in _columnas(conn, t)]
                     for t, cols in COLUMNAS.items() if _existe(conn, "table", t)},
        "indices": [i for i in INDICES if not _existe(conn, "index", i)],
        "disparadores": [d for d in DISPARADORES if not _existe(conn, "trigger", d)
                         and _aplicable(conn, d, [t for t in TABLAS if not _existe(conn, "table", t)])],
    }
    falta["columnas"] = {t: c for t, c in falta["columnas"].items() if c}
    return {k: v for k, v in falta.items() if v}


def migrar_fundacion_f2() -> dict:
    """Aplica lo que falte de F2. Devuelve {"migrada": bool, ...}. Idempotente."""
    from database import _respaldar_bd, get_connection  # import diferido: database importa este módulo

    db_path = Path(config.obtener_db_path())
    conn = get_connection()
    try:
        falta = pendiente(conn)
        if not falta:
            return {"migrada": False, "motivo": "ya migrada", "respaldo": None}
        conteos_antes = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                         for t in ("proyectos", "planos", "visitas", "elementos_diseno", "dudas_y_hallazgos",
                                   "auditoria", "trabajos") if _existe(conn, "table", t)}
        # Una base sin datos (recién creada) no necesita respaldo; cualquier otra se respalda antes de tocarla.
        respaldo = _respaldar_bd(conn, db_path) if any(conteos_antes.values()) else None
        conn.isolation_level = None
        try:
            conn.execute("BEGIN IMMEDIATE")
            for t in falta.get("tablas", []):
                conn.execute(TABLAS[t])
            for t, cols in falta.get("columnas", {}).items():
                definiciones = dict(COLUMNAS[t])
                for c in cols:
                    conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {definiciones[c]}")
            for i in falta.get("indices", []):
                conn.execute(INDICES[i])
            for d in falta.get("disparadores", []):
                conn.execute(DISPARADORES[d])

            ahora = datetime.now().isoformat()
            # Un servicio por obra existente, desde proyectos.tipo / formato_defecto (resuelve H4 sin duplicar obras)
            servicios = 0
            if _aplicable(conn, "proyectos_servicio_inicial"):
                servicios = conn.execute("""
                    INSERT OR IGNORE INTO obra_servicios (obra_id, servicio, formato_defecto, creado)
                    SELECT id, tipo, formato_defecto, ? FROM proyectos WHERE tipo IN ('Supervisión', 'Levantamiento')
                """, (ahora,)).rowcount
            # Origen de las dudas que ya existen (el texto «IA:» se conserva; solo se copia a la columna)
            origenes = 0
            if ("origen" in falta.get("columnas", {}).get("dudas_y_hallazgos", [])
                    and _aplicable(conn, "dudas_origen")):
                origenes = conn.execute(
                    f"UPDATE dudas_y_hallazgos SET origen = {_CASE_ORIGEN.format(p='')} WHERE origen IS NULL").rowcount

            conteos_despues = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in conteos_antes}
            if conteos_despues != conteos_antes:
                raise sqlite3.IntegrityError(f"Migración F2 abortada: filas {conteos_antes} -> {conteos_despues}")
            violaciones = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violaciones:
                raise sqlite3.IntegrityError(f"Migración F2 abortada: {len(violaciones)} violaciones FK")
            detalle = {"respaldo": respaldo.name if respaldo else None, "aplicado": falta, "servicios_creados": servicios,
                       "dudas_con_origen": origenes, "filas_conservadas": conteos_antes}
            conn.execute("""
                INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ahora, "sistema", "SISTEMA", "MIGRACION_FUNDACION_F2", "catdic_local.db",
                  json.dumps(detalle, ensure_ascii=False)))
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return {"migrada": True, **detalle, "respaldo": str(respaldo) if respaldo else None}
    finally:
        conn.close()
