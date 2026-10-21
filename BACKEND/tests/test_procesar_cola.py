# BACKEND/tests/test_procesar_cola.py
# Etapa 1 · T9 — "Procesar Cola" desactivado hasta la Etapa 3 (PLANES/etapa-1.md: T9).
#
# BD temporal (CATDIC_DB_PATH). Las visitas se insertan con SQL directo.
#   - "# SINTÉTICO: ..." -> dato inventado solo para probar la regla; no es dato de proyecto.
import sqlite3

import pytest
from fastapi.testclient import TestClient

import config
import main

VISITAS_SINTETICAS = [
    # SINTÉTICO: una visita 'Sin procesar' y otra 'En cola' del proyecto sembrado terra-living
    ("terra-living-901-prueba-sin-procesar", 901, "901. PRUEBA SIN PROCESAR 01-01-2026",
     "2026-01-01", "Parcial", "Sin procesar"),
    ("terra-living-902-prueba-en-cola", 902, "902. PRUEBA EN COLA 02-01-2026",
     "2026-01-02", "Completivo", "En cola"),
]


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    """BD temporal; el startup de FastAPI crea el esquema y siembra los proyectos."""
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "catdic_test.db"))
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "dropbox"))  # nunca el real
    with TestClient(main.app) as c:
        with _bd() as conn:
            for vid, numero, carpeta, fecha, clase, estado in VISITAS_SINTETICAS:
                conn.execute(
                    """INSERT INTO visitas (id, proyecto_id, numero, nombre_carpeta, ruta_carpeta,
                           fecha_visita, clase, estado, formatos_solicitados, actualizado)
                       VALUES (?, 'terra-living', ?, ?, ?, ?, ?, ?, '["STP-MIVED"]',
                               '2026-01-01 00:00:00')""",
                    (vid, numero, carpeta, str(tmp_path / "dropbox" / carpeta),
                     fecha, clase, estado))  # SINTÉTICO
        yield c


def _bd():
    conn = sqlite3.connect(config.obtener_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _foto_bd():
    with _bd() as conn:
        visitas = [dict(f) for f in conn.execute("SELECT * FROM visitas ORDER BY id")]
        n_auditoria = conn.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]
    return visitas, n_auditoria


def test_procesar_cola_responde_409_y_no_toca_la_bd(cliente):
    visitas_antes, auditoria_antes = _foto_bd()
    assert {v["estado"] for v in visitas_antes} >= {"Sin procesar", "En cola"}

    r = cliente.post("/api/visitas/procesar-cola")

    assert r.status_code == 409
    assert r.json() == {"detail": main.MENSAJE_PROCESAR_COLA_DESACTIVADO}
    assert "Etapa 3" in r.json()["detail"]
    visitas_despues, auditoria_despues = _foto_bd()
    assert visitas_despues == visitas_antes  # ni estado ni 'actualizado'
    assert auditoria_despues == auditoria_antes


def test_procesar_cola_repetido_sigue_sin_cambiar_nada(cliente):
    antes = _foto_bd()
    for _ in range(3):
        assert cliente.post("/api/visitas/procesar-cola").status_code == 409
    assert _foto_bd() == antes
