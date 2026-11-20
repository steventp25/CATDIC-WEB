# Fundación F2 · pedidos con control de versión (escenarios 3, 7 y 8 del §7, y la parada por fuente cambiada §2.3).
import json
import threading
from pathlib import Path

import pytest

import database
import main
from f2_ayudas import cliente, crear_persona, dar, filas, preparar_entorno, subir_planos

pytestmark = pytest.mark.seguridad_real

OBRA = "terra-living"


@pytest.fixture
def gente(tmp_path, monkeypatch):
    preparar_entorno(tmp_path, monkeypatch)
    g = {"prepara": crear_persona("solo-prepara"), "revisa": crear_persona("solo-revisa"),
         "ambas": crear_persona("prepara-y-revisa"), "mira": crear_persona("solo-consulta")}
    dar(g["prepara"], OBRA, "preparar")
    dar(g["revisa"], OBRA, "revisar_autorizar")
    dar(g["ambas"], OBRA, "preparar", "revisar_autorizar")
    dar(g["mira"], OBRA, "consultar")
    return g


def _plano(c) -> int:
    r = subir_planos(c, OBRA)
    assert r.status_code == 201, r.text
    return filas("SELECT id FROM planos ORDER BY id DESC LIMIT 1")[0]["id"]


def _paso(c, pedido, **cambios):
    return c.patch(f"/api/pedidos/{pedido['id']}", json={"version": pedido["version"], **cambios})


def test_preparar_y_autorizar_son_actos_separados_y_auditados(gente):
    """Escenario 3: la misma persona puede tener las dos funciones, pero cada paso es un acto con su función."""
    with cliente(main.app, gente["ambas"]) as a:
        plano = _plano(a)
    with cliente(main.app, gente["prepara"]) as p, cliente(main.app, gente["revisa"]) as r, \
            cliente(main.app, gente["mira"]) as m, cliente(main.app, gente["ambas"]) as a:
        pedido = p.post(f"/api/obras/{OBRA}/pedidos", json={"proposito": "Pedido ficticio de prueba"}).json()["pedido"]
        assert m.post(f"/api/obras/{OBRA}/pedidos", json={"proposito": "x"}).status_code == 403
        assert _paso(m, pedido, proposito="cambio").status_code == 403
        pedido = p.put(f"/api/pedidos/{pedido['id']}/fuentes",
                       json={"version": pedido["version"], "fuentes": [{"plano_id": plano}]}).json()["pedido"]
        assert _paso(r, pedido, estado="solicitado").status_code == 403       # revisar no incluye preparar
        for estado in ("solicitado", "preparado", "en_revision"):
            res = _paso(p, pedido, estado=estado)
            assert res.status_code == 200, res.text
            pedido = res.json()["pedido"]
        assert _paso(p, pedido, estado="aprobado").status_code == 403         # preparar no incluye autorizar
        pedido = _paso(r, pedido, estado="corregir").json()["pedido"]
        pedido = _paso(a, pedido, estado="en_revision").json()["pedido"]      # quien tiene ambas: acto de preparar
        res = _paso(a, pedido, estado="aprobado")                              # ...y aparte, acto de autorizar
        assert res.status_code == 200, res.text
        pedido = res.json()["pedido"]
        assert pedido["estado"] == "aprobado" and pedido["version"] == 8
        assert _paso(a, pedido, proposito="otro").status_code == 409          # aprobado no se edita
        assert _paso(a, pedido, estado="borrador").status_code == 409         # ni vuelve atrás
    actos = filas("SELECT usuario, usuario_id, accion, detalle_json FROM auditoria WHERE modulo = 'PEDIDOS' ORDER BY id")
    resumen = [(f["accion"], f["usuario"], json.loads(f["detalle_json"])["funcion"]) for f in actos if f["accion"] != "CREAR"]
    assert resumen == [
        ("FIJAR_FUENTES", "solo-prepara", "preparar"),
        ("SOLICITAR", "solo-prepara", "preparar"),
        ("PREPARAR", "solo-prepara", "preparar"),
        ("ENVIAR_A_REVISION", "solo-prepara", "preparar"),
        ("PEDIR_CORRECCION", "solo-revisa", "revisar_autorizar"),
        ("ENVIAR_A_REVISION", "prepara-y-revisa", "preparar"),
        ("APROBAR", "prepara-y-revisa", "revisar_autorizar"),
    ]
    assert all(f["usuario_id"] is not None for f in actos)


def _carrera(clientes, peticion):
    """Lanza la misma petición desde varios clientes a la vez (una barrera los suelta juntos)."""
    barrera, resultados = threading.Barrier(len(clientes)), [None] * len(clientes)

    def correr(i, c):
        barrera.wait()
        resultados[i] = peticion(c, i)

    hilos = [threading.Thread(target=correr, args=(i, c)) for i, c in enumerate(clientes)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(30)
    return resultados


@pytest.mark.parametrize("ronda", range(5))
def test_dos_ediciones_a_la_vez_una_gana_la_otra_recibe_409(gente, ronda):
    """Escenario 7: dos personas editan la misma versión al mismo tiempo; ninguna pisa a la otra."""
    with cliente(main.app, gente["prepara"]) as uno, cliente(main.app, gente["ambas"]) as dos:
        pedido = uno.post(f"/api/obras/{OBRA}/pedidos", json={"proposito": "Original"}).json()["pedido"]
        res = _carrera([uno, dos], lambda c, i: c.patch(f"/api/pedidos/{pedido['id']}",
                                                         json={"version": 1, "proposito": f"Cambio {i}"}))
        codigos = sorted(r.status_code for r in res)
        assert codigos == [200, 409], [r.text for r in res]
        ganador = next(r for r in res if r.status_code == 200).json()["pedido"]
        final = uno.get(f"/api/pedidos/{pedido['id']}").json()["pedido"]
        assert final["version"] == 2 and final["proposito"] == ganador["proposito"]
        # Con la versión vieja, el perdedor tampoco entra después
        assert uno.patch(f"/api/pedidos/{pedido['id']}", json={"version": 1, "proposito": "x"}).status_code == 409
    ediciones = filas("SELECT detalle_json FROM auditoria WHERE modulo = 'PEDIDOS' AND accion = 'EDITAR'")
    assert len(ediciones) == 1


def test_fijar_fuentes_a_la_vez_y_con_version_vieja(gente):
    with cliente(main.app, gente["ambas"]) as a, cliente(main.app, gente["prepara"]) as p:
        plano = _plano(a)
        pedido = a.post(f"/api/obras/{OBRA}/pedidos", json={"proposito": "Fuentes"}).json()["pedido"]
        res = _carrera([a, p], lambda c, i: c.put(f"/api/pedidos/{pedido['id']}/fuentes",
                                                  json={"version": 1, "fuentes": [{"plano_id": plano}] if i else []}))
        assert sorted(r.status_code for r in res) == [200, 409]
        # Una edición y una fijación de fuentes sobre la misma versión también chocan
        actual = a.get(f"/api/pedidos/{pedido['id']}").json()["pedido"]
        assert _paso(a, actual, proposito="Primero").status_code == 200
        r = a.put(f"/api/pedidos/{pedido['id']}/fuentes", json={"version": actual["version"], "fuentes": []})
        assert r.status_code == 409
        # Fuentes que no son de plano, o planos de otra obra, no se aceptan
        actual = a.get(f"/api/pedidos/{pedido['id']}").json()["pedido"]
        assert a.put(f"/api/pedidos/{pedido['id']}/fuentes",
                     json={"version": actual["version"], "fuentes": [{"documento_version_id": 1}]}).status_code == 422
        assert a.put(f"/api/pedidos/{pedido['id']}/fuentes",
                     json={"version": actual["version"], "fuentes": [{"plano_id": 99999}]}).status_code == 404
        assert a.get(f"/api/pedidos/{pedido['id']}").json()["pedido"]["version"] == actual["version"]
    assert len(filas("SELECT 1 FROM auditoria WHERE accion = 'FIJAR_FUENTES'")) == 1


def test_el_pedido_sobrevive_al_reinicio(gente):
    """Escenario 8: se reinicia el servidor a mitad del pedido; vuelve con su estado, versión y fuentes."""
    with cliente(main.app, gente["ambas"]) as a:
        plano = _plano(a)
        pedido = a.post(f"/api/obras/{OBRA}/pedidos", json={"proposito": "Antes del reinicio"}).json()["pedido"]
        pedido = a.put(f"/api/pedidos/{pedido['id']}/fuentes",
                       json={"version": 1, "fuentes": [{"plano_id": plano}]}).json()["pedido"]
        pedido = _paso(a, pedido, estado="solicitado", progreso={"paso": "elegir fuentes", "hechos": 1}).json()["pedido"]
    database.inicializar_bd()          # el arranque de nuevo (migraciones idempotentes) no toca el pedido
    with cliente(main.app, gente["ambas"]) as a:
        despues = a.get(f"/api/pedidos/{pedido['id']}").json()["pedido"]
        assert {k: despues[k] for k in ("estado", "version", "progreso", "proposito")} == \
            {"estado": "solicitado", "version": 3, "progreso": {"paso": "elegir fuentes", "hechos": 1},
             "proposito": "Antes del reinicio"}
        assert [f["plano_id"] for f in despues["fuentes"]] == [plano]
        assert _paso(a, despues, estado="preparado").status_code == 200   # y se continúa donde se dejó


def test_se_detiene_si_el_archivo_de_la_fuente_cambio(gente):
    with cliente(main.app, gente["ambas"]) as a:
        plano = _plano(a)
        pedido = a.post(f"/api/obras/{OBRA}/pedidos", json={"proposito": "Fuente que cambia"}).json()["pedido"]
        sin_fuentes = _paso(a, pedido, estado="solicitado").json()["pedido"]
        r = _paso(a, sin_fuentes, estado="preparado")
        assert r.status_code == 409 and "no tiene fuentes" in json.dumps(r.json(), ensure_ascii=False)
        pedido = a.put(f"/api/pedidos/{pedido['id']}/fuentes",
                       json={"version": sin_fuentes["version"], "fuentes": [{"plano_id": plano}]}).json()["pedido"]
        ruta = Path(filas("SELECT vectorial_ruta FROM planos WHERE id = ?", (plano,))[0]["vectorial_ruta"])
        ruta.write_bytes(ruta.read_bytes() + b"\n% cambio ficticio\n")
        r = _paso(a, pedido, estado="preparado")
        assert r.status_code == 409
        assert any("vectorial cambió" in m for m in r.json()["detail"]["motivos"])
        assert a.get(f"/api/pedidos/{pedido['id']}").json()["pedido"]["estado"] == "solicitado"
    detenidos = filas("SELECT usuario_id, detalle_json FROM auditoria WHERE accion = 'DETENIDO'")
    assert len(detenidos) == 2 and all(f["usuario_id"] == gente["ambas"].id for f in detenidos)
