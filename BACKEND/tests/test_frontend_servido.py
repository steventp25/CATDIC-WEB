# Pruebas del servidor local unificado (frontend + API).
from fastapi.testclient import TestClient

import config
import main


def test_raiz_entrega_el_tablero_local(tmp_path, monkeypatch):
    """El servidor local entrega el index sin necesidad de abrir file://."""
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "catdic_test.db"))
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "dropbox"))

    with TestClient(main.app) as cliente:
        respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert "Control Taller" in respuesta.text
    assert "localhost:8000" in respuesta.text
