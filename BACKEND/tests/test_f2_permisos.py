# Fundación F2 · permisos por obra y acción, con la guardia real (contrato §4; escenarios 1, 2, 3 y 15 del §7).
import re
import sqlite3

import pytest
from fastapi.testclient import TestClient

import database
import main
from f2_ayudas import CABECERAS, cliente, crear_persona, dar, filas, preparar_entorno, subir_planos
from identidad import guardia, permisos

pytestmark = pytest.mark.seguridad_real

OBRA_X = "terra-living"        # obras sembradas (ficticias en la base temporal)
OBRA_Y = "torre-p16"


def _rutas_api():
    """(método, plantilla) de toda ruta /api, sacadas del esquema de la aplicación."""
    rutas = []
    for plantilla, metodos in main.app.openapi()["paths"].items():
        if plantilla.startswith("/api"):
            rutas += [(m.upper(), plantilla) for m in metodos]
    return sorted(rutas)


def _url(plantilla: str, obra: str = OBRA_X) -> str:
    valores = {"proyecto_id": obra, "obra_id": obra, "pagina": "1", "uid": "u-1", "tabla_id": "1", "visita_id": "v-1",
               "duda_id": "1", "trabajo_id": "t-1", "pedido_id": "1", "usuario_id": "999"}
    return re.sub(r"\{(\w+)\}", lambda m: valores[m.group(1)], plantilla)


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    preparar_entorno(tmp_path, monkeypatch)
    personas = {
        "a": crear_persona("persona-a"),
        "b": crear_persona("persona-b"),
        "admin": crear_persona("admin-global", es_admin=True),
        "gestor": crear_persona("gestor-obra"),
        "steven": crear_persona("steven-prueba", es_admin=True),
    }
    dar(personas["a"], OBRA_X, "consultar")
    dar(personas["b"], OBRA_Y, "preparar", "revisar_autorizar")
    dar(personas["gestor"], OBRA_X, "administrar_obra")
    dar(personas["steven"], OBRA_X, "preparar", "revisar_autorizar")
    return personas


def test_toda_ruta_api_tiene_politica():
    """Una ruta nueva sin política se rechazaría (403): aquí se exige que todas estén en la tabla."""
    faltan = [r for r in _rutas_api() if r not in guardia.POLITICAS]
    sobran = [k for k in guardia.POLITICAS if k not in _rutas_api()]
    assert faltan == [] and sobran == []


def test_sin_sesion_toda_ruta_responde_401(entorno):
    with cliente(main.app) as c:
        for metodo, plantilla in _rutas_api():
            if (metodo, plantilla) == ("POST", "/api/sesion"):
                continue
            r = c.request(metodo, _url(plantilla))
            assert r.status_code == 401, (metodo, plantilla, r.status_code)


def test_sesion_falsa_o_cerrada_responde_401(entorno):
    with cliente(main.app) as c:
        c.cookies.set("catdic_sesion", "token-inventado")
        assert c.get("/api/dashboard").status_code == 401


def test_obra_ajena_responde_404_en_toda_ruta_de_esa_obra(entorno):
    """Escenario 1: B conoce el id de X y no la ve en la API, en la búsqueda, en el visor ni en los archivos."""
    with cliente(main.app, entorno["steven"]) as s:
        assert subir_planos(s, OBRA_X).status_code == 201
    probadas = 0
    with cliente(main.app, entorno["b"]) as c:
        for metodo, plantilla in _rutas_api():
            if "{proyecto_id}" not in plantilla and "{obra_id}" not in plantilla:
                continue
            if plantilla == "/api/proyectos/{proyecto_id}" and metodo != "PATCH":
                continue
            r = c.request(metodo, _url(plantilla, OBRA_X))
            assert r.status_code == 404, (metodo, plantilla, r.status_code, r.text)
            probadas += 1
        # Con su propia obra, la misma ruta sí entra (no es un 404 general)
        assert c.get(f"/api/proyectos/{OBRA_Y}/planos").status_code == 200
        # Listados: ni nombres ni datos de la obra ajena
        assert OBRA_X not in c.get("/api/dashboard").text
        assert [o["id"] for o in c.get("/api/obras").json()["obras"]] == [OBRA_Y]
        assert all(d["proyecto_id"] != OBRA_X for d in c.get("/api/dudas").json())
        assert c.get("/api/dudas", params={"proyecto_id": OBRA_X}).status_code == 404
        # El archivo de la hoja (PNG) de la obra ajena tampoco
        assert c.get(f"/api/proyectos/{OBRA_X}/visor/hojas/1.png").status_code == 404
        # Una obra que no existe responde igual que la ajena
        assert c.get("/api/obras/no-existe").status_code == 404
    assert probadas >= 20
    with cliente(main.app, entorno["a"]) as c:   # A, que sí es de la obra, ve la hoja
        r = c.get(f"/api/proyectos/{OBRA_X}/visor/hojas/1.png")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
        assert OBRA_Y not in c.get("/api/dashboard").text


def test_recursos_de_obra_ajena_por_id_responden_404(entorno):
    """Duda, visita, trabajo y pedido de otra obra, pedidos por su id directo."""
    conn = database.get_connection()
    try:
        conn.execute("""INSERT INTO visitas (id, proyecto_id, numero, nombre_carpeta, ruta_carpeta, fecha_visita, clase,
                        estado, formatos_solicitados, actualizado) VALUES ('v-x', ?, 1, 'VISITA FICTICIA', 'r', '2026-01-02',
                        'Parcial', 'Sin procesar', '[]', 'x')""", (OBRA_X,))
        duda = conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria,
                               campo_afectado, descripcion_pregunta, creado) VALUES (?, 'v-x', 'C1', 'DUDA_BLOQUEANTE',
                               'EJES', '¿Pregunta ficticia?', 'x')""", (OBRA_X,)).lastrowid
        conn.execute("""INSERT INTO trabajos (id, tipo, visitas_json, estado, usuario, creado)
                        VALUES ('t-x', 'visita', '["v-x"]', 'terminado', 'x', 'x')""")
        conn.commit()
    finally:
        conn.close()
    with cliente(main.app, entorno["steven"]) as s:
        pedido = s.post(f"/api/obras/{OBRA_X}/pedidos", json={"proposito": "Pedido ficticio"}).json()["pedido"]
    with cliente(main.app, entorno["b"]) as c:
        assert c.patch(f"/api/dudas/{duda}", json={"respuesta": "x"}).status_code == 404
        assert c.post("/api/visitas/v-x/procesar").status_code == 404
        assert c.get("/api/trabajos/t-x").status_code == 404
        assert c.get("/api/trabajos/t-x/eventos").status_code == 404
        assert c.get(f"/api/pedidos/{pedido['id']}").status_code == 404
        assert c.patch(f"/api/pedidos/{pedido['id']}", json={"version": 1, "proposito": "x"}).status_code == 404
        assert c.put(f"/api/pedidos/{pedido['id']}/fuentes", json={"version": 1, "fuentes": []}).status_code == 404
        assert c.get("/api/dudas", params={"visita_id": "v-x"}).status_code == 404
        # Procesar la cola o sincronizar «todo» no toca la obra ajena
        r = c.post("/api/visitas/procesar-cola")
        assert r.status_code == 202 and r.json()["trabajo"] is None
    with cliente(main.app, entorno["a"]) as c:
        assert c.get("/api/trabajos/t-x").status_code == 200
        assert c.get(f"/api/pedidos/{pedido['id']}").status_code == 200


def test_revocacion_la_siguiente_peticion_da_404(entorno):
    """Escenario 2: el gestor (administrar_obra) le quita la membresía a A; su próxima petición recibe 404."""
    with cliente(main.app, entorno["a"]) as a, cliente(main.app, entorno["gestor"]) as g:
        assert a.get(f"/api/obras/{OBRA_X}").status_code == 200
        membresias = g.get(f"/api/obras/{OBRA_X}/membresias").json()["membresias"]
        m = next(x for x in membresias if x["usuario_id"] == entorno["a"].id)
        r = g.put(f"/api/obras/{OBRA_X}/membresias/{entorno['a'].id}", json={"funciones": [], "version": m["version"]})
        assert r.status_code == 200, r.text
        assert a.get(f"/api/obras/{OBRA_X}").status_code == 404
        assert a.get(f"/api/proyectos/{OBRA_X}/planos").status_code == 404
        assert OBRA_X not in a.get("/api/dashboard").text
    acciones = [f["accion"] for f in filas("SELECT accion FROM auditoria WHERE modulo = 'MEMBRESIAS'")]
    assert acciones == ["REVOCAR"]


def test_membresia_con_version_vieja_da_409_y_no_se_cambia_a_si_mismo(entorno):
    with cliente(main.app, entorno["gestor"]) as g:
        url = f"/api/obras/{OBRA_X}/membresias/{entorno['a'].id}"
        assert g.put(url, json={"funciones": ["consultar", "preparar"], "version": 1}).status_code == 200
        assert g.put(url, json={"funciones": ["consultar"], "version": 1}).status_code == 409
        # administrar_obra no puede darse a sí mismo revisar_autorizar
        r = g.put(f"/api/obras/{OBRA_X}/membresias/{entorno['gestor'].id}",
                  json={"funciones": ["administrar_obra", "revisar_autorizar"], "version": 1})
        assert r.status_code == 403
    assert permisos.componer(["administrar_obra"]) == {"administrar_obra", "consultar"}


def test_confirmar_sin_funcion_tecnica(entorno, tmp_path):
    """Escenario 15 (rev. 3): solo administrar_obra -> 403; es_admin sin membresía -> 404; no cambia nada."""
    antes = (filas("SELECT COUNT(*) AS n FROM planos")[0]["n"],
             filas("SELECT COUNT(*) AS n FROM auditoria WHERE modulo NOT IN ('SESION', 'SISTEMA')")[0]["n"])
    with cliente(main.app, entorno["gestor"]) as g:
        assert subir_planos(g, OBRA_X).status_code == 403                       # confirmar una revisión de plano
        assert g.post(f"/api/proyectos/{OBRA_X}/tablas-extraidas/1/confirmar", json={}).status_code == 403
        assert g.put(f"/api/proyectos/{OBRA_X}/datos-obra",
                     json={"tipo": "techo", "items": [{"clave": "1", "valor": "x"}]}).status_code == 403
    with cliente(main.app, entorno["admin"]) as ad:
        assert subir_planos(ad, OBRA_X).status_code == 404
        assert ad.post(f"/api/proyectos/{OBRA_X}/tablas-extraidas/1/confirmar", json={}).status_code == 404
        assert ad.get(f"/api/obras/{OBRA_X}").status_code == 404                # es_admin no ve datos técnicos
    despues = (filas("SELECT COUNT(*) AS n FROM planos")[0]["n"],
               filas("SELECT COUNT(*) AS n FROM auditoria WHERE modulo NOT IN ('SESION', 'SISTEMA')")[0]["n"])
    assert despues[0] == antes[0] and despues[1] == antes[1]


def test_funcion_administrar_se_rechaza(entorno):
    conn = database.get_connection()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="funcion de obra no permitida"):
            conn.execute("""INSERT INTO membresias (usuario_id, obra_id, funciones, creada, actualizada)
                            VALUES (?, ?, '["administrar"]', 'x', 'x')""", (entorno["b"].id, OBRA_X))
        with pytest.raises(sqlite3.IntegrityError, match="funcion de obra no permitida"):
            conn.execute("UPDATE membresias SET funciones = '[\"administrar\", \"consultar\"]' WHERE usuario_id = ?",
                         (entorno["a"].id,))
    finally:
        conn.close()
    # Si apareciera saltándose la base, no concede nada ni se traduce a otra
    assert permisos.componer(["administrar"]) == frozenset()
    with cliente(main.app, entorno["gestor"]) as g:
        r = g.put(f"/api/obras/{OBRA_X}/membresias/{entorno['b'].id}", json={"funciones": ["administrar"]})
        assert r.status_code == 422


def test_composicion_de_funciones(entorno):
    """preparar y revisar_autorizar no se incluyen entre sí; ambas incluyen consultar."""
    solo_preparar, solo_revisar = crear_persona("solo-preparar"), crear_persona("solo-revisar")
    dar(solo_preparar, OBRA_X, "preparar")
    dar(solo_revisar, OBRA_X, "revisar_autorizar")
    with cliente(main.app, solo_preparar) as p, cliente(main.app, solo_revisar) as r:
        for c in (p, r):
            assert c.get(f"/api/proyectos/{OBRA_X}/planos").status_code == 200
        assert subir_planos(p, OBRA_X).status_code == 403
        assert r.post(f"/api/obras/{OBRA_X}/pedidos", json={"proposito": "x"}).status_code == 403
        assert subir_planos(r, OBRA_X).status_code == 201
        assert p.post(f"/api/obras/{OBRA_X}/pedidos", json={"proposito": "x"}).status_code == 201


def test_crear_obra_solo_es_admin_y_el_creador_queda_registrado(entorno):
    with cliente(main.app, entorno["a"]) as a:
        assert a.post("/api/proyectos", json={"nombre": "Obra ficticia"}).status_code == 403
    with cliente(main.app, entorno["admin"]) as ad:
        r = ad.post("/api/proyectos", json={"nombre": "Obra ficticia"})
        assert r.status_code == 201, r.text
        obra = r.json()["proyecto"]["id"]
        assert sorted(ad.get(f"/api/obras/{obra}").json()["obra"]["funciones"]) == [
            "administrar_obra", "consultar", "preparar", "revisar_autorizar"]
        assert ad.get(f"/api/obras/{obra}").json()["obra"]["servicios"][0]["servicio"] == "Supervisión"
    auditoria = filas("SELECT usuario, usuario_id, accion FROM auditoria WHERE accion IN ('CREAR_PROYECTO', 'ASIGNAR')")
    assert [(f["accion"], f["usuario_id"]) for f in auditoria] == [("CREAR_PROYECTO", entorno["admin"].id),
                                                                  ("ASIGNAR", entorno["admin"].id)]


def test_mutacion_sin_encabezado_u_origin_responde_403(entorno):
    """Escenario 12: 403 si falta el encabezado propio o el Origin no es este servidor; no cambia nada."""
    with cliente(main.app, entorno["steven"]) as s:
        cookie = s.cookies.get("catdic_sesion")
    casos = [
        {"Origin": "http://testserver"},                                    # sin encabezado propio
        {"X-CATDIC-Peticion": "1"},                                         # sin Origin
        {"Origin": "http://otra-pagina.example", "X-CATDIC-Peticion": "1"},  # otro origen
        {"Origin": "null", "X-CATDIC-Peticion": "1"},                       # archivo local / iframe aislado
    ]
    for cabeceras in casos:
        with TestClient(main.app, headers=cabeceras) as c:
            c.cookies.set("catdic_sesion", cookie)
            r = c.post(f"/api/obras/{OBRA_X}/pedidos", json={"proposito": "no debe crearse"})
            assert r.status_code == 403, (cabeceras, r.status_code)
            assert c.post("/api/sesion", json={"usuario": "x", "contrasena": "y"}).status_code == 403
            assert c.get(f"/api/obras/{OBRA_X}").status_code == 200      # las lecturas no necesitan el encabezado
    assert filas("SELECT COUNT(*) AS n FROM pedidos")[0]["n"] == 0
    with TestClient(main.app, headers={**CABECERAS, "Host": "evil.example"}) as c:   # rebinding de DNS
        c.cookies.set("catdic_sesion", cookie)
        assert c.post(f"/api/obras/{OBRA_X}/pedidos", json={"proposito": "x"}).status_code == 403


def test_sin_cors_abierto(entorno):
    with cliente(main.app) as c:
        r = c.options("/api/dashboard", headers={"Origin": "http://otra-pagina.example",
                                                "Access-Control-Request-Method": "GET"})
        assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_visor_no_sirve_archivos_fuera_de_la_carpeta_de_la_obra(entorno, tmp_path):
    """H7: aunque la base apunte a otro archivo del disco, el visor solo lee dentro de <datos>/<obra>/."""
    import shutil
    with cliente(main.app, entorno["steven"]) as s:
        assert subir_planos(s, OBRA_X).status_code == 201
        assert s.get(f"/api/proyectos/{OBRA_X}/visor/hojas/1.png").status_code == 200
        original = filas("SELECT id, vectorial_ruta FROM planos WHERE proyecto_id = ?", (OBRA_X,))[0]
        for fuera in (tmp_path / "fuera.pdf", tmp_path / "datos" / OBRA_Y / "ajeno.pdf"):
            fuera.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(original["vectorial_ruta"], fuera)
            conn = database.get_connection()
            conn.execute("UPDATE planos SET vectorial_ruta = ? WHERE id = ?", (str(fuera), original["id"]))
            conn.commit()
            conn.close()
            r = s.get(f"/api/proyectos/{OBRA_X}/visor/hojas/2.png")
            assert r.status_code == 409 and "fuera de la carpeta" in r.text, fuera
