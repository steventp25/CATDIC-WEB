# Fundación F2: ayudas de las pruebas de identidad y permisos. Todo es ficticio: usuarios de prueba sin datos
# personales y una contraseña de prueba que solo existe aquí (no es de nadie).
import json
from contextlib import contextmanager
from dataclasses import dataclass

import pymupdf
from fastapi.testclient import TestClient

import config
import database
from identidad import sesiones

CONTRASENA = "clave-de-prueba-f2"     # ficticia, solo para las pruebas
ORIGEN = "http://testserver"
CABECERAS = {"Origin": ORIGEN, "X-CATDIC-Peticion": "1"}


@dataclass
class Persona:
    id: int
    usuario: str


def preparar_entorno(tmp_path, monkeypatch, nombre_bd: str = "f2.db"):
    """Base, Dropbox, datos y caché en carpetas temporales; nunca la base real ni Dropbox."""
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / nombre_bd))
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "raiz-sincronizada"))
    monkeypatch.setenv(config.ENV_DATOS_RAIZ, str(tmp_path / "datos"))
    monkeypatch.setenv(config.ENV_CACHE_RAIZ, str(tmp_path / "cache"))
    monkeypatch.setenv(config.ENV_SALIDA_PRUEBAS, str(tmp_path / "salida"))
    database.inicializar_bd()
    database.sembrar_datos_iniciales_catdic()


def crear_persona(usuario: str, es_admin: bool = False, contrasena: str = CONTRASENA) -> Persona:
    conn = database.get_connection()
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        u = sesiones.crear_usuario(conn, usuario, f"Persona de prueba {usuario}", contrasena, es_admin, None)
        conn.execute("COMMIT")
    finally:
        conn.close()
    return Persona(u["id"], u["usuario"])


def dar(persona: Persona, obra_id: str, *funciones: str) -> None:
    """Membresía directa en la base (como haría el alta inicial local)."""
    conn = database.get_connection()
    try:
        conn.execute("""INSERT INTO membresias (usuario_id, obra_id, funciones, version, creada, actualizada)
                        VALUES (?, ?, ?, 1, 'x', 'x')
                        ON CONFLICT(usuario_id, obra_id) DO UPDATE SET funciones = excluded.funciones""",
                     (persona.id, obra_id, json.dumps(sorted(funciones))))
        conn.commit()
    finally:
        conn.close()


@contextmanager
def cliente(app, persona: Persona = None, contrasena: str = CONTRASENA, cabeceras: dict = None):
    """TestClient con el Origin y el encabezado propio; si se da una persona, entra con su sesión."""
    with TestClient(app, headers=CABECERAS if cabeceras is None else cabeceras) as c:
        if persona is not None:
            r = c.post("/api/sesion", json={"usuario": persona.usuario, "contrasena": contrasena})
            assert r.status_code == 200, r.text
        yield c


def pdf_bytes(texto: str = "HOJA DE PRUEBA", paginas: int = 1) -> bytes:
    doc = pymupdf.open()
    for i in range(paginas):
        doc.new_page().insert_text((72, 72), f"{texto} {i + 1}")
    datos = doc.tobytes()
    doc.close()
    return datos


def subir_planos(c, obra_id: str, sufijo: str = "a"):
    return c.post(f"/api/proyectos/{obra_id}/planos",
                  files={"vectorial": (f"vectorial-{sufijo}.pdf", pdf_bytes(f"V{sufijo}"), "application/pdf"),
                         "sellado": (f"sellado-{sufijo}.pdf", pdf_bytes(f"S{sufijo}"), "application/pdf")},
                  data={"certifico": "true"})


def filas(sql: str, params=()) -> list:
    conn = database.get_connection()
    try:
        return [dict(f) for f in conn.execute(sql, params)]
    finally:
        conn.close()
