# Fundación F2 · concurrencia real en SQLite (escenario 11 del §7) sobre el esquema y la conexión de la app:
# varios hilos por la API, varios procesos a la vez, una transacción larga y un proceso que cae a mitad.
# Las cifras de rendimiento (p50/p95, delete vs. WAL) las da tests/medir_concurrencia_f2.py; aquí se exige que
# no se pierda ni se duplique nada y que nadie vea «database is locked».
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

import config
import database
import main
from f2_ayudas import cliente, crear_persona, dar, filas, preparar_entorno

pytestmark = pytest.mark.seguridad_real

OBRA = "terra-living"
BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def gente(tmp_path, monkeypatch):
    preparar_entorno(tmp_path, monkeypatch)
    ps = [crear_persona(f"persona-{i}") for i in range(6)]
    for p in ps:
        dar(p, OBRA, "preparar")
    return ps


def test_muchos_hilos_editan_por_la_api_sin_perder_cambios(gente):
    """6 personas × 15 ediciones sobre el mismo pedido: cada 200 es una versión y una fila de auditoría; el resto 409."""
    with cliente(main.app, gente[0]) as c:
        pedido_id = c.post(f"/api/obras/{OBRA}/pedidos", json={"proposito": "Concurrido"}).json()["pedido"]["id"]
    resultados, errores = [], []

    def persona(p):
        try:
            with cliente(main.app, p) as c:
                for i in range(15):
                    v = c.get(f"/api/pedidos/{pedido_id}").json()["pedido"]["version"]
                    r = c.patch(f"/api/pedidos/{pedido_id}", json={"version": v, "progreso": {"quien": p.usuario, "i": i}})
                    resultados.append(r.status_code)
        except Exception as exc:  # noqa: BLE001 — se informa abajo
            errores.append(repr(exc))

    hilos = [threading.Thread(target=persona, args=(p,)) for p in gente]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(120)
    assert errores == [] and len(resultados) == 90
    assert set(resultados) <= {200, 409}
    ok = resultados.count(200)
    final = filas("SELECT version FROM pedidos WHERE id = ?", (pedido_id,))[0]["version"]
    auditadas = len(filas("SELECT 1 FROM auditoria WHERE modulo = 'PEDIDOS' AND accion = 'EDITAR'"))
    assert final - 1 == ok == auditadas and ok >= 15
    assert filas("PRAGMA integrity_check")[0]["integrity_check"] == "ok"


_ESCRITOR = r"""
import sys
sys.path.insert(0, sys.argv[1])
import database
n, quien = int(sys.argv[2]), sys.argv[3]
for i in range(n):
    conn = database.get_connection()
    conn.isolation_level = None
    conn.execute("BEGIN IMMEDIATE")
    v = conn.execute("SELECT version FROM proyectos WHERE id = 'terra-living'").fetchone()[0] or 1
    cur = conn.execute("UPDATE proyectos SET version = ? WHERE id = 'terra-living' AND COALESCE(version, 1) = ?", (v + 1, v))
    assert cur.rowcount == 1
    conn.execute("INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json) "
                 "VALUES ('x', ?, 'PRUEBA', 'CONCURRENCIA', ?, '{}')", (quien, str(v + 1)))
    conn.execute("COMMIT")
    conn.close()
print("FIN", flush=True)
"""


def test_varios_procesos_escriben_a_la_vez_sin_bloqueos_ni_perdidas(gente):
    """4 procesos + el de la prueba, 40 transacciones cada uno sobre la misma fila, con la espera de get_connection."""
    v0 = filas("SELECT COALESCE(version, 1) AS v FROM proyectos WHERE id = ?", (OBRA,))[0]["v"]
    entorno = {**os.environ, config.ENV_DB_PATH: str(config.obtener_db_path())}
    procesos = [subprocess.Popen([sys.executable, "-c", _ESCRITOR, str(BACKEND), "40", f"proc{i}"], env=entorno,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(4)]
    for i in range(40):
        conn = database.get_connection()
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        v = conn.execute("SELECT COALESCE(version, 1) FROM proyectos WHERE id = ?", (OBRA,)).fetchone()[0]
        conn.execute("UPDATE proyectos SET version = ? WHERE id = ?", (v + 1, OBRA))
        conn.execute("INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json) "
                     "VALUES ('x', 'prueba', 'PRUEBA', 'CONCURRENCIA', ?, '{}')", (str(v + 1),))
        conn.execute("COMMIT")
        conn.close()
    salidas = [p.communicate(timeout=120) for p in procesos]
    assert [p.returncode for p in procesos] == [0] * 4, [e for _, e in salidas]
    assert all("locked" not in e for _, e in salidas)
    v = filas("SELECT version FROM proyectos WHERE id = ?", (OBRA,))[0]["version"]
    versiones = [int(f["entidad_id"]) for f in filas("SELECT entidad_id FROM auditoria WHERE accion = 'CONCURRENCIA'")]
    assert v - v0 == 200 == len(versiones) == len(set(versiones))     # ni perdida ni duplicada
    assert filas("PRAGMA integrity_check")[0]["integrity_check"] == "ok"


def test_transaccion_larga_no_bloquea_lecturas_y_la_escritura_espera(gente):
    """Mientras otra conexión escribe durante 2 s, la API lee al instante y su escritura espera y entra (no 500)."""
    listo, soltar = threading.Event(), threading.Event()

    def larga():
        conn = database.get_connection()
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE proyectos SET avance_informe = 5 WHERE id = ?", (OBRA,))
        listo.set()
        soltar.wait(10)
        conn.execute("COMMIT")
        conn.close()

    with cliente(main.app, gente[0]) as c:
        h = threading.Thread(target=larga)
        h.start()
        listo.wait(5)
        t0 = time.perf_counter()
        assert c.get("/api/dashboard").status_code == 200
        lectura = time.perf_counter() - t0
        threading.Timer(2.0, soltar.set).start()
        t0 = time.perf_counter()
        r = c.post(f"/api/obras/{OBRA}/pedidos", json={"proposito": "Espera su turno"})
        escritura = time.perf_counter() - t0
        h.join(10)
    assert r.status_code == 201, r.text
    assert lectura < 1.5                     # el lector no espera a la transacción larga
    assert 1.5 <= escritura < database.ESPERA_BD_SEGUNDOS   # el escritor sí espera, y entra antes del límite


_CAE = r"""
import sys
sys.path.insert(0, sys.argv[1])
import database
conn = database.get_connection()
conn.isolation_level = None
conn.execute("BEGIN IMMEDIATE")
for i in range(300):
    conn.execute("INSERT INTO pedidos (obra_id, proposito, estado, progreso_json, version, creado_en, actualizado_en) "
                 "VALUES ('terra-living', ?, 'borrador', '{}', 1, 'x', 'x')", ("a medias %d " % i + "x" * 3000,))
    conn.execute("INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json) "
                 "VALUES ('x', 'caida', 'PEDIDOS', 'CREAR', ?, '{}')", (str(i),))
print("DENTRO", flush=True)
sys.stdin.readline()
"""


def test_caida_a_mitad_de_transaccion_no_deja_nada_a_medias(gente):
    entorno = {**os.environ, config.ENV_DB_PATH: str(config.obtener_db_path())}
    p = subprocess.Popen([sys.executable, "-c", _CAE, str(BACKEND)], env=entorno, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == "DENTRO"
    p.kill()                                  # como un corte de luz: sin COMMIT ni ROLLBACK
    p.wait(10)
    with cliente(main.app, gente[0]) as c:    # la app sigue: la primera escritura deshace el diario
        r = c.post(f"/api/obras/{OBRA}/pedidos", json={"proposito": "Después de la caída"})
        assert r.status_code == 201, r.text
        assert [x["proposito"] for x in c.get(f"/api/obras/{OBRA}/pedidos").json()["pedidos"]] == ["Después de la caída"]
    assert filas("SELECT COUNT(*) AS n FROM auditoria WHERE usuario = 'caida'")[0]["n"] == 0
    assert filas("PRAGMA integrity_check")[0]["integrity_check"] == "ok"
    assert filas("PRAGMA foreign_key_check") == []
