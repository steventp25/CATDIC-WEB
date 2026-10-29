# BACKEND/tests/test_extractor.py
# Etapa 2 · T6n — Extractor desde el vectorial (PLANES/etapa-2.md, T6n).
# Todo # SINTÉTICO: los vectoriales se generan aquí con PyMuPDF; no se usa ningún plano ni dato real.
import hashlib
import json
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

import config
import database
import main
from importadores.validador_diseno import CONFIRMADO, PENDIENTE_ESTADO
from plano import extractor as ex
from plano import lector_plano as lp
from reglas_ingenieria import PENDIENTE

COLS_LOSA = {"TIPO DE": 0, "H": 45, "Bw1": 75, "Bw2": 115, "h1": 150, "h2": 185, "DIR. X": 230, "DIR. Y": 290, "AS. ADIC.": 350}
FILAS_LOSA = [("A", "0.25", "0.125", "0.156", "0.20", "0.05", '3Ø1/2"', '3Ø1/2"', '2Ø1/2"'),
              ("B", "0.25", "0.125", "0.156", "0.20", "0.05", '2Ø1/2"', '2Ø1/2"', '2Ø3/8"'),
              ("C", "0.25", "0.125", "0.156", "0.20", "0.05", '3Ø3/8"', '3Ø3/8"', '2Ø3/8"')]


def _t(pag, x, y, texto, tam=8.0, oc=0):
    pag.insert_text((x, y), texto, fontsize=tam, oc=oc)


def _hoja(doc, nn, titulo):
    pag = doc.new_page(width=1600, height=900)
    _t(pag, 1500, 870, nn, 14)
    _t(pag, 1516, 870, "/36", 14)
    if titulo:
        _t(pag, 100, 860, titulo, 15)
    return pag


def _tabla_losa(pag, filas=FILAS_LOSA, jitter=None, x0=1000, y0=200):
    jitter = jitter or {}
    _t(pag, x0, y0, "TABLA DE ACERO EN LOSA", 10)
    for c, dx in COLS_LOSA.items():
        _t(pag, x0 + dx, y0 + 30, c, 8)
    for i, fila in enumerate(filas):
        for j, (c, dx) in enumerate(COLS_LOSA.items()):
            if fila[j] is None:
                continue
            jx, jy = jitter.get((i, c), (0, 0))
            _t(pag, x0 + dx + jx, y0 + 50 + 17 * i + jy, fila[j], 8)


def _tabla_fc(pag, filas, x0=1200, y0=700):
    _t(pag, x0, y0, "CONCRETO F'c", 8)
    for i, (rango, valor) in enumerate(filas):
        _t(pag, x0 - 10, y0 + 20 + 11 * i, rango, 8)
        _t(pag, x0 + 50, y0 + 20 + 11 * i, valor, 8)


def _ids(pag, ids):
    for i, lid in enumerate(ids):
        _t(pag, 200 + 90 * i, 400, lid, 8)


def _vectorial(construir) -> bytes:
    doc = pymupdf.open()
    construir(doc)
    datos = doc.tobytes()
    doc.close()
    return datos


def _planta_basica(doc, ids=("L1", "L2"), titulo="PLANTA ESTRUCTURAL NIVEL 2", jitter=None,
                   fc=(("E1 @ E3", "350 Kg/cm2"), ("E4 @ E6", "280 Kg/cm2"))):
    pag = _hoja(doc, "20", titulo)
    _tabla_losa(pag, jitter=jitter)
    _ids(pag, ids)
    _tabla_fc(pag, fc)
    return pag


def _sellado() -> bytes:
    doc = pymupdf.open()
    doc.new_page(width=300, height=200)
    datos = doc.tobytes()
    doc.close()
    return datos


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    (tmp_path / "bd").mkdir()
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "bd" / "prueba.db"))
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "dropbox"))
    monkeypatch.setenv(config.ENV_DATOS_RAIZ, str(tmp_path / "datos"))
    monkeypatch.setenv(config.ENV_CACHE_RAIZ, str(tmp_path / "cache"))
    database.inicializar_bd()
    with TestClient(main.app) as c:
        yield c


def _obra(c, vectorial: bytes, datos=None) -> str:
    pid = c.post("/api/proyectos", json={"nombre": "Obra Extractor"}).json()["proyecto"]["id"]
    r = c.post(f"/api/proyectos/{pid}/planos", files={"vectorial": ("vec.pdf", vectorial, "application/pdf"),
                                                       "sellado": ("sel.pdf", _sellado(), "application/pdf")},
               data={"certifico": "true"})
    assert r.status_code == 201, r.text
    for tipo, items in (datos or {}).items():
        r = c.put(f"/api/proyectos/{pid}/datos-obra",
                  json={"tipo": tipo, "items": [{"clave": k, "valor": v} for k, v in items.items()], "completo": True})
        assert r.status_code == 200, r.text
    return pid


DATOS_COMPLETOS = {"equivalencia_nivel": {"E-2": "NIVEL 2"}, "losa_tipo": {"L1": "A", "L2": "C"}}


def _extraer(c, pid):
    r = c.post(f"/api/proyectos/{pid}/extraer-diseno")
    assert r.status_code == 200, r.text
    return r.json()


def _elementos(pid):
    conn = database.get_connection()
    try:
        return {(r["id_elemento"], r["nivel_rango"]): dict(r) for r in conn.execute(
            "SELECT * FROM elementos_diseno WHERE proyecto_id = ?", (pid,))}
    finally:
        conn.close()


def _dudas(pid):
    conn = database.get_connection()
    try:
        # solo las del extractor (prefijo T6n:); `campo` es el campo_afectado sin el prefijo
        return [{**dict(r), "campo": r["campo_afectado"].removeprefix("T6n:")} for r in conn.execute(
            "SELECT * FROM dudas_y_hallazgos WHERE proyecto_id = ? AND resuelta = 0 AND campo_afectado LIKE 'T6n:%'",
            (pid,))]
    finally:
        conn.close()


def _tabla(c, pid, clave):
    return next(t for t in c.get(f"/api/proyectos/{pid}/tablas-extraidas").json()["tablas"] if t["clave"] == clave)


# ---------- Propuesta completa: celdas desalineadas, fuente por valor y todo pendiente ----------

def test_celdas_desalineadas_se_leen_y_cada_valor_lleva_su_fuente_y_queda_pendiente(entorno):
    c = entorno
    desal = {(0, "H"): (3, 3), (0, "DIR. Y"): (-3, -3), (2, "h1"): (3, -3), (2, "AS. ADIC."): (-3, 3)}
    pid = _obra(c, _vectorial(lambda d: _planta_basica(d, jitter=desal)), DATOS_COMPLETOS)
    res = _extraer(c, pid)
    assert res["elementos"] == {"propuestos": 2, "nuevo": 2, "actualizado": 0, "sin_cambios": 0, "choque": 0}
    el = _elementos(pid)
    l1, l2 = el[("L1", "NIVEL 2")], el[("L2", "NIVEL 2")]
    assert l1["tipo_elemento"] == "LOSA" and l1["ejes"] == "—" and l1["hoja_plano_origen"] == "20"
    d1, d2 = json.loads(l1["datos_diseno_json"]), json.loads(l2["datos_diseno_json"])
    assert d1["tipo_losa"] == "A" and d1["H"] == "0.25" and d1["DIR. Y"] == '3Ø1/2"' and d1["AS. ADIC."] == '2Ø1/2"'
    assert d2["tipo_losa"] == "C" and d2["h1"] == "0.20" and d2["AS. ADIC."] == '2Ø3/8"'
    assert d1["fc_kgcm2"] == "350"  # E-2 (equivalencia del usuario) cae en 'E1 @ E3'
    # todos los campos pendientes, ninguno confirmado
    for fila in (l1, l2):
        estado = json.loads(fila["estado_campos_json"])
        assert estado and set(estado.values()) == {PENDIENTE_ESTADO}
        assert set(json.loads(fila["pendientes_json"])) == set(estado)
    # fuente: archivo, revisión, sha256, y por valor página, hoja y bbox
    f = json.loads(l1["fuente_json"])
    assert f["extractor"] == "T6n" and f["archivo"] == "vec.pdf" and f["revision"] == 1 and len(f["sha256"]) == 64
    h = f["valores"]["H"]
    assert h["pagina"] == 1 and h["hoja"] == "20" and h["columna"] == "H" and h["fila"] == "A" and len(h["bbox"]) == 4
    assert f["valores"]["tipo_losa"] == {"origen": "usuario", "dato": "losa_tipo", "clave": "L1"}
    assert f["valores"]["fc_kgcm2"]["tabla"] == "p1:fc_por_rango" and f["niveles_cubiertos"] == ["E-2"]
    # tablas en verde y sin dudas abiertas por el extractor
    assert _tabla(c, pid, "p1:acero_en_losa")["resultado"] == "verde"
    assert _tabla(c, pid, "p1:fc_por_rango")["resultado"] == "verde"
    assert sorted(_tabla(c, pid, "p1:acero_en_losa")["elementos"]) == sorted([l1["uid"], l2["uid"]])
    assert _dudas(pid) == []


def test_el_pdf_no_cambia_y_la_corrida_queda_auditada(entorno, tmp_path):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), DATOS_COMPLETOS)
    conn = database.get_connection()
    ruta = Path(conn.execute("SELECT vectorial_ruta FROM planos WHERE proyecto_id = ?", (pid,)).fetchone()[0])
    conn.close()
    antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
    res = _extraer(c, pid)
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == antes == res["sha256"] and res["sha256_sin_cambios"]
    conn = database.get_connection()
    aud = conn.execute("SELECT * FROM auditoria WHERE accion = 'EXTRAER_DISENO'").fetchall()
    conn.close()
    assert len(aud) == 1 and json.loads(aud[0]["detalle_json"])["elementos"]["nuevo"] == 2


# ---------- Capas ocultas ----------

def test_el_texto_de_una_capa_oculta_se_ignora(entorno):
    def construir(doc):
        pag = _planta_basica(doc)
        oculta = doc.add_ocg("OCULTA", on=False)
        _t(pag, 600, 400, "L9", 8, oc=oculta)                       # un ID de losa solo en la capa oculta
        _t(pag, 1000 + 45, 200 + 50 + 17 * 3, "9.99", 8, oc=oculta)  # una celda "de más" bajo la tabla
    c = entorno
    pid = _obra(c, _vectorial(construir), DATOS_COMPLETOS)
    res = _extraer(c, pid)
    assert res["capas_ocultas"] == 1
    assert {k[0] for k in _elementos(pid)} == {"L1", "L2"}
    t = _tabla(c, pid, "p1:acero_en_losa")
    assert t["resultado"] == "verde" and [f["etiqueta"]["valor"] for f in t["filas"]] == ["A", "B", "C"]


# ---------- Rangos E-n ----------

def test_rango_de_nivel_impreso_se_expande_y_toma_el_fc_de_su_rango(entorno):
    datos = {"equivalencia_nivel": {"E-4": "NIVEL 4", "E-5": "NIVEL 5", "E-6": "NIVEL 6"}, "losa_tipo": {"L1": "A", "L2": "B"}}
    c = entorno
    pid = _obra(c, _vectorial(lambda d: _planta_basica(d, titulo="PLANTA ESTRUCTURAL NIVEL 4@6")), datos)
    _extraer(c, pid)
    l1 = _elementos(pid)[("L1", "NIVEL 4@6")]  # nivel_rango tal como está impreso en la hoja
    f = json.loads(l1["fuente_json"])
    assert f["niveles_cubiertos"] == ["E-4", "E-5", "E-6"] and json.loads(l1["datos_diseno_json"])["fc_kgcm2"] == "280"
    fc = _tabla(c, pid, "p1:fc_por_rango")
    assert [r["expandido"] for r in fc["filas"]] == [["E-1", "E-2", "E-3"], ["E-4", "E-5", "E-6"]]


def test_el_borde_entre_dos_rangos_toma_el_fc_del_rango_que_empieza_en_el(entorno):
    # Regla de Steven: "E3 @ E10" = 350 y "E10 @ E16" = 280 → E-10 queda con 280; no es choque.
    c = entorno
    fc = (("E3 @ E10", "350 Kg/cm2"), ("E10 @ E16", "280 Kg/cm2"))
    datos = {"equivalencia_nivel": {"E-10": "NIVEL 2"}, "losa_tipo": {"L1": "A", "L2": "C"}}
    pid = _obra(c, _vectorial(lambda d: _planta_basica(d, fc=fc)), datos)
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:fc_por_rango")
    assert t["resultado"] == "verde"
    assert next(x for x in t["comprobaciones"] if x["comprobacion"] == "rangos_sin_choque")["ok"]
    assert t["filas"][0]["cede_a"] == {"E-10": "E10 @ E16"} and t["filas"][1]["cede_a"] == {}
    l1 = _elementos(pid)[("L1", "NIVEL 2")]
    assert json.loads(l1["datos_diseno_json"])["fc_kgcm2"] == "280"
    fuente = json.loads(l1["fuente_json"])["valores"]["fc_kgcm2"]
    assert fuente["fila"] == "E10 @ E16"
    assert fuente["borde_de_rango"]["E-10"]["fila_usada"] == "E10 @ E16"
    assert fuente["borde_de_rango"]["E-10"]["filas_que_ceden"] == ["E3 @ E10"]
    assert set(json.loads(l1["estado_campos_json"]).values()) == {PENDIENTE_ESTADO}  # sigue sin confirmar (T7n)
    assert not any("fc_por_rango" in d["campo"] for d in _dudas(pid))
    # un entrepiso interior de un rango no cambia: E-9 sigue en 350
    _, por_e = ex.comprobar_fc({"filas": t["filas"], "descartadas": []}, {})
    assert por_e["E-9"][0] == "350" and por_e["E-9"][2] is None and por_e["E-10"][0] == "280"


@pytest.mark.parametrize("fc,e_en_choque", [
    ((("E3 @ E10", "350 Kg/cm2"), ("E8 @ E12", "280 Kg/cm2")), "E-8"),   # solape real, más allá del borde
    ((("E3 @ E10", "350 Kg/cm2"), ("E3 @ E6", "280 Kg/cm2")), "E-3"),    # dos rangos que empiezan en el mismo E-n
])
def test_un_solape_real_con_fc_distinto_es_rojo_y_abre_duda(entorno, fc, e_en_choque):
    c = entorno
    datos = {"equivalencia_nivel": {e_en_choque: "NIVEL 2"}, "losa_tipo": {"L1": "A", "L2": "C"}}
    pid = _obra(c, _vectorial(lambda d: _planta_basica(d, fc=fc)), datos)
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:fc_por_rango")
    assert t["resultado"] == "rojo"
    choque = next(x for x in t["comprobaciones"] if x["comprobacion"] == "rangos_sin_choque")
    assert not choque["ok"] and any(d.startswith(f"{e_en_choque} ") for d in choque["detalle"])
    assert any(d["campo"] == "p1:fc_por_rango:rangos_sin_choque" for d in _dudas(pid))
    # la losa en ese E-n no recibe ninguno de los dos valores: queda pendiente
    assert json.loads(_elementos(pid)[("L1", "NIVEL 2")]["datos_diseno_json"])["fc_kgcm2"] == PENDIENTE


def test_rango_hasta_techo_no_se_expande_sin_la_equivalencia_del_usuario(entorno):
    c = entorno
    fc = (("E1 @ E3", "350 Kg/cm2"), ("E4 @ TECHO", "280 Kg/cm2"))
    pid = _obra(c, _vectorial(lambda d: _planta_basica(d, fc=fc)), DATOS_COMPLETOS)
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:fc_por_rango")
    assert t["resultado"] == "rojo" and t["filas"][1]["expandido"] is None
    assert any(d["campo"] == "p1:fc_por_rango:rangos_expandidos" for d in _dudas(pid))
    # con la equivalencia E-6 = TECHO el rango se cierra
    c.put(f"/api/proyectos/{pid}/datos-obra", json={"tipo": "equivalencia_nivel", "items": [{"clave": "E-6", "valor": "TECHO"}]})
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:fc_por_rango")
    assert t["resultado"] == "verde" and t["filas"][1]["expandido"] == ["E-4", "E-5", "E-6"]


def test_falta_la_equivalencia_del_nivel_el_fc_queda_pendiente_con_duda(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), {"losa_tipo": {"L1": "A", "L2": "C"}})
    _extraer(c, pid)
    assert json.loads(_elementos(pid)[("L1", "NIVEL 2")]["datos_diseno_json"])["fc_kgcm2"] == PENDIENTE
    assert any(d["campo"] == "equivalencia_nivel:NIVEL 2" for d in _dudas(pid))


# ---------- ID duplicado, tipo de losa y nivel ----------

def test_id_duplicado_en_el_mismo_nivel_abre_duda_y_la_tabla_queda_roja(entorno):
    c = entorno
    pid = _obra(c, _vectorial(lambda d: _planta_basica(d, ids=("L1", "L2", "L1"))), DATOS_COMPLETOS)
    res = _extraer(c, pid)
    assert res["elementos"]["propuestos"] == 2  # no se crean dos L1
    duda = next(d for d in _dudas(pid) if d["campo"] == "id_duplicado@NIVEL 2")
    assert duda["id_elemento"] == "L1" and duda["categoria"] == "DUDA_BLOQUEANTE"
    t = _tabla(c, pid, "p1:acero_en_losa")
    assert t["resultado"] == "rojo" and "ids_en_planta_sin_duplicados" in [x["comprobacion"] for x in t["comprobaciones"] if not x["ok"]]
    assert len(json.loads(_elementos(pid)[("L1", "NIVEL 2")]["fuente_json"])["bbox_id"]) == 2


def test_sin_el_tipo_de_la_losa_los_valores_quedan_pendientes_con_una_duda(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), {"equivalencia_nivel": {"E-2": "NIVEL 2"}, "losa_tipo": {"L1": "A"}})
    _extraer(c, pid)
    d2 = json.loads(_elementos(pid)[("L2", "NIVEL 2")]["datos_diseno_json"])
    assert d2["tipo_losa"] == PENDIENTE and d2["H"] == PENDIENTE and d2["DIR. X"] == PENDIENTE  # no se toma de otra fila
    dudas = [d for d in _dudas(pid) if d["id_elemento"] == "L2"]
    assert [d["campo"] for d in dudas] == ["losa_tipo"]  # una sola duda: la causa, no un campo por campo
    assert _tabla(c, pid, "p1:acero_en_losa")["resultado"] == "rojo"


def test_dos_plantas_con_el_mismo_titulo_quedan_sin_nivel_hasta_que_el_usuario_lo_diga(entorno):
    def construir(doc):
        for _ in range(2):
            pag = _hoja(doc, "31", "PLANTA ESTRUCTURAL DE TECHO")
            _tabla_losa(pag)
            _ids(pag, ["L1"])
    c = entorno
    pid = _obra(c, _vectorial(construir), {"losa_tipo": {"L1": "A"}})
    res = _extraer(c, pid)
    assert res["elementos"]["choque"] == 1  # L1 'pendiente' en las dos hojas: no se fusionan
    campos = {d["campo"] for d in _dudas(pid)}
    assert {"nivel_hoja:p1", "nivel_hoja:p2", f"clave_unica@{PENDIENTE}"} <= campos
    c.put(f"/api/proyectos/{pid}/datos-obra", json={"tipo": "techo", "items": [
        {"clave": "1", "valor": "TECHO"}, {"clave": "2", "valor": "TECHO ASCENSOR"}]})
    _extraer(c, pid)
    assert {("L1", "TECHO"), ("L1", "TECHO ASCENSOR")} <= set(_elementos(pid))


def test_al_dar_el_dato_y_reextraer_la_duda_del_extractor_se_cierra_con_auditoria(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), {"equivalencia_nivel": {"E-2": "NIVEL 2"}, "losa_tipo": {"L1": "A"}})
    _extraer(c, pid)
    duda = next(d for d in _dudas(pid) if d["id_elemento"] == "L2" and d["campo"] == "losa_tipo")
    assert duda["campo_afectado"] == "T6n:losa_tipo"
    conn = database.get_connection()
    obra_antes = [dict(r) for r in conn.execute(  # dudas de la obra de T4n (sin prefijo)
        "SELECT * FROM dudas_y_hallazgos WHERE proyecto_id = ? AND campo_afectado NOT LIKE 'T6n:%' ORDER BY id", (pid,))]
    conn.close()
    assert obra_antes and any(d["resuelta"] == 0 for d in obra_antes)
    # el usuario da L2 → C, pero sin marcar la entrega como completa: la duda de T4n debe seguir abierta
    c.put(f"/api/proyectos/{pid}/datos-obra", json={"tipo": "losa_tipo", "items": [{"clave": "L2", "valor": "C"}]})
    res = _extraer(c, pid)
    assert res["dudas_cerradas"] >= 1 and not any(d["id_elemento"] == "L2" for d in _dudas(pid))
    conn = database.get_connection()
    cerrada = dict(conn.execute("SELECT * FROM dudas_y_hallazgos WHERE id = ?", (duda["id"],)).fetchone())
    aud = conn.execute("SELECT * FROM auditoria WHERE accion = 'CERRAR_DUDAS_REEXTRACCION'").fetchall()
    obra_despues = [dict(r) for r in conn.execute(
        "SELECT * FROM dudas_y_hallazgos WHERE proyecto_id = ? AND campo_afectado NOT LIKE 'T6n:%' ORDER BY id", (pid,))]
    conn.close()
    assert cerrada["resuelta"] == 1 and cerrada["resuelto_en"] and "re-extracción" in cerrada["respuesta_usuario"]
    assert len(aud) == 1 and duda["id"] in json.loads(aud[0]["detalle_json"])["dudas_cerradas"] and aud[0]["usuario"]
    assert obra_despues == obra_antes  # las dudas de la obra (T4n) no se tocan
    assert _tabla(c, pid, "p1:acero_en_losa")["resultado"] == "verde"


# ---------- Comprobaciones de unidades y barras ----------

def test_una_dimension_en_cm_o_una_barra_ilegible_dejan_la_tabla_en_rojo(entorno):
    filas = [("A", "25", "0.125", "0.156", "0.20", "0.05", '3Ø1/2"', '3Ø1/2"', '2Ø1/2"'),
             ("B", "0.25", "0.125", "0.156", "0.20", "0.05", '2Ø9/7"', '2Ø1/2"', '2Ø3/8"'),
             ("C", "0.25", "0.125", "0.156", "0.21", "0.05", '3Ø3/8"', '3Ø3/8"', '2Ø3/8"')]

    def construir(doc):
        pag = _hoja(doc, "20", "PLANTA ESTRUCTURAL NIVEL 2")
        _tabla_losa(pag, filas=filas)
        _ids(pag, ["L1"])
    c = entorno
    pid = _obra(c, _vectorial(construir), DATOS_COMPLETOS)
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:acero_en_losa")
    fallos = {x["comprobacion"]: x["detalle"] for x in t["comprobaciones"] if not x["ok"]}
    assert set(fallos) == {"unidades", "total_de_barras", "espesor_total"}
    assert "A / H = '25'" in fallos["unidades"][0] and "9/7" in fallos["total_de_barras"][0]
    assert fallos["espesor_total"] == ["A: H 25 ≠ h1 0.20 + h2 0.05", "C: H 0.25 ≠ h1 0.21 + h2 0.05"]
    # el valor se propone tal cual (no se corrige a 0.25 m), pendiente, y la comprobación abre su duda
    assert json.loads(_elementos(pid)[("L1", "NIVEL 2")]["datos_diseno_json"])["H"] == "25"
    assert {"p1:acero_en_losa:unidades", "p1:acero_en_losa:total_de_barras"} <= {d["campo"] for d in _dudas(pid)}


# ---------- Idempotencia, campos confirmados y choques con el UNIQUE ----------

def test_extraer_dos_veces_no_duplica_ni_reabre_dudas(entorno):
    c = entorno
    pid = _obra(c, _vectorial(lambda d: _planta_basica(d, ids=("L1", "L2", "L1"))), DATOS_COMPLETOS)
    _extraer(c, pid)
    n_dudas = len(_dudas(pid))
    res = _extraer(c, pid)
    assert res["elementos"] == {"propuestos": 2, "nuevo": 0, "actualizado": 0, "sin_cambios": 2, "choque": 0}
    assert res["dudas_creadas"] == 0 and len(_dudas(pid)) == n_dudas and len(_elementos(pid)) == 2


def test_un_campo_confirmado_nunca_se_toca_al_volver_a_extraer(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), DATOS_COMPLETOS)
    _extraer(c, pid)
    l1 = _elementos(pid)[("L1", "NIVEL 2")]
    datos, estado = json.loads(l1["datos_diseno_json"]), json.loads(l1["estado_campos_json"])
    datos["H"], estado["datos_diseno.H"] = "0.30", CONFIRMADO   # el usuario confirmó (y corrigió) H en T7n
    datos["Bw1"] = "0.999"                                    # un campo aún pendiente que alguien cambió
    conn = database.get_connection()
    conn.execute("UPDATE elementos_diseno SET datos_diseno_json = ?, estado_campos_json = ? WHERE uid = ?",
                 (json.dumps(datos), json.dumps(estado), l1["uid"]))
    conn.commit()
    conn.close()
    res = _extraer(c, pid)
    assert res["elementos"]["actualizado"] == 1
    nuevo = _elementos(pid)[("L1", "NIVEL 2")]
    d, e = json.loads(nuevo["datos_diseno_json"]), json.loads(nuevo["estado_campos_json"])
    assert d["H"] == "0.30" and e["datos_diseno.H"] == CONFIRMADO       # confirmado: intacto
    assert d["Bw1"] == "0.125" and e["datos_diseno.Bw1"] == PENDIENTE_ESTADO  # pendiente: se vuelve a proponer
    assert "datos_diseno.H" not in json.loads(nuevo["pendientes_json"])


def test_un_choque_con_el_unique_abre_duda_y_no_toca_la_fila(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), DATOS_COMPLETOS)
    conn = database.get_connection()
    conn.execute("""INSERT INTO elementos_diseno (uid, proyecto_id, id_elemento, tipo_elemento, nivel_rango, ejes,
                    hoja_plano_origen, archivo_plano_origen, datos_diseno_json, estado_campos_json, actualizado)
                    VALUES ('manual-1', ?, 'L1', 'LOSA', 'NIVEL 2', '—', '20', 'otro.pdf', '{"H": "0.40"}', '{}', 'x')""", (pid,))
    conn.commit()
    conn.close()
    res = _extraer(c, pid)  # sin IntegrityError
    assert res["elementos"]["choque"] == 1 and res["elementos"]["nuevo"] == 1
    fila = _elementos(pid)[("L1", "NIVEL 2")]
    assert fila["uid"] == "manual-1" and json.loads(fila["datos_diseno_json"]) == {"H": "0.40"}
    duda = next(d for d in _dudas(pid) if d["campo"] == "clave_unica@NIVEL 2")
    assert duda["id_elemento"] == "L1" and "manual-1" in duda["descripcion_pregunta"]


# ---------- Zapata de muro de lindero y variante de losa aligerada (P16) ----------

def test_zapata_de_muro_lindero_propone_sus_filas_con_nivel_y_ejes_pendientes(entorno):
    def construir(doc):
        pag = _hoja(doc, "05", None)
        x0, y0 = 700, 300
        _t(pag, x0, y0, "TABLA DE APLICACION PARA", 10)
        _t(pag, x0 + 3, y0 + 12, "ZAPATA DE MURO LINDERO", 10)
        for col, dx in {"MURO": 0, "B": 38, "h": 70, "Df": 100, "ACERO Ast": 130, "ACERO Asl": 190}.items():
            _t(pag, x0 + dx, y0 + 40, col, 8)
        for i, fila in enumerate([('6"', "0.60", "0.30", "0.80", 'Ø 3/8" @ 0.15', '4 Ø 3/8"'),
                                  ('8"', "0.80", "0.30", "1.00", 'Ø 3/8" @ 0.10', '5 Ø 3/8"')]):
            for dx, v in zip((0, 38, 70, 100, 130, 190), fila):
                _t(pag, x0 + dx, y0 + 58 + 17 * i, v, 8)
    c = entorno
    pid = _obra(c, _vectorial(construir))
    _extraer(c, pid)
    z = _elementos(pid)[('ZAPATA MURO LINDERO 8"', PENDIENTE)]
    assert z["tipo_elemento"] == "ZAPATA DE MURO" and z["ejes"] == PENDIENTE
    assert json.loads(z["datos_diseno_json"]) == {"B": "0.80", "h": "0.30", "Df": "1.00", "ACERO Ast": 'Ø 3/8" @ 0.10',
                                                  "ACERO Asl": '5 Ø 3/8"'}
    assert _tabla(c, pid, "p1:zapata_muro_lindero")["resultado"] == "verde"
    campos = {d["campo"] for d in _dudas(pid) if d["id_elemento"] == 'ZAPATA MURO LINDERO 8"'}
    assert {f"nivel_rango@{PENDIENTE}", f"ejes@{PENDIENTE}"} <= campos  # lo que la tabla no da, pendiente + duda


def _aligerada(pag, nivel, filas, x0=1000, y0=100):
    _t(pag, x0, y0, f"TABLA DE LOSA ALIGERADA ({nivel})", 8)
    cols = {"Losa": 0, "AsxC": 45, "AsxB": 100, "AsyC": 155, "AsyB": 210, "Ht(m)": 265, "HB(m)": 320}
    for col, dx in cols.items():
        _t(pag, x0 + dx, y0 + 30, col, 8)
    for i, fila in enumerate(filas):
        for dx, v in zip(cols.values(), fila):
            _t(pag, x0 + dx, y0 + 50 + 20 * i, v, 8)


def test_variante_tabla_de_losa_aligerada_por_nivel(entorno):
    def construir(doc):
        pag = _hoja(doc, "10", None)
        _t(pag, 100, 860, "PLANTA ESTRUCTURAL DE ENTREPISO E9", 15)
        _t(pag, 800, 860, "PLANTA ESTRUCTURAL DE TECHO", 15)
        _aligerada(pag, "E9", [("L9", '3 Ø 1/2"', '3 Ø 1/2"', "-", "-", "0.05", "0.20"),
                               ("L10", '3 Ø 1/2"', '3 Ø 1/2"', '3 Ø 1/2"', '3 Ø 1/2"', "0.05", "0.15")])
        _aligerada(pag, "TECHO", [("L1", '3 Ø 1/2"', '3 Ø 1/2"', "-", "-", "0.05", "0.15")], y0=450)
    c = entorno
    pid = _obra(c, _vectorial(construir))
    res = _extraer(c, pid)
    el = _elementos(pid)
    assert set(el) == {("L9", "ENTREPISO E9"), ("L10", "ENTREPISO E9"), ("L1", "TECHO")}
    l9 = el[("L9", "ENTREPISO E9")]
    assert l9["tipo_elemento"] == "LOSA ALIGERADA" and l9["ejes"] == "—"
    d = json.loads(l9["datos_diseno_json"])
    assert d["AsyC"] == "-" and d["HB(m)"] == "0.20" and d["AsxC"] == '3 Ø 1/2"'
    assert {t["clave"]: t["resultado"] for t in res["tablas"]} == {"p1:losa_aligerada:E9": "verde",
                                                                   "p1:losa_aligerada:TECHO": "verde"}


def test_lector_devuelve_las_dos_tablas_de_losa_aligerada_de_la_hoja(tmp_path):
    doc = pymupdf.open()
    pag = _hoja(doc, "10", "PLANTA ESTRUCTURAL DE ENTREPISO E9")
    _aligerada(pag, "E9", [("L9", '3 Ø 1/2"', '3 Ø 1/2"', "-", "-", "0.05", "0.20")])
    _aligerada(pag, "TECHO", [("L1", '3 Ø 1/2"', "-", "-", "-", "0.05", "0.15")], y0=450)
    ruta = tmp_path / "a.pdf"
    doc.save(str(ruta))
    doc.close()
    t = lp.tablas_losa_aligerada(ruta, 1)
    assert [x["nivel_impreso"] for x in t] == ["E9", "TECHO"]
    assert [f["etiqueta"]["valor"] for f in t[0]["filas"]] == ["L9"] and t[0]["filas"][0]["celdas"]["HB(m)"]["valor"] == "0.20"
    assert t[1]["filas"][0]["celdas"]["AsxB"]["valor"] == "-" and t[1]["descartadas"] == []


# ---------- Errores ----------

def test_sin_plano_vigente_responde_409(entorno):
    c = entorno
    pid = c.post("/api/proyectos", json={"nombre": "Sin Plano"}).json()["proyecto"]["id"]
    assert c.post(f"/api/proyectos/{pid}/extraer-diseno").status_code == 409
    assert c.post("/api/proyectos/no-existe/extraer-diseno").status_code == 404


def test_un_vectorial_alterado_despues_de_subirlo_no_se_lee(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), DATOS_COMPLETOS)
    conn = database.get_connection()
    ruta = Path(conn.execute("SELECT vectorial_ruta FROM planos WHERE proyecto_id = ?", (pid,)).fetchone()[0])
    conn.close()
    ruta.write_bytes(ruta.read_bytes() + b"\n%alterado")
    r = c.post(f"/api/proyectos/{pid}/extraer-diseno")
    assert r.status_code == 409 and "sha256" in r.json()["detail"]
    assert _elementos(pid) == {}


# ---------- Funciones puras ----------

def test_nivel_de_titulo_y_expansiones_sin_adivinar():
    assert ex.nivel_de_titulo("PLANTA ESTRUCTURAL DE SOTANO S6") == "SOTANO S6"
    assert ex.nivel_de_titulo("PLANTA ESTRUCTURAL NIVEL 4@8") == "NIVEL 4@8"
    assert ex.nivel_de_titulo("PLANTA ESTRUCTURAL DE ENTREPISO E3 @ E8") == "ENTREPISO E3 @ E8"
    assert ex.expandir_nivel("NIVEL 4@8") == ["NIVEL 4", "NIVEL 5", "NIVEL 6", "NIVEL 7", "NIVEL 8"]
    assert ex.expandir_nivel("ENTREPISO E3 @ E5") == ["ENTREPISO E3", "ENTREPISO E4", "ENTREPISO E5"]
    assert ex.expandir_nivel("SOTANO S6") == ["SOTANO S6"]
    assert ex.expandir_rango_e("E3", "E5", {}) == (["E-3", "E-4", "E-5"], "")
    assert ex.expandir_rango_e("FUND.", "E3", {})[0] is None
    assert ex.expandir_rango_e("E10", "E3", {})[0] is None
    assert ex.e_de_nivel("ENTREPISO E9", {}) == "E-9"
    assert ex.e_de_nivel("NIVEL 1", {"E-1": "NIVEL 18"}) is None  # 'NIVEL 1' no es 'NIVEL 18'
    assert ex.e_de_nivel("LOSA DE PISO (SOTANO S7)", {"E-1": "SOTANO S7"}) == "E-1"
