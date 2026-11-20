# Fundación F2 · auditoría con identidad real (contrato §4 y §6): cada cambio hecho por una persona autenticada
# deja su usuario_id en la misma transacción; si la fila de auditoría no se puede escribir, el cambio no ocurre.
import sqlite3

import pytest
from fastapi.testclient import TestClient

import database
import main
import procesador_cola
from f2_ayudas import CABECERAS, CONTRASENA, cliente, crear_persona, dar, filas, preparar_entorno
from identidad import contexto

pytestmark = pytest.mark.seguridad_real

OBRA = "terra-living"


@pytest.fixture
def persona(tmp_path, monkeypatch):
    preparar_entorno(tmp_path, monkeypatch)
    p = crear_persona("persona-a")
    dar(p, OBRA, "preparar", "revisar_autorizar")
    return p


def test_ruta_anterior_a_f2_audita_con_el_usuario_real(persona):
    """PATCH /api/proyectos escribe su auditoría como siempre; la fila sale con el usuario de la sesión."""
    with cliente(main.app, persona) as c:
        r = c.patch(f"/api/proyectos/{OBRA}", json={"avance_informe": 40})
        assert r.status_code == 200, r.text
    f = filas("SELECT usuario, usuario_id FROM auditoria WHERE accion = 'ACTUALIZAR_PROYECTO'")
    assert f == [{"usuario": "persona-a", "usuario_id": persona.id}]


def test_patch_de_obra_con_version_vieja_da_409(persona):
    with cliente(main.app, persona) as c:
        version = filas("SELECT version FROM proyectos WHERE id = ?", (OBRA,))[0]["version"] or 1
        assert c.patch(f"/api/proyectos/{OBRA}", json={"avance_informe": 10, "version": version}).status_code == 200
        r = c.patch(f"/api/proyectos/{OBRA}", json={"avance_informe": 20, "version": version})
        assert r.status_code == 409
    assert filas("SELECT avance_informe FROM proyectos WHERE id = ?", (OBRA,))[0]["avance_informe"] == 10
    assert len(filas("SELECT 1 FROM auditoria WHERE accion = 'ACTUALIZAR_PROYECTO'")) == 1


def test_si_la_auditoria_falla_el_cambio_no_ocurre(persona):
    conn = sqlite3.connect(database.config.obtener_db_path())
    conn.execute("""CREATE TRIGGER prueba_auditoria_rota BEFORE INSERT ON auditoria
                    WHEN NEW.modulo IN ('PROYECTOS', 'PEDIDOS')
                    BEGIN SELECT RAISE(ABORT, 'auditoria no disponible'); END""")
    conn.commit()
    conn.close()
    antes = filas("SELECT * FROM proyectos WHERE id = ?", (OBRA,))
    with TestClient(main.app, headers=CABECERAS, raise_server_exceptions=False) as c:
        assert c.post("/api/sesion", json={"usuario": persona.usuario, "contrasena": CONTRASENA}).status_code == 200
        assert c.patch(f"/api/proyectos/{OBRA}", json={"avance_informe": 77}).status_code == 500
        assert c.post(f"/api/obras/{OBRA}/pedidos", json={"proposito": "No debe quedar"}).status_code == 500
    assert filas("SELECT * FROM proyectos WHERE id = ?", (OBRA,)) == antes
    assert filas("SELECT COUNT(*) AS n FROM pedidos")[0]["n"] == 0


def test_dudas_llevan_autor_y_origen(persona):
    token = contexto.fijar(contexto.Usuario(persona.id, persona.usuario))
    try:
        conn = database.get_connection()
        conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, id_elemento, categoria, campo_afectado,
                        descripcion_pregunta, creado) VALUES (?, 'C1', 'DUDA_BLOQUEANTE', 'EJES', 'IA: lectura ficticia', 'x'),
                        (?, 'C2', 'DUDA_BLOQUEANTE', 'EJES', 'Pregunta ficticia', 'x')""", (OBRA, OBRA))
        conn.commit()
        conn.close()
    finally:
        contexto.restaurar(token)
    conn = database.get_connection()      # sin usuario (p. ej. un script local): autor vacío, origen igual
    conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, id_elemento, categoria, campo_afectado,
                    descripcion_pregunta, creado) VALUES (?, 'C3', 'DUDA_BLOQUEANTE', 'EJES', 'Otra pregunta', 'x')""",
                 (OBRA,))
    conn.commit()
    conn.close()
    dudas = {f["id_elemento"]: (f["autor_id"], f["origen"]) for f in
             filas("SELECT id_elemento, autor_id, origen FROM dudas_y_hallazgos WHERE id_elemento IN ('C1','C2','C3')")}
    assert dudas == {"C1": (persona.id, "ia"), "C2": (persona.id, "programa"), "C3": (None, "programa")}


def test_el_hilo_del_trabajo_hereda_el_usuario(persona, monkeypatch):
    vistos = []

    def ejecutar_falso(trabajo_id):
        vistos.append(contexto.actual())
        database.registrar_auditoria("COLA", "PASO_DEL_HILO", trabajo_id, {})
        conn = database.get_connection()
        conn.execute("UPDATE trabajos SET estado = 'terminado' WHERE id = ?", (trabajo_id,))
        conn.commit()
        conn.close()

    monkeypatch.setattr(procesador_cola, "ejecutar_trabajo", ejecutar_falso)
    conn = database.get_connection()
    conn.execute("""INSERT INTO visitas (id, proyecto_id, numero, nombre_carpeta, ruta_carpeta, fecha_visita, clase,
                    estado, formatos_solicitados, actualizado) VALUES ('v-h', ?, 1, 'VISITA FICTICIA', 'r', '2026-01-02',
                    'Parcial', 'Sin procesar', '[]', 'x')""", (OBRA,))
    conn.commit()
    conn.close()
    token = contexto.fijar(contexto.Usuario(persona.id, persona.usuario))
    try:
        t = procesador_cola.lanzar_trabajo(["v-h"])
        procesador_cola.esperar(t["id"], 10)
    finally:
        contexto.restaurar(token)
    assert [u.id for u in vistos] == [persona.id]
    assert filas("SELECT usuario, usuario_id FROM trabajos WHERE id = ?", (t["id"],)) == [
        {"usuario": "persona-a", "usuario_id": persona.id}]
    assert filas("SELECT usuario_id FROM auditoria WHERE accion IN ('LANZAR_TRABAJO', 'PASO_DEL_HILO')") == [
        {"usuario_id": persona.id}] * 2


def test_llamadas_locales_sin_sesion_siguen_como_antes(persona):
    """Un script local (sin petición HTTP) no tiene usuario: la fila conserva el texto de siempre y sin usuario_id."""
    database.registrar_auditoria("PRUEBA", "LOCAL", "x", {})
    assert filas("SELECT usuario, usuario_id FROM auditoria WHERE accion = 'LOCAL'") == [
        {"usuario": "steven", "usuario_id": None}]
