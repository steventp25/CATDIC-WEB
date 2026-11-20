# Fundación F2 · interfaz mínima (página de entrada y envoltorio de fetch) y alta inicial local.
import builtins
import getpass

import pytest

import main
from f2_ayudas import cliente, filas, preparar_entorno
from identidad import alta_inicial

pytestmark = pytest.mark.seguridad_real


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    preparar_entorno(tmp_path, monkeypatch)


def test_paginas_se_sirven_sin_sesion_y_la_api_no(entorno):
    with cliente(main.app) as c:
        entrada = c.get("/entrar.html")
        assert entrada.status_code == 200 and "X-CATDIC-Peticion" in entrada.text and "/api/sesion" in entrada.text
        inicio = c.get("/")
        assert inicio.status_code == 200
        # El tablero clásico manda el encabezado propio en las mutaciones y vuelve a la entrada con 401
        assert "X-CATDIC-Peticion" in inicio.text and "/entrar.html" in inicio.text
        assert "credentials: 'same-origin'" in inicio.text
        assert c.get("/api/dashboard").status_code == 401


def _respuestas(monkeypatch, entradas, contrasenas):
    entradas, contrasenas = iter(entradas), iter(contrasenas)
    monkeypatch.setattr(builtins, "input", lambda _="": next(entradas))
    monkeypatch.setattr(getpass, "getpass", lambda _="": next(contrasenas))


def test_alta_inicial_crea_usuario_con_obras_y_puede_entrar(entorno, monkeypatch):
    obras = [f["id"] for f in filas("SELECT id FROM proyectos ORDER BY nombre")]
    funciones = ["preparar, revisar_autorizar"] + ["administrar, consultar"] + [""] * (len(obras) - 2)
    _respuestas(monkeypatch, ["persona.local", "Persona local de prueba", "n", *funciones],
                ["corta", "clave-local-larga", "clave-local-larga"])
    assert alta_inicial.main([]) == 0
    m = {f["obra_id"]: f["funciones"] for f in filas("SELECT obra_id, funciones FROM membresias")}
    assert m == {obras[0]: '["preparar", "revisar_autorizar"]', obras[1]: '["consultar"]'}   # 'administrar' no existe
    with cliente(main.app) as c:
        assert c.post("/api/sesion", json={"usuario": "persona.local", "contrasena": "clave-local-larga"}).status_code == 200
        # Cambiar la contraseña cierra la sesión abierta
        _respuestas(monkeypatch, [], ["otra-clave-larga", "otra-clave-larga"])
        assert alta_inicial.main(["--contrasena", "persona.local"]) == 0
        assert c.get("/api/sesion").status_code == 401
        assert c.post("/api/sesion", json={"usuario": "persona.local", "contrasena": "otra-clave-larga"}).status_code == 200
    texto = " ".join(f["detalle_json"] or "" for f in filas("SELECT detalle_json FROM auditoria"))
    assert "clave-local-larga" not in texto and "otra-clave-larga" not in texto
