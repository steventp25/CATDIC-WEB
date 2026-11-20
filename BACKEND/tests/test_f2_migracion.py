# Fundación F2 · migración conservadora (escenario 4 del §7): solo aditiva, con respaldo previo, idempotente,
# conserva ids y filas, no toca la auditoría histórica y, si algo falla, no deja nada a medias.
import sqlite3
from pathlib import Path

import pytest

import config
import database
import migracion_fundacion
from f2_ayudas import filas

pytestmark = pytest.mark.seguridad_real

NUEVAS = ("usuarios", "sesiones", "membresias", "obra_servicios", "intentos_entrada", "pedidos", "pedido_fuentes")


@pytest.fixture
def base_anterior(tmp_path, monkeypatch):
    """Una base con el esquema y los datos de antes de F2 (la migración F2 se omite al crearla)."""
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "anterior.db"))
    real = migracion_fundacion.migrar_fundacion_f2
    monkeypatch.setattr(migracion_fundacion, "migrar_fundacion_f2", lambda: {"migrada": False})
    database.inicializar_bd()
    database.sembrar_datos_iniciales_catdic()
    monkeypatch.setattr(migracion_fundacion, "migrar_fundacion_f2", real)
    conn = sqlite3.connect(tmp_path / "anterior.db")
    conn.executescript("""
        INSERT INTO dudas_y_hallazgos (proyecto_id, id_elemento, categoria, campo_afectado, descripcion_pregunta, creado)
        VALUES ('terra-living', 'C1', 'DUDA_BLOQUEANTE', 'IA: EJES', 'IA: lectura ficticia por confirmar', 'x'),
               ('terra-living', 'C2', 'DUDA_BLOQUEANTE', 'EJES', 'Pregunta ficticia del programa', 'x');
        INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
        VALUES ('2026-01-01T00:00:00', 'steven', 'PRUEBA', 'HISTORICA', 'x', '{}');
    """)
    conn.commit()
    conn.close()
    return tmp_path / "anterior.db"


def _foto(ruta: Path) -> dict:
    conn = sqlite3.connect(ruta)
    try:
        return {t: conn.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall()
                for t in ("proyectos", "visitas", "dudas_y_hallazgos", "elementos_diseno", "ordenes_trabajo")}
    finally:
        conn.close()


def _historica(ruta: Path) -> list:
    conn = sqlite3.connect(ruta)
    try:
        return conn.execute("SELECT id, fecha_hora, usuario, modulo, accion, entidad_id, detalle_json FROM auditoria "
                            "WHERE accion != 'MIGRACION_FUNDACION_F2' ORDER BY id").fetchall()
    finally:
        conn.close()


def test_migracion_aditiva_idempotente_y_con_respaldo(base_anterior):
    conn = database.get_connection()
    assert set(migracion_fundacion.pendiente(conn)["tablas"]) == set(NUEVAS)
    conn.close()
    antes, historica = _foto(base_anterior), _historica(base_anterior)

    r1 = migracion_fundacion.migrar_fundacion_f2()
    assert r1["migrada"] is True and r1["respaldo"]
    respaldo = Path(r1["respaldo"])
    assert respaldo.exists() and respaldo.parent == base_anterior.parent
    # El respaldo es la base de antes, sin las tablas nuevas
    copia = sqlite3.connect(respaldo)
    assert copia.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'usuarios'").fetchone()[0] == 0
    copia.close()

    # Segunda vez: nada pendiente, ni respaldo nuevo ni otra fila de auditoría
    r2 = migracion_fundacion.migrar_fundacion_f2()
    assert r2 == {"migrada": False, "motivo": "ya migrada", "respaldo": None}
    database.inicializar_bd()                      # arrancar otra vez el servidor tampoco hace nada
    assert len(list(base_anterior.parent.glob("anterior.backup-*.db"))) == 1
    assert len(filas("SELECT 1 FROM auditoria WHERE accion = 'MIGRACION_FUNDACION_F2'")) == 1

    # Filas e ids intactos (las tablas viejas solo ganan columnas al final)
    despues = _foto(base_anterior)
    for tabla, filas_antes in antes.items():
        assert [f[:len(filas_antes[0])] if filas_antes else f for f in despues[tabla]] == filas_antes, tabla
    # La auditoría histórica ('steven' en texto) queda igual y sin usuario_id
    assert _historica(base_anterior)[:len(historica)] == historica
    assert all(f["usuario_id"] is None for f in filas("SELECT usuario_id FROM auditoria"))

    conn = database.get_connection()
    try:
        assert migracion_fundacion.pendiente(conn) == {}
        assert all(conn.execute(f"SELECT 1 FROM sqlite_master WHERE name = '{t}'").fetchone() for t in NUEVAS)
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        # Un servicio por obra, desde su tipo (ninguna obra duplicada)
        obras = {f["id"]: f["tipo"] for f in conn.execute("SELECT id, tipo FROM proyectos")}
        servicios = {f["obra_id"]: f["servicio"] for f in conn.execute("SELECT obra_id, servicio FROM obra_servicios")}
        assert servicios == {k: v for k, v in obras.items() if v in ("Supervisión", "Levantamiento")}
        # El origen de las dudas existentes se rellena sin cambiar su texto
        origen = {f["id_elemento"]: (f["origen"], f["descripcion_pregunta"])
                  for f in conn.execute("SELECT id_elemento, origen, descripcion_pregunta FROM dudas_y_hallazgos")}
        assert origen["C1"] == ("ia", "IA: lectura ficticia por confirmar")
        assert origen["C2"] == ("programa", "Pregunta ficticia del programa")
        # estado_campos_json no cambia de forma (ni siquiera de tipo de columna)
        tipos = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(elementos_diseno)")}
        assert "estado_campos_json" not in tipos or tipos["estado_campos_json"] == "TEXT"
    finally:
        conn.close()


def test_obra_nueva_recibe_su_servicio_y_la_funcion_administrar_no_existe(base_anterior):
    migracion_fundacion.migrar_fundacion_f2()
    conn = database.get_connection()
    try:
        conn.execute("""INSERT INTO proyectos (id, nombre, tipo, formato_defecto, actualizado)
                        VALUES ('obra-ficticia', 'Obra ficticia', 'Levantamiento', 'HV-LEV', 'x')""")
        conn.commit()
        assert conn.execute("SELECT servicio FROM obra_servicios WHERE obra_id = 'obra-ficticia'").fetchone()[0] == \
            "Levantamiento"
        assert "administrar" not in migracion_fundacion.FUNCIONES_OBRA
    finally:
        conn.close()


def test_si_la_migracion_falla_no_queda_nada_a_medias(base_anterior, monkeypatch):
    antes = _foto(base_anterior)
    monkeypatch.setitem(migracion_fundacion.INDICES, "idx_roto", "CREATE INDEX idx_roto ON tabla_que_no_existe(x)")
    with pytest.raises(sqlite3.OperationalError):
        migracion_fundacion.migrar_fundacion_f2()
    conn = sqlite3.connect(base_anterior)
    try:
        # Ni tablas ni columnas nuevas: la transacción se deshizo entera
        assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name IN (%s)" % ",".join("?" * len(NUEVAS)),
                            NUEVAS).fetchone()[0] == 0
        assert "usuario_id" not in {r[1] for r in conn.execute("PRAGMA table_info(auditoria)")}
        assert conn.execute("SELECT COUNT(*) FROM auditoria WHERE accion = 'MIGRACION_FUNDACION_F2'").fetchone()[0] == 0
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()
    assert _foto(base_anterior) == antes
    # El respaldo previo sí existe, y al quitar la causa la migración se completa
    assert len(list(base_anterior.parent.glob("anterior.backup-*.db"))) == 1
    monkeypatch.delitem(migracion_fundacion.INDICES, "idx_roto")
    assert migracion_fundacion.migrar_fundacion_f2()["migrada"] is True
