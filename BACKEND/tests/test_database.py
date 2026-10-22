# BACKEND/tests/test_database.py
# Etapa 1 · T1 — Configuración (config.py) y BD probable (PLANES/etapa-1.md, R4/R6).
# Etapa 1 · T2 — Migración del esquema visitas (R3, P2).
# Etapa 1 · T6 — Rutas sembradas de P16 y Zoetry y su corrección idempotente (D3, D4, P5).
# Etapa 1 · T8 — Columna visitas.origen_datos_json añadida de forma idempotente.
# Las pruebas usan una BD temporal (CATDIC_DB_PATH -> tmp_path) y nunca la BD real.
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

import config
import database
from reglas_ingenieria import PENDIENTE

BD_REAL = Path(__file__).resolve().parent.parent / "catdic_local.db"

TABLAS_ESPERADAS = {
    "proyectos", "elementos_diseno", "visitas", "elementos_visita",
    "dudas_y_hallazgos", "ordenes_trabajo", "auditoria",
}


def _firma_archivo(ruta: Path):
    """(existe, tamaño, mtime_ns) para comparar antes/después."""
    if not ruta.exists():
        return (False, None, None)
    st = ruta.stat()
    return (True, st.st_size, st.st_mtime_ns)


@pytest.fixture
def bd_temporal(tmp_path, monkeypatch):
    ruta = tmp_path / "catdic_prueba.db"
    monkeypatch.setenv(config.ENV_DB_PATH, str(ruta))
    return ruta


# ---------- config.py ----------

def test_db_path_por_defecto_es_backend_catdic_local(monkeypatch):
    monkeypatch.delenv(config.ENV_DB_PATH, raising=False)
    assert config.obtener_db_path().resolve() == BD_REAL


def test_db_path_se_cambia_con_variable_de_entorno(tmp_path, monkeypatch):
    destino = tmp_path / "otra.db"
    monkeypatch.setenv(config.ENV_DB_PATH, str(destino))
    assert config.obtener_db_path() == destino


def test_dropbox_raiz_por_defecto(monkeypatch):
    monkeypatch.delenv(config.ENV_DROPBOX_RAIZ, raising=False)
    assert config.obtener_dropbox_raiz() == Path(r"C:\Users\Steve\CATDIC Dropbox")


def test_dropbox_raiz_se_cambia_con_variable_de_entorno(tmp_path, monkeypatch):
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path))
    assert config.obtener_dropbox_raiz() == tmp_path


def test_variable_de_entorno_vacia_usa_el_valor_por_defecto(monkeypatch):
    monkeypatch.setenv(config.ENV_DB_PATH, "   ")
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, "")
    assert config.obtener_db_path().resolve() == BD_REAL
    assert config.obtener_dropbox_raiz() == Path(r"C:\Users\Steve\CATDIC Dropbox")


# ---------- database.py contra BD temporal ----------

def test_inicializar_bd_crea_la_bd_en_tmp_y_no_toca_la_real(bd_temporal):
    """Criterio T1: con CATDIC_DB_PATH en tmp_path, la BD real no cambia."""
    antes = _firma_archivo(BD_REAL)

    database.inicializar_bd()
    database.sembrar_datos_iniciales_catdic()

    assert bd_temporal.exists()
    assert _firma_archivo(BD_REAL) == antes


def test_bd_temporal_tiene_las_7_tablas_y_la_siembra(bd_temporal):
    database.inicializar_bd()
    database.sembrar_datos_iniciales_catdic()

    conn = database.get_connection()
    try:
        tablas = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert TABLAS_ESPERADAS <= tablas
        ids = {r["id"] for r in conn.execute("SELECT id FROM proyectos")}
        assert ids == {"terra-living", "torre-p16", "hotel-zoetry-h2-h5"}
        n_aud = conn.execute(
            "SELECT COUNT(*) FROM auditoria WHERE accion='INICIALIZACION_BD'").fetchone()[0]
        assert n_aud == 1
    finally:
        conn.close()


def test_get_connection_respeta_el_valor_en_tiempo_de_llamada(tmp_path, monkeypatch):
    """La ruta se resuelve en cada llamada, no al importar database."""
    primera = tmp_path / "a.db"
    segunda = tmp_path / "b.db"

    monkeypatch.setenv(config.ENV_DB_PATH, str(primera))
    database.inicializar_bd()
    monkeypatch.setenv(config.ENV_DB_PATH, str(segunda))
    database.inicializar_bd()

    assert primera.exists() and segunda.exists()


def test_fastapi_testclient_importa():
    """Criterio T1: httpx instalado para fastapi.testclient (P6, Python 3.14)."""
    from fastapi.testclient import TestClient  # noqa: F401


# ---------- Etapa 1 · T2 — Migración del esquema 'visitas' ----------
# Todas las filas de estas pruebas son SINTÉTICAS (marcadas "SINTETICO"), no datos de obra.

# Esquema viejo de 'visitas' tal como estaba en database.py antes de T2
SQL_VISITAS_VIEJA = """
CREATE TABLE visitas (
    id TEXT PRIMARY KEY,
    proyecto_id TEXT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    numero INTEGER NOT NULL,
    nombre_carpeta TEXT NOT NULL,
    ruta_carpeta TEXT NOT NULL,
    fecha_visita TEXT NOT NULL,
    clase TEXT NOT NULL CHECK(clase IN ('Parcial', 'Completivo')),
    estado TEXT NOT NULL CHECK(estado IN (
        'Sin procesar', 'En cola', 'En proceso', 'Con dudas', 'En revisión', 'Procesada'
    )),
    formatos_solicitados TEXT NOT NULL,
    salida_json TEXT DEFAULT '{}',
    nota TEXT DEFAULT '',
    version INTEGER DEFAULT 1,
    actualizado TEXT NOT NULL
);
"""

FILA_SINTETICA = {
    "id": "SINTETICO-V1", "proyecto_id": "SINTETICO-P", "numero": 99,
    "nombre_carpeta": "SINTETICO 99. PRUEBA PARCIAL 01-01-2000",
    "ruta_carpeta": "C:/SINTETICO/99", "fecha_visita": "2000-01-01",
    "clase": "Parcial", "estado": "En revisión",
    "formatos_solicitados": '["SINTETICO"]', "salida_json": '{"stp": "SINTETICO.pdf"}',
    "nota": "SINTETICO", "version": 3, "actualizado": "2000-01-01T00:00:00",
}


def _crear_bd_vieja(ruta: Path):
    """BD con 'visitas' en el esquema viejo + un hijo en elementos_visita y en dudas."""
    conn = sqlite3.connect(ruta)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("CREATE TABLE proyectos (id TEXT PRIMARY KEY, nombre TEXT NOT NULL)")
    conn.execute(SQL_VISITAS_VIEJA)
    conn.execute("""CREATE TABLE elementos_visita (
        uid TEXT PRIMARY KEY,
        visita_id TEXT NOT NULL REFERENCES visitas(id) ON DELETE CASCADE)""")
    conn.execute("""CREATE TABLE dudas_y_hallazgos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id TEXT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
        visita_id TEXT REFERENCES visitas(id) ON DELETE CASCADE)""")
    conn.execute("INSERT INTO proyectos VALUES ('SINTETICO-P', 'SINTETICO')")
    _insertar_visita(conn)
    conn.execute("INSERT INTO elementos_visita VALUES ('SINTETICO-E1', 'SINTETICO-V1')")
    conn.execute(
        "INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id) VALUES ('SINTETICO-P', 'SINTETICO-V1')")
    conn.commit()
    conn.close()


def _insertar_visita(conn, **cambios):
    fila = {**FILA_SINTETICA, **cambios}
    cols = ", ".join(fila)
    marcas = ", ".join("?" for _ in fila)
    conn.execute(f"INSERT INTO visitas ({cols}) VALUES ({marcas})", tuple(fila.values()))


def _respaldos(carpeta: Path, stem: str):
    return sorted(p.name for p in carpeta.glob(f"{stem}.backup-*.db"))


def _n_auditoria_migracion(conn):
    return conn.execute(
        "SELECT COUNT(*) FROM auditoria WHERE modulo='SISTEMA' AND accion='MIGRACION_VISITAS'"
    ).fetchone()[0]


def _n_auditoria_origen(conn):
    return conn.execute(
        "SELECT COUNT(*) FROM auditoria WHERE modulo='SISTEMA' AND accion='MIGRACION_VISITAS_ORIGEN'"
    ).fetchone()[0]


@pytest.fixture
def bd_vieja(bd_temporal):
    _crear_bd_vieja(bd_temporal)
    return bd_temporal


def test_migracion_conserva_fila_hijos_y_crea_respaldo(bd_vieja):
    database.inicializar_bd()

    conn = database.get_connection()
    try:
        fila = dict(conn.execute("SELECT * FROM visitas WHERE id='SINTETICO-V1'").fetchone())
        for campo, valor in FILA_SINTETICA.items():
            assert fila[campo] == valor, campo
        # Columnas nuevas con su valor por defecto
        assert fila["clase_detalle_json"] == "[]"
        assert fila["archivos_json"] == "[]"
        assert fila["campos_pendientes_json"] == "[]"
        assert fila["origen_datos_json"] == "{}"
        # Los hijos no se pierden y las FK siguen consistentes
        assert conn.execute("SELECT COUNT(*) FROM elementos_visita").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM dudas_y_hallazgos").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        # Las FK de los hijos siguen apuntando a 'visitas' (no a una tabla temporal)
        ref = conn.execute("PRAGMA foreign_key_list(elementos_visita)").fetchone()
        assert ref["table"] == "visitas"
        # Auditoría
        assert _n_auditoria_migracion(conn) == 1
        detalle = json.loads(conn.execute(
            "SELECT detalle_json FROM auditoria WHERE accion='MIGRACION_VISITAS'").fetchone()[0])
        assert detalle["filas_conservadas"] == 1
        assert set(detalle["columnas_nuevas"]) == (
            set(database.COLUMNAS_NUEVAS_VISITAS) | {database.COLUMNA_ORIGEN_VISITAS})
        # Esquema viejo reconstruido: la columna de T8 ya viene en el esquema, sin otra auditoría
        assert _n_auditoria_origen(conn) == 0
        assert detalle["columnas_descartadas"] == []
    finally:
        conn.close()

    respaldos = _respaldos(bd_vieja.parent, bd_vieja.stem)
    assert len(respaldos) == 1
    assert respaldos[0] == detalle["respaldo"]
    # El respaldo conserva el esquema viejo y la fila
    copia = sqlite3.connect(bd_vieja.parent / respaldos[0])
    try:
        sql = copia.execute("SELECT sql FROM sqlite_master WHERE name='visitas'").fetchone()[0]
        assert "'Mixta'" not in sql
        assert copia.execute("SELECT COUNT(*) FROM visitas").fetchone()[0] == 1
    finally:
        copia.close()


def test_borrado_en_cascada_sigue_activo_tras_migrar(bd_vieja):
    database.inicializar_bd()
    conn = database.get_connection()
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        conn.execute("DELETE FROM visitas WHERE id='SINTETICO-V1'")
        assert conn.execute("SELECT COUNT(*) FROM elementos_visita").fetchone()[0] == 0
        conn.rollback()
    finally:
        conn.close()


def test_esquema_nuevo_acepta_pendiente_y_mixta_y_rechaza_otra(bd_vieja):
    database.inicializar_bd()
    conn = database.get_connection()
    try:
        _insertar_visita(conn, id="SINTETICO-V2", ruta_carpeta="C:/SINTETICO/V2",
                         clase=PENDIENTE, fecha_visita=PENDIENTE)
        _insertar_visita(conn, id="SINTETICO-V3", ruta_carpeta="C:/SINTETICO/V3",
                         clase="Mixta",
                         clase_detalle_json='[{"elementos": "SINTETICO", "clase": "Parcial"}]')
        with pytest.raises(sqlite3.IntegrityError):
            _insertar_visita(conn, id="SINTETICO-V4", ruta_carpeta="C:/SINTETICO/V4", clase="Otra")
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM visitas").fetchone()[0] == 3
    finally:
        conn.close()


def test_fecha_visita_solo_admite_iso_o_pendiente(bd_vieja):
    database.inicializar_bd()
    conn = database.get_connection()
    try:
        for i, fecha in enumerate(["01/01/2000", "", "1-1-2000", None]):
            with pytest.raises(sqlite3.IntegrityError):
                _insertar_visita(conn, id=f"SINTETICO-F{i}", ruta_carpeta=f"C:/SINTETICO/F{i}",
                                 fecha_visita=fecha)
    finally:
        conn.close()


def test_unique_proyecto_ruta_carpeta_rechaza_duplicado(bd_vieja):
    database.inicializar_bd()
    conn = database.get_connection()
    try:
        # Mismo proyecto y misma ruta que la fila migrada, con otro id
        with pytest.raises(sqlite3.IntegrityError):
            _insertar_visita(conn, id="SINTETICO-DUP")
        # Misma ruta en otro proyecto sí se admite
        conn.execute("INSERT INTO proyectos (id, nombre) VALUES ('SINTETICO-P2', 'SINTETICO')")
        _insertar_visita(conn, id="SINTETICO-OTRO", proyecto_id="SINTETICO-P2")
    finally:
        conn.close()


def test_migracion_dos_veces_no_cambia_nada(bd_vieja):
    database.inicializar_bd()
    conn = database.get_connection()
    try:
        sql_1 = conn.execute("SELECT sql FROM sqlite_master WHERE name='visitas'").fetchone()[0]
        filas_1 = [tuple(r) for r in conn.execute("SELECT * FROM visitas")]
        aud_1 = conn.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]
    finally:
        conn.close()
    respaldos_1 = _respaldos(bd_vieja.parent, bd_vieja.stem)

    resultado = database.migrar_visitas()
    database.inicializar_bd()

    assert resultado["migrada"] is False
    conn = database.get_connection()
    try:
        assert conn.execute("SELECT sql FROM sqlite_master WHERE name='visitas'").fetchone()[0] == sql_1
        assert [tuple(r) for r in conn.execute("SELECT * FROM visitas")] == filas_1
        assert conn.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0] == aud_1
        assert _n_auditoria_migracion(conn) == 1
    finally:
        conn.close()
    assert _respaldos(bd_vieja.parent, bd_vieja.stem) == respaldos_1


def test_bd_nueva_no_crea_respaldo_ni_auditoria_de_migracion(bd_temporal):
    database.inicializar_bd()
    assert _respaldos(bd_temporal.parent, bd_temporal.stem) == []
    conn = database.get_connection()
    try:
        assert _n_auditoria_migracion(conn) == 0
        cols = {r[1] for r in conn.execute("PRAGMA table_info(visitas)")}
        assert set(database.COLUMNAS_NUEVAS_VISITAS) <= cols
        assert database._visitas_esta_migrada(conn)
    finally:
        conn.close()


def test_migracion_fallida_revierte_todo(bd_temporal):
    """Una fila vieja con fecha fuera de formato aborta la migración sin perder datos."""
    _crear_bd_vieja(bd_temporal)
    conn = sqlite3.connect(bd_temporal)
    _insertar_visita(conn, id="SINTETICO-MAL", ruta_carpeta="C:/SINTETICO/MAL",
                     fecha_visita="01/01/2000")
    conn.commit()
    conn.close()

    with pytest.raises(sqlite3.IntegrityError):
        database.inicializar_bd()

    conn = database.get_connection()
    try:
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='visitas'").fetchone()[0]
        assert "'Mixta'" not in sql  # sigue el esquema viejo
        assert conn.execute("SELECT COUNT(*) FROM visitas").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM elementos_visita").fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name='visitas_nueva'").fetchone()[0] == 0
        assert _n_auditoria_migracion(conn) == 0
    finally:
        conn.close()


def test_ruta_respaldo_nunca_pisa_uno_existente(tmp_path):
    db = tmp_path / "catdic_local.db"
    ahora = datetime(2000, 1, 2, 3, 4, 5)
    primera = database._ruta_respaldo(db, ahora)
    assert primera.name == "catdic_local.backup-20000102-030405.db"
    primera.write_bytes(b"SINTETICO")
    segunda = database._ruta_respaldo(db, ahora)
    assert segunda.name == "catdic_local.backup-20000102-030405 v2.db"
    segunda.write_bytes(b"SINTETICO")
    assert database._ruta_respaldo(db, ahora).name == "catdic_local.backup-20000102-030405 v3.db"
    assert primera.read_bytes() == b"SINTETICO"


# ---------- T6: rutas de Dropbox de los proyectos sembrados ----------

RUTA_VIEJA_P16 = ("SUPERVISION", "EN CURSO", "TORRE P16")
RUTA_VIEJA_ZOETRY = ("LEVANTAMIENTO", "HOTEL ZOETRY")


@pytest.fixture
def raiz_temporal(tmp_path, monkeypatch, bd_temporal):
    raiz = tmp_path / "Dropbox sintetico"
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(raiz))
    return raiz


def _carpetas(conn):
    return {r["id"]: r["carpeta_dropbox"] for r in conn.execute(
        "SELECT id, carpeta_dropbox FROM proyectos")}


def _auditoria_rutas(conn):
    return conn.execute(
        "SELECT entidad_id, modulo, detalle_json FROM auditoria "
        "WHERE accion='CORREGIR_RUTA_PROYECTO' ORDER BY id").fetchall()


def _sembrar_con_rutas_viejas(raiz: Path):
    """Simula una BD sembrada antes de T6: inserta P16 y Zoetry con las rutas viejas exactas."""
    database.inicializar_bd()
    conn = database.get_connection()
    ahora = datetime.now().isoformat()
    for pid, nombre, tipo, partes in (
        ("torre-p16", "Torre P16", "Supervisión", RUTA_VIEJA_P16),
        ("hotel-zoetry-h2-h5", "Hotel Zoetry Cap Cana · H2 y H5", "Levantamiento", RUTA_VIEJA_ZOETRY),
    ):
        conn.execute("""
            INSERT INTO proyectos (id, nombre, tipo, formato_defecto, carpeta_dropbox, actualizado)
            VALUES (?, ?, ?, 'X', ?, '2000-01-01T00:00:00')
        """, (pid, nombre, tipo, str(raiz.joinpath(*partes))))
    conn.commit()
    conn.close()


def test_siembra_nueva_usa_la_raiz_de_config_y_las_rutas_reales(raiz_temporal):
    database.inicializar_bd()
    database.sembrar_datos_iniciales_catdic()
    conn = database.get_connection()
    try:
        assert _carpetas(conn) == {
            "terra-living": str(raiz_temporal / "SUPERVISION" / "EN CURSO" / "TERRA LIVING"),
            "torre-p16": str(raiz_temporal / "SUPERVISION" / "EN CURSO" / "PROYECTO P16"),
            "hotel-zoetry-h2-h5": str(
                raiz_temporal / "LEVANTAMIENTO" / "LEV Y EVA" / "EN CURSO" / "ZOETRY CAP CANA"),
        }
        # BD nueva: nada que corregir, nada en auditoría
        assert _auditoria_rutas(conn) == []
        # P16 sigue sin planos_sellados (su layout no es §5.1)
        assert conn.execute(
            "SELECT planos_sellados FROM proyectos WHERE id='torre-p16'").fetchone()[0] == ""
    finally:
        conn.close()


def test_ruta_vieja_se_corrige_una_sola_vez(raiz_temporal):
    _sembrar_con_rutas_viejas(raiz_temporal)

    database.sembrar_datos_iniciales_catdic()
    conn = database.get_connection()
    try:
        carpetas = _carpetas(conn)
        assert carpetas["torre-p16"] == str(raiz_temporal / "SUPERVISION" / "EN CURSO" / "PROYECTO P16")
        assert carpetas["hotel-zoetry-h2-h5"] == str(
            raiz_temporal / "LEVANTAMIENTO" / "LEV Y EVA" / "EN CURSO" / "ZOETRY CAP CANA")
        filas = _auditoria_rutas(conn)
        assert [f["entidad_id"] for f in filas] == ["torre-p16", "hotel-zoetry-h2-h5"]
        assert all(f["modulo"] == "SISTEMA" for f in filas)
        det = json.loads(filas[0]["detalle_json"])
        assert det == {
            "ruta_vieja": str(raiz_temporal.joinpath(*RUTA_VIEJA_P16)),
            "ruta_nueva": carpetas["torre-p16"],
        }
        actualizado = conn.execute(
            "SELECT actualizado FROM proyectos WHERE id='torre-p16'").fetchone()[0]
        assert actualizado != "2000-01-01T00:00:00"
    finally:
        conn.close()

    # Segunda ejecución: 0 correcciones y sin auditoría nueva
    database.sembrar_datos_iniciales_catdic()
    conn = database.get_connection()
    try:
        assert database.corregir_rutas_proyectos(conn) == []
        assert len(_auditoria_rutas(conn)) == 2
    finally:
        conn.close()


def test_ruta_cambiada_a_mano_no_se_toca(raiz_temporal):
    _sembrar_con_rutas_viejas(raiz_temporal)
    a_mano = str(raiz_temporal / "OTRA CARPETA" / "P16 elegida por Steven")
    conn = database.get_connection()
    conn.execute("UPDATE proyectos SET carpeta_dropbox=? WHERE id='torre-p16'", (a_mano,))
    conn.commit()
    conn.close()

    database.sembrar_datos_iniciales_catdic()
    conn = database.get_connection()
    try:
        carpetas = _carpetas(conn)
        assert carpetas["torre-p16"] == a_mano
        # Zoetry sí tenía la ruta vieja exacta: se corrige
        assert carpetas["hotel-zoetry-h2-h5"].endswith(r"LEV Y EVA\EN CURSO\ZOETRY CAP CANA")
        assert [f["entidad_id"] for f in _auditoria_rutas(conn)] == ["hotel-zoetry-h2-h5"]
    finally:
        conn.close()


# ---------- T8: columna visitas.origen_datos_json ----------

def _crear_bd_t2_sin_origen(ruta: Path):
    """BD con el esquema de T2 (ya migrada) pero sin origen_datos_json, con una visita SINTÉTICA."""
    database.inicializar_bd()
    conn = sqlite3.connect(ruta)
    conn.execute("PRAGMA foreign_keys = OFF;")
    conn.execute("DROP TABLE visitas")
    sql_t2 = database._sql_tabla_visitas("visitas").replace(
        "        origen_datos_json TEXT DEFAULT '{}',      -- De dónde salió fecha/clase/estado (T8)\n",
        "")
    assert "origen_datos_json" not in sql_t2
    conn.execute(sql_t2)
    conn.execute("INSERT INTO proyectos (id, nombre, tipo, formato_defecto, actualizado) "
                 "VALUES ('SINTETICO-P', 'SINTETICO', 'Supervisión', 'X', '2000-01-01')")
    _insertar_visita(conn)
    conn.execute("DELETE FROM auditoria")
    conn.commit()
    conn.close()


def test_bd_nueva_trae_origen_datos_json_sin_auditoria(bd_temporal):
    database.inicializar_bd()
    conn = database.get_connection()
    try:
        cols = {r[1]: r for r in conn.execute("PRAGMA table_info(visitas)")}
        assert database.COLUMNA_ORIGEN_VISITAS in cols
        assert cols[database.COLUMNA_ORIGEN_VISITAS][4] == "'{}'"  # valor por defecto
        assert _n_auditoria_origen(conn) == 0
    finally:
        conn.close()


def test_columna_origen_se_anade_una_sola_vez_y_conserva_filas(bd_temporal):
    _crear_bd_t2_sin_origen(bd_temporal)
    respaldos_antes = _respaldos(bd_temporal.parent, bd_temporal.stem)

    database.inicializar_bd()  # migrar_visitas no reconstruye (ya migrada) y se añade la columna
    conn = database.get_connection()
    try:
        fila = dict(conn.execute("SELECT * FROM visitas WHERE id='SINTETICO-V1'").fetchone())
        for campo, valor in FILA_SINTETICA.items():
            assert fila[campo] == valor, campo
        assert fila["origen_datos_json"] == "{}"
        assert _n_auditoria_migracion(conn) == 0
        assert _n_auditoria_origen(conn) == 1
        detalle = json.loads(conn.execute(
            "SELECT detalle_json FROM auditoria WHERE accion='MIGRACION_VISITAS_ORIGEN'").fetchone()[0])
        assert detalle == {"columna": "origen_datos_json", "valor_por_defecto": "{}",
                           "filas_existentes": 1}
        sql_1 = conn.execute("SELECT sql FROM sqlite_master WHERE name='visitas'").fetchone()[0]
    finally:
        conn.close()
    # No destructiva: sin respaldo extra
    assert _respaldos(bd_temporal.parent, bd_temporal.stem) == respaldos_antes

    # Segunda vez: nada cambia ni se audita
    assert database.agregar_columna_origen_visitas() == {"agregada": False, "motivo": "ya existe"}
    database.inicializar_bd()
    conn = database.get_connection()
    try:
        assert conn.execute("SELECT sql FROM sqlite_master WHERE name='visitas'").fetchone()[0] == sql_1
        assert _n_auditoria_origen(conn) == 1
    finally:
        conn.close()


# ---------- Etapa 2 · T1 — elementos_diseno: UNIQUE, fuente_json, pendientes_json ----------

def _crear_bd_diseno_vieja(ruta: Path, con_fila: bool = True):
    """BD con 'elementos_diseno' del esquema anterior a la Etapa 2 (SINTÉTICO)."""
    conn = sqlite3.connect(ruta)
    conn.executescript("""
        CREATE TABLE proyectos (id TEXT PRIMARY KEY);
        CREATE TABLE elementos_diseno (
            uid TEXT PRIMARY KEY,
            proyecto_id TEXT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
            id_elemento TEXT NOT NULL, tipo_elemento TEXT NOT NULL,
            nivel_rango TEXT NOT NULL, ejes TEXT NOT NULL,
            hoja_plano_origen TEXT NOT NULL, archivo_plano_origen TEXT NOT NULL,
            datos_diseno_json TEXT NOT NULL, estado_campos_json TEXT NOT NULL,
            recorte_planta_json TEXT DEFAULT '{}', recorte_detalle_json TEXT DEFAULT '{}',
            actualizado TEXT NOT NULL
        );
        CREATE TABLE elementos_visita (
            uid TEXT PRIMARY KEY,
            elemento_diseno_uid TEXT REFERENCES elementos_diseno(uid)
        );
        CREATE TABLE auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT, usuario TEXT,
            modulo TEXT, accion TEXT, entidad_id TEXT, detalle_json TEXT
        );
        INSERT INTO proyectos VALUES ('SINTETICO-P');
    """)
    if con_fila:
        conn.execute(
            "INSERT INTO elementos_diseno VALUES ('SINTETICO-U1','SINTETICO-P','C1','COLUMNA',"
            "'S-4','EJE F-11','ES-05','sintetico.pdf','{}','{}','{}','{}','2026-10-22')")
        conn.execute("INSERT INTO elementos_visita VALUES ('SINTETICO-EV1','SINTETICO-U1')")
    conn.commit()
    conn.close()


def _n_audit_diseno(conn):
    return conn.execute(
        "SELECT COUNT(*) FROM auditoria WHERE accion='MIGRACION_ELEMENTOS_DISENO'").fetchone()[0]


def _insertar_diseno(conn, uid, id_elemento="C2", nivel="S-4", ejes="EJE F-12"):
    conn.execute(
        "INSERT INTO elementos_diseno (uid, proyecto_id, id_elemento, tipo_elemento, nivel_rango,"
        " ejes, hoja_plano_origen, archivo_plano_origen, datos_diseno_json, estado_campos_json,"
        " actualizado) VALUES (?, 'SINTETICO-P', ?, 'COLUMNA', ?, ?, 'ES-05', 's.pdf', '{}', '{}', 'x')",
        (uid, id_elemento, nivel, ejes))


def test_migrar_diseno_conserva_filas_fk_respalda_y_audita(bd_temporal):
    _crear_bd_diseno_vieja(bd_temporal)
    resultado = database.migrar_elementos_diseno()
    assert resultado["migrada"] is True
    assert Path(resultado["respaldo"]).exists()
    assert resultado["columnas_nuevas"] == ["fuente_json", "pendientes_json"]
    conn = database.get_connection()
    try:
        fila = conn.execute("SELECT * FROM elementos_diseno WHERE uid='SINTETICO-U1'").fetchone()
        assert fila["id_elemento"] == "C1" and fila["ejes"] == "EJE F-11"
        assert fila["fuente_json"] == "{}" and fila["pendientes_json"] == "[]"
        assert conn.execute("SELECT elemento_diseno_uid FROM elementos_visita").fetchone()[0] == "SINTETICO-U1"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert _n_audit_diseno(conn) == 1
    finally:
        conn.close()


def test_migrar_diseno_dos_veces_no_cambia_nada(bd_temporal):
    _crear_bd_diseno_vieja(bd_temporal)
    database.migrar_elementos_diseno()
    respaldos = _respaldos(bd_temporal.parent, bd_temporal.stem)
    assert database.migrar_elementos_diseno() == {
        "migrada": False, "motivo": "ya migrada", "respaldo": None}
    assert _respaldos(bd_temporal.parent, bd_temporal.stem) == respaldos
    conn = database.get_connection()
    try:
        assert _n_audit_diseno(conn) == 1
    finally:
        conn.close()


def test_unique_diseno_rechaza_duplicado_en_bd_migrada_y_en_bd_nueva(bd_temporal, tmp_path, monkeypatch):
    _crear_bd_diseno_vieja(bd_temporal)
    database.migrar_elementos_diseno()
    conn = database.get_connection()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            _insertar_diseno(conn, "SINTETICO-U2", "C1", "S-4", "EJE F-11")  # duplicado de U1
        _insertar_diseno(conn, "SINTETICO-U3", "C1", "S-3", "EJE F-11")      # otro nivel: permitido
    finally:
        conn.close()

    nueva = tmp_path / "nueva.db"
    monkeypatch.setenv(config.ENV_DB_PATH, str(nueva))
    database.inicializar_bd()
    conn = database.get_connection()
    try:
        conn.execute("INSERT INTO proyectos (id, nombre, tipo, formato_defecto, actualizado)"
                     " VALUES ('SINTETICO-P','x','Supervisión','STP-MIVED','x')")
        _insertar_diseno(conn, "A1")
        with pytest.raises(sqlite3.IntegrityError):
            _insertar_diseno(conn, "A2")
        assert _n_audit_diseno(conn) == 0  # BD nueva: sin migración ni respaldo
    finally:
        conn.close()
    assert _respaldos(nueva.parent, nueva.stem) == []


def test_migrar_diseno_con_duplicados_previos_revierte(bd_temporal):
    _crear_bd_diseno_vieja(bd_temporal)
    conn = sqlite3.connect(bd_temporal)
    conn.execute("INSERT INTO elementos_diseno VALUES ('SINTETICO-U9','SINTETICO-P','C1','COLUMNA',"
                 "'S-4','EJE F-11','ES-05','s.pdf','{}','{}','{}','{}','x')")
    conn.commit()
    conn.close()
    with pytest.raises(sqlite3.IntegrityError):
        database.migrar_elementos_diseno()
    conn = sqlite3.connect(bd_temporal)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(elementos_diseno)")}
        assert "fuente_json" not in cols
        assert conn.execute("SELECT COUNT(*) FROM elementos_diseno").fetchone()[0] == 2
    finally:
        conn.close()
