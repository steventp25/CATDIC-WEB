# BACKEND/tests/test_mesa_dudas.py
# Etapa 3 · T4 — API de la Mesa de Dudas (PLANES/etapa-3.md, T4; CLAUDE.md Regla de Oro #1, §1.5).
# Reutiliza el Dropbox falso de test_sync_endpoint.py (nombres REALES de Terra Living, contenido
# falso). Las respuestas de Steven que se prueban son SINTÉTICAS: no son datos de proyecto.
import json

import pytest

from test_sync_endpoint import _bd, _dudas, _sync, _visitas, entorno  # noqa: F401 (fixture)

CARPETA_FONDO = "1. FONDO DE SEPTICO"                                      # REAL: sin fecha ni clase
CARPETA_18 = "18. LOSA Y VIGA ENTREPISO S-4 COMPLETIVO 02-10-2026"          # REAL: duda `estado`
CARPETA_19 = "19. VERTICALES S-3 COMPLETIVO 09-10-2026"                     # REAL: sin PDF
CARPETA_8 = "8 - COLUMNAS S-6 COMPLETIVO"                                   # REAL: hallazgo de clase
STP_18 = "Terra Living - STP - Losa y Vigas Entrepiso 4 Sotano S4 - 02-10-2026 v2.pdf"  # REAL


def _duda(conn, carpeta, campo, categoria="DUDA_BLOQUEANTE"):
    v = _visitas(conn)[carpeta]
    return next(d for d in _dudas(conn)
                if d["visita_id"] == v["id"] and d["campo_afectado"] == campo
                and d["categoria"] == categoria)


def _n_auditoria(conn):
    return conn.execute(
        "SELECT COUNT(*) FROM auditoria WHERE modulo='MESA_DUDAS' AND accion='RESPONDER_DUDA'"
    ).fetchone()[0]


def _foto_bd(conn):
    return ([dict(f) for f in conn.execute("SELECT * FROM visitas ORDER BY id")],
            [dict(f) for f in conn.execute("SELECT * FROM dudas_y_hallazgos ORDER BY id")],
            conn.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0])


def _patch(cliente, duda_id, respuesta, **extra):
    return cliente.patch(f"/api/dudas/{duda_id}", json={"respuesta": respuesta, **extra})


@pytest.fixture
def con_sync(entorno):
    cliente, terra, raiz = entorno
    _sync(cliente)
    return cliente, terra


# ---------- GET ----------

def test_listar_con_filtros(con_sync):
    cliente, _ = con_sync
    todas = cliente.get("/api/dudas").json()
    assert len(todas) > 10
    with _bd() as conn:
        v19 = _visitas(conn)[CARPETA_19]
    r = cliente.get("/api/dudas", params={"visita_id": v19["id"]}).json()
    assert len(r) == 1
    d = r[0]
    assert d["campo_afectado"] == "archivos_json" and d["categoria"] == "DUDA_BLOQUEANTE"
    assert d["visita_numero"] == 19 and d["visita_carpeta"] == CARPETA_19
    assert d["resuelta"] == 0 and d["respuesta"] == "" and d["creado"] and "pregunta" in d
    assert all(x["categoria"] == "HALLAZGO_INTERNO"
               for x in cliente.get("/api/dudas", params={"categoria": "HALLAZGO_INTERNO"}).json())
    assert cliente.get("/api/dudas", params={"resuelta": "true"}).json() == []
    assert len(cliente.get("/api/dudas", params={"resuelta": "false"}).json()) == len(todas)
    assert len(cliente.get("/api/dudas", params={"proyecto_id": "terra-living"}).json()) == len(todas)
    assert cliente.get("/api/dudas", params={"proyecto_id": "no-existe"}).json() == []


# ---------- fecha ----------

def test_fecha_valida_se_aplica_audita_y_quita_el_pendiente(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        duda = _duda(conn, CARPETA_FONDO, "fecha_visita")
        antes = _visitas(conn)[CARPETA_FONDO]
        n_aud = _n_auditoria(conn)
    assert json.loads(antes["campos_pendientes_json"]) == ["fecha_visita", "clase"]
    r = _patch(cliente, duda["id"], "05/03/2026")  # SINTÉTICO
    assert r.status_code == 200, r.text
    assert r.json()["valor_aplicado"] == "2026-03-05"
    with _bd() as conn:
        v = _visitas(conn)[CARPETA_FONDO]
        d = _duda(conn, CARPETA_FONDO, "fecha_visita")
        aud = conn.execute("""SELECT * FROM auditoria WHERE modulo='MESA_DUDAS'
                              ORDER BY id DESC LIMIT 1""").fetchone()
        assert _n_auditoria(conn) == n_aud + 1
    assert v["fecha_visita"] == "2026-03-05"
    assert json.loads(v["campos_pendientes_json"]) == ["clase"]
    assert json.loads(v["origen_datos_json"])["fecha"] == "mesa_dudas"
    assert v["estado"] == "Con dudas"  # la clase sigue abierta
    assert d["resuelta"] == 1 and d["respuesta_usuario"] == "05/03/2026" and d["resuelto_en"]
    detalle = json.loads(aud["detalle_json"])
    assert detalle["valor_anterior"] == "pendiente de verificar" and detalle["valor_nuevo"] == "2026-03-05"
    assert aud["entidad_id"] == str(duda["id"])


@pytest.mark.parametrize("respuesta", ["5/3/2026", "31/02/2026", "2026-03-05", "05-03-2026", "", "hoy"])
def test_fecha_invalida_422_y_no_cambia_nada(con_sync, respuesta):
    cliente, _ = con_sync
    with _bd() as conn:
        duda = _duda(conn, CARPETA_FONDO, "fecha_visita")
        antes = _foto_bd(conn)
    r = _patch(cliente, duda["id"], respuesta)
    assert r.status_code == 422
    with _bd() as conn:
        assert _foto_bd(conn) == antes


# ---------- clase ----------

def test_clase_aplicada(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        duda = _duda(conn, CARPETA_FONDO, "clase")
    r = _patch(cliente, duda["id"], "completivo")
    assert r.status_code == 200 and r.json()["valor_aplicado"] == "Completivo"
    with _bd() as conn:
        v = _visitas(conn)[CARPETA_FONDO]
    assert v["clase"] == "Completivo"
    assert json.loads(v["campos_pendientes_json"]) == ["fecha_visita"]


def test_clase_invalida_422(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        duda = _duda(conn, CARPETA_FONDO, "clase")
        antes = _foto_bd(conn)
    for malo in ("Parciales", "Final", "Mixta", "mixta", ""):
        assert _patch(cliente, duda["id"], malo).status_code == 422
    with _bd() as conn:
        assert _foto_bd(conn) == antes


# ---------- última duda ----------

def test_ultima_duda_deja_la_visita_en_sin_procesar_nunca_procesada(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        d_fecha = _duda(conn, CARPETA_FONDO, "fecha_visita")
        d_clase = _duda(conn, CARPETA_FONDO, "clase")
    assert _patch(cliente, d_fecha["id"], "05/03/2026").json()["estado_visita"] == "Con dudas"
    r = _patch(cliente, d_clase["id"], "Parcial")
    assert r.json()["estado_visita"] == "Sin procesar"
    with _bd() as conn:
        v = _visitas(conn)[CARPETA_FONDO]
    assert v["estado"] == "Sin procesar" and json.loads(v["salida_json"]) == {}


# ---------- estado (P3) ----------

def test_estado_corresponde_pasa_a_procesada_citando_el_stp(con_sync):
    cliente, terra = con_sync
    with _bd() as conn:
        duda = _duda(conn, CARPETA_18, "estado")
    r = _patch(cliente, duda["id"], "Corresponde")
    assert r.status_code == 200, r.text
    with _bd() as conn:
        v = _visitas(conn)[CARPETA_18]
    assert v["estado"] == "Procesada"
    stp = json.loads(v["salida_json"])["stp"]
    assert [p.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for p in stp] == [STP_18]
    assert json.loads(v["origen_datos_json"])["estado"] == "mesa_dudas"


def test_estado_no_corresponde_pasa_a_sin_procesar(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        duda = _duda(conn, CARPETA_18, "estado")
    r = _patch(cliente, duda["id"], "no corresponde")
    assert r.status_code == 200
    with _bd() as conn:
        v = _visitas(conn)[CARPETA_18]
    assert v["estado"] == "Sin procesar" and json.loads(v["salida_json"]) == {}


def test_estado_respuesta_invalida_422(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        duda = _duda(conn, CARPETA_18, "estado")
        antes = _foto_bd(conn)
    assert _patch(cliente, duda["id"], "sí").status_code == 422
    assert _patch(cliente, duda["id"], "corresponde", stp=["otro.pdf"]).status_code == 422
    with _bd() as conn:
        assert _foto_bd(conn) == antes


# ---------- archivos_json, hallazgos, elementos ----------

def test_archivos_json_422_sin_cambios(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        duda = _duda(conn, CARPETA_19, "archivos_json")
        antes = _foto_bd(conn)
    r = _patch(cliente, duda["id"], "ya lo subí")
    assert r.status_code == 422 and "sincronizar" in r.json()["detail"]
    with _bd() as conn:
        assert _foto_bd(conn) == antes


def test_hallazgo_se_marca_revisado_sin_aplicar_valor(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        h = _duda(conn, CARPETA_8, "clase", "HALLAZGO_INTERNO")
        antes = _visitas(conn)[CARPETA_8]
    r = _patch(cliente, h["id"], "revisado")
    assert r.status_code == 200
    with _bd() as conn:
        despues = _visitas(conn)[CARPETA_8]
        assert _duda(conn, CARPETA_8, "clase", "HALLAZGO_INTERNO")["resuelta"] == 1
    assert despues["clase"] == antes["clase"] == "Completivo"
    assert despues["estado"] == antes["estado"]


def test_hallazgo_revisado_con_bloqueante_abierta_no_congela_el_campo(con_sync):
    """T4b (a): ya no hace falta el 409; el sync solo cuenta bloqueantes resueltas."""
    cliente, _ = con_sync
    with _bd() as conn:
        v = _visitas(conn)[CARPETA_FONDO]
        conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria,
                        campo_afectado, descripcion_pregunta, creado)
                        VALUES ('terra-living', ?, '', 'HALLAZGO_INTERNO', 'clase', 'SINTÉTICO', 'x')""",
                     (v["id"],))
        h = _duda(conn, CARPETA_FONDO, "clase", "HALLAZGO_INTERNO")
    assert _patch(cliente, h["id"], "revisado").status_code == 200
    _sync(cliente)
    with _bd() as conn:
        v2 = _visitas(conn)[CARPETA_FONDO]
        assert _duda(conn, CARPETA_FONDO, "clase")["resuelta"] == 0  # la bloqueante sigue abierta
    assert "clase" in json.loads(v2["campos_pendientes_json"])
    assert v2["clase"] == "pendiente de verificar" and v2["estado"] == "Con dudas"


def test_duda_de_elemento_solo_guarda_la_respuesta(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        v = _visitas(conn)[CARPETA_8]
        cur = conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria,
                              campo_afectado, descripcion_pregunta, creado)
                              VALUES ('terra-living', ?, 'C1', 'DUDA_BLOQUEANTE', 'ejes', 'SINTÉTICO', 'x')""",
                           (v["id"],))
        duda_id = cur.lastrowid
        antes = _visitas(conn)[CARPETA_8]
    assert _patch(cliente, duda_id, "EJE A-1").status_code == 200  # SINTÉTICO
    with _bd() as conn:
        despues = _visitas(conn)[CARPETA_8]
        fila = conn.execute("SELECT * FROM dudas_y_hallazgos WHERE id=?", (duda_id,)).fetchone()
    assert fila["resuelta"] == 1 and fila["respuesta_usuario"] == "EJE A-1"
    assert {k: despues[k] for k in despues if k != "actualizado"} == \
        {k: antes[k] for k in antes if k != "actualizado"}


# ---------- 404 / 409 ----------

def test_id_inexistente_404(con_sync):
    cliente, _ = con_sync
    assert _patch(cliente, 999999, "05/03/2026").status_code == 404


def test_duda_ya_resuelta_409_y_no_cambia(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        duda = _duda(conn, CARPETA_FONDO, "fecha_visita")
    assert _patch(cliente, duda["id"], "05/03/2026").status_code == 200
    with _bd() as conn:
        antes = _foto_bd(conn)
    assert _patch(cliente, duda["id"], "06/03/2026").status_code == 409
    with _bd() as conn:
        assert _foto_bd(conn) == antes


# ---------- el sincronizador no revierte nada ----------

def test_sync_posterior_no_recrea_la_duda_ni_pisa_el_valor(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        d_fecha = _duda(conn, CARPETA_FONDO, "fecha_visita")
        d_clase = _duda(conn, CARPETA_FONDO, "clase")
        d_estado = _duda(conn, CARPETA_18, "estado")
    assert _patch(cliente, d_fecha["id"], "05/03/2026").status_code == 200
    assert _patch(cliente, d_clase["id"], "Parcial").status_code == 200
    assert _patch(cliente, d_estado["id"], "corresponde").status_code == 200
    with _bd() as conn:
        antes_v = {k: {c: x for c, x in v.items() if c != "actualizado"} for k, v in _visitas(conn).items()}
        antes_d = _dudas(conn)
    _sync(cliente)
    _sync(cliente)
    with _bd() as conn:
        despues_v = {k: {c: x for c, x in v.items() if c != "actualizado"} for k, v in _visitas(conn).items()}
        assert _dudas(conn) == antes_d  # misma cantidad, ninguna reabierta
    assert despues_v[CARPETA_FONDO] == antes_v[CARPETA_FONDO]
    assert despues_v[CARPETA_FONDO]["fecha_visita"] == "2026-03-05"
    assert despues_v[CARPETA_FONDO]["clase"] == "Parcial"
    assert despues_v[CARPETA_FONDO]["estado"] == "Sin procesar"
    assert despues_v[CARPETA_18] == antes_v[CARPETA_18]
    assert despues_v[CARPETA_18]["estado"] == "Procesada"


# ---------- BD intacta si falla a mitad ----------

def test_error_a_mitad_revierte_todo(con_sync, monkeypatch):
    cliente, _ = con_sync
    import mesa_dudas

    with _bd() as conn:
        duda = _duda(conn, CARPETA_FONDO, "fecha_visita")
        antes = _foto_bd(conn)

    original = mesa_dudas._json

    def falla(valor):  # falla al armar la auditoría, cuando la duda y la visita ya se actualizaron
        if isinstance(valor, dict) and "duda_id" in valor:
            raise RuntimeError("fallo simulado")
        return original(valor)
    with monkeypatch.context() as m:
        m.setattr(mesa_dudas, "_json", falla)
        with pytest.raises(RuntimeError):
            mesa_dudas.responder_duda(duda["id"], "05/03/2026")
    with _bd() as conn:
        assert _foto_bd(conn) == antes


# ---------- T4b ----------

def test_t4b_c_estado_diferido_se_aplica_al_cerrar_la_ultima_bloqueante(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        v = _visitas(conn)[CARPETA_18]
        cur = conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria,
                              campo_afectado, descripcion_pregunta, creado)
                              VALUES ('terra-living', ?, 'C1', 'DUDA_BLOQUEANTE', 'ejes', 'SINTÉTICO', 'x')""",
                           (v["id"],))
        d_elemento = cur.lastrowid
        d_estado = _duda(conn, CARPETA_18, "estado")
    r = _patch(cliente, d_estado["id"], "corresponde")
    assert r.status_code == 200 and r.json()["estado_visita"] == "Con dudas"  # queda otra abierta
    with _bd() as conn:
        v1 = _visitas(conn)[CARPETA_18]
    assert v1["estado"] == "Con dudas" and json.loads(v1["salida_json"]) == {}
    assert json.loads(v1["origen_datos_json"])["estado_mesa"]["estado"] == "Procesada"
    r = _patch(cliente, d_elemento, "EJE A-1")  # SINTÉTICO: cierra la última
    assert r.json()["estado_visita"] == "Procesada"
    with _bd() as conn:
        v2 = _visitas(conn)[CARPETA_18]
    assert v2["estado"] == "Procesada"
    assert [p.replace("\\", "/").rsplit("/", 1)[-1] for p in json.loads(v2["salida_json"])["stp"]] == [STP_18]
    assert json.loads(v2["origen_datos_json"])["estado"] == "mesa_dudas"


def test_t4b_d_corresponde_con_el_stp_borrado_422_sin_cambios(con_sync):
    cliente, terra = con_sync
    from sync.escaner_dropbox import SUBRUTA_INFORMES_PROCESADOS
    (terra / SUBRUTA_INFORMES_PROCESADOS / STP_18).unlink()
    with _bd() as conn:
        duda = _duda(conn, CARPETA_18, "estado")
        antes = _foto_bd(conn)
    r = _patch(cliente, duda["id"], "corresponde")
    assert r.status_code == 422 and STP_18 in r.json()["detail"]
    with _bd() as conn:
        assert _foto_bd(conn) == antes
    # "no corresponde" no necesita el archivo
    assert _patch(cliente, duda["id"], "no corresponde").status_code == 200


def test_t4b_e_mixta_no_se_acepta_en_la_mesa(con_sync):
    cliente, _ = con_sync
    with _bd() as conn:
        duda = _duda(conn, CARPETA_FONDO, "clase")
        antes = _foto_bd(conn)
    r = _patch(cliente, duda["id"], "Mixta")
    assert r.status_code == 422 and "Mixta" not in r.json()["detail"].split(":")[-1]
    with _bd() as conn:
        assert _foto_bd(conn) == antes
    assert _patch(cliente, duda["id"], "Parcial").status_code == 200
