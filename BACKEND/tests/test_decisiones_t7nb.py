# BACKEND/tests/test_decisiones_t7nb.py
# Etapa 2 · T7n-b — Las 5 decisiones de Steven sobre la confirmación de los datos del plano (PLANES/etapa-2.md).
# Todo # SINTÉTICO: los vectoriales se generan con PyMuPDF (fixtures de test_extractor); ningún plano ni dato real.
import json

import database
import obras
from importadores.validador_diseno import CONFIRMADO, PENDIENTE_ESTADO
from plano import extractor as ex
from reglas_ingenieria import PENDIENTE
from test_confirmacion import _auditoria, _confirmar, _estado, _sql
from test_extractor import (COLS_LOSA, DATOS_COMPLETOS, FILAS_LOSA, _dudas, _elementos, _extraer, _hoja, _ids,  # noqa: F401
                            _obra, _planta_basica, _t, _tabla, _tabla_fc, _tabla_losa, _vectorial, entorno)

NOTA = ["SE MODIFICO EL ARMADO DE LAS LOSAS EN", "REEMPLAZO DE LA SOLUCION INDICADA EN EL PLANO ANTERIOR APROBADO."]


def _filas(sin=None):
    """FILAS_LOSA con las celdas `sin` = {(fila, columna)} vacías (no se imprime nada en ellas)."""
    cols = list(COLS_LOSA)
    return [tuple(None if (f[0], cols[j]) in (sin or set()) else v for j, v in enumerate(f)) for f in FILAS_LOSA]


def _planta(doc, sin=None, nota=False):
    pag = _hoja(doc, "20", "PLANTA ESTRUCTURAL NIVEL 2")
    _tabla_losa(pag, filas=_filas(sin))
    _ids(pag, ("L1", "L2"))
    _tabla_fc(pag, (("E1 @ E3", "350 Kg/cm2"), ("E4 @ E6", "280 Kg/cm2")))
    if nota:
        for i, linea in enumerate(NOTA):
            _t(pag, 100, 600 + 10 * i, linea, 8)
    return pag


def _guardar_tipo(c, pid, lid, tipo):
    r = c.put(f"/api/proyectos/{pid}/datos-obra", json={"tipo": "losa_tipo", "items": [{"clave": lid, "valor": tipo}]})
    assert r.status_code == 200, r.text


# ---------- Decisión 1: el L#→tipo de "Datos de la obra" llega confirmado ----------

def test_el_tipo_de_losa_del_usuario_llega_confirmado_con_referencia_a_su_auditoria(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), DATOS_COMPLETOS)
    _extraer(c, pid)
    l1 = _elementos(pid)[("L1", "NIVEL 2")]
    assert json.loads(l1["estado_campos_json"])["datos_diseno.tipo_losa"] == CONFIRMADO
    assert "datos_diseno.tipo_losa" not in json.loads(l1["pendientes_json"])
    fuente = json.loads(l1["fuente_json"])["valores"]["tipo_losa"]
    assert fuente["origen"] == "usuario" and fuente["via"] == "datos_de_la_obra"
    guardar = next(a for a in _auditoria("GUARDAR_DATOS_OBRA") if a["detalle"]["tipo"] == "losa_tipo")
    assert fuente["auditoria_id"] == guardar["id"] and fuente["por"] == "steven"
    aud = [a for a in _auditoria("CONFIRMAR_CAMPO") if a["entidad_id"] == l1["uid"]]
    assert len(aud) == 1 and aud[0]["modulo"] == "EXTRACTOR" and aud[0]["detalle"]["campo"] == "tipo_losa"
    assert aud[0]["detalle"]["valor"] == "A" and aud[0]["detalle"]["fuente"]["auditoria_id"] == guardar["id"]
    # volver a extraer sin cambios no repite la auditoría
    _extraer(c, pid)
    assert len([a for a in _auditoria("CONFIRMAR_CAMPO") if a["entidad_id"] == l1["uid"]]) == 1


def test_si_el_usuario_cambia_el_tipo_lo_confirmado_de_la_fila_vieja_no_se_toca_y_abre_duda(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), DATOS_COMPLETOS)
    _extraer(c, pid)
    assert _confirmar(c, pid, _tabla(c, pid, "p1:acero_en_losa")).status_code == 200  # L1 con la fila A
    _guardar_tipo(c, pid, "L1", "B")
    _extraer(c, pid)
    l1 = _elementos(pid)[("L1", "NIVEL 2")]
    datos, estado = json.loads(l1["datos_diseno_json"]), json.loads(l1["estado_campos_json"])
    assert datos["tipo_losa"] == "B" and estado["datos_diseno.tipo_losa"] == CONFIRMADO  # sigue al usuario
    assert datos["DIR. X"] == '3Ø1/2"' and estado["datos_diseno.DIR. X"] == CONFIRMADO   # fila A: intacta
    duda = next(d for d in _dudas(pid) if d["campo"] == "tipo_losa_cambiado@NIVEL 2")
    assert duda["id_elemento"] == "L1" and "DIR. X" in duda["descripcion_pregunta"]
    aud = [a for a in _auditoria("CONFIRMAR_CAMPO") if a["entidad_id"] == l1["uid"] and a["modulo"] == "EXTRACTOR"]
    assert [(a["detalle"]["valor"], a["detalle"]["valor_anterior"]) for a in aud] == [("A", None), ("B", "A")]


# ---------- Decisión 2: el lote confirma también la identidad ----------

def test_el_lote_confirma_la_identidad_con_una_fila_de_auditoria_por_campo(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), DATOS_COMPLETOS)
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:acero_en_losa")
    det = c.get(f"/api/proyectos/{pid}/tablas-extraidas/{t['id']}").json()
    assert {(x["id_elemento"], x["campo"]) for x in det["identidad"]} == {
        (lid, k) for lid in ("L1", "L2") for k in ("id_elemento", "nivel_rango", "ejes", "hoja_plano_origen",
                                                  "archivo_plano_origen")}
    res = _confirmar(c, pid, t).json()
    assert res["identidad_confirmados"] == 10
    e = _estado(pid, "L1")
    for k in ("id_elemento", "nivel_rango", "ejes", "hoja_plano_origen", "archivo_plano_origen"):
        assert e[k] == CONFIRMADO
    assert e["tipo_elemento"] == PENDIENTE_ESTADO  # fuera de la decisión 2
    aud = {a["detalle"]["campo"]: a for a in _auditoria("CONFIRMAR_CAMPO")
           if a["detalle"]["id_elemento"] == "L1" and a["detalle"]["lote"] == res["lote"]}
    assert aud["ejes"]["detalle"]["valor"] == "—" and aud["nivel_rango"]["detalle"]["valor"] == "NIVEL 2"
    assert aud["hoja_plano_origen"]["detalle"]["fuente"]["hoja"] == "20"
    assert aud["archivo_plano_origen"]["detalle"]["valor"] == "vec.pdf"
    assert aud["id_elemento"]["detalle"]["fuente"]["bbox"]
    fuente = json.loads(_elementos(pid)[("L1", "NIVEL 2")]["fuente_json"])
    assert fuente["identidad"]["nivel_rango"]["confirmado"]["lote"] == res["lote"]


def test_la_identidad_pendiente_no_se_confirma_en_el_lote(entorno):
    def construir(doc):
        pag = _hoja(doc, "05", None)
        x0, y0 = 700, 300
        _t(pag, x0, y0, "TABLA DE APLICACION PARA", 10)
        _t(pag, x0 + 3, y0 + 12, "ZAPATA DE MURO LINDERO", 10)
        for col, dx in {"MURO": 0, "B": 38, "h": 70, "Df": 100, "ACERO Ast": 130, "ACERO Asl": 190}.items():
            _t(pag, x0 + dx, y0 + 40, col, 8)
        for dx, v in zip((0, 38, 70, 100, 130, 190), ('8"', "0.80", "0.30", "1.00", 'Ø 3/8" @ 0.10', '5 Ø 3/8"')):
            _t(pag, x0 + dx, y0 + 58, v, 8)
    c = entorno
    pid = _obra(c, _vectorial(construir))
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:zapata_muro_lindero")
    assert _confirmar(c, pid, t).status_code == 200
    e = _estado(pid, 'ZAPATA MURO LINDERO 8"', PENDIENTE)
    assert e["id_elemento"] == CONFIRMADO and e["hoja_plano_origen"] == CONFIRMADO
    assert e["nivel_rango"] == PENDIENTE_ESTADO and e["ejes"] == PENDIENTE_ESTADO  # la tabla no los da


def test_una_hoja_distinta_de_la_tabla_detiene_el_lote(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), DATOS_COMPLETOS)
    _extraer(c, pid)
    _sql("UPDATE elementos_diseno SET hoja_plano_origen = '99' WHERE id_elemento = 'L2'")
    r = _confirmar(c, pid, _tabla(c, pid, "p1:acero_en_losa"))
    assert r.status_code == 409 and "hoja_plano_origen" in r.json()["detail"]
    assert _estado(pid, "L1")["id_elemento"] == PENDIENTE_ESTADO  # atómico


# ---------- Decisión 3: AS. ADIC. vacía = sin acero adicional ----------

def test_as_adic_vacia_es_sin_acero_y_la_tabla_queda_en_verde(entorno):
    c = entorno
    pid = _obra(c, _vectorial(lambda d: _planta(d, sin={("A", "AS. ADIC."), ("B", "AS. ADIC.")})), DATOS_COMPLETOS)
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:acero_en_losa")
    assert t["resultado"] == "verde", [x for x in t["comprobaciones"] if not x["ok"]]
    celda = next(f for f in t["filas"] if f["etiqueta"]["valor"] == "A")["celdas"]["AS. ADIC."]
    assert celda["valor"] == ex.SIN_ACERO and celda["vacia"] and "Steven" in celda["regla"] and len(celda["bbox"]) == 4
    l1 = _elementos(pid)[("L1", "NIVEL 2")]  # L1 es tipo A
    assert json.loads(l1["datos_diseno_json"])["AS. ADIC."] == ex.SIN_ACERO
    fuente = json.loads(l1["fuente_json"])["valores"]["AS. ADIC."]
    assert fuente["celda_vacia"] is True and "sin acero adicional" in fuente["regla"]
    assert not [d for d in _dudas(pid) if "AS. ADIC." in d["campo"]]
    # se confirma por lote como cualquier otro valor
    assert _confirmar(c, pid, t).status_code == 200
    assert _estado(pid, "L1")["datos_diseno.AS. ADIC."] == CONFIRMADO


def test_otra_celda_vacia_sigue_siendo_duda_y_la_tabla_queda_en_rojo(entorno):
    c = entorno
    pid = _obra(c, _vectorial(lambda d: _planta(d, sin={("A", "AS. ADIC."), ("A", "Bw2")})), DATOS_COMPLETOS)
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:acero_en_losa")
    fallo = next(x for x in t["comprobaciones"] if x["comprobacion"] == "celdas_completas")
    assert t["resultado"] == "rojo" and fallo["detalle"] == ["A / Bw2"]
    campos = {(d["id_elemento"], d["campo"]) for d in _dudas(pid)}
    assert ("A", "p1:acero_en_losa:Bw2") in campos and ("A", "p1:acero_en_losa:AS. ADIC.") not in campos
    assert json.loads(_elementos(pid)[("L1", "NIVEL 2")]["datos_diseno_json"])["Bw2"] == PENDIENTE


def test_la_duda_vieja_de_as_adic_vacia_se_cierra_con_auditoria(entorno):
    c = entorno
    pid = _obra(c, _vectorial(lambda d: _planta(d, sin={("A", "AS. ADIC.")})), DATOS_COMPLETOS)
    # la duda que abría el extractor antes de la decisión 3
    _sql("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria, campo_afectado,
            descripcion_pregunta, creado) VALUES (?, NULL, 'A', 'DUDA_BLOQUEANTE', 'T6n:p1:acero_en_losa:AS. ADIC.',
            'vacía', 'x')""", (pid,))
    res = _extraer(c, pid)
    assert res["dudas_cerradas"] == 1
    duda = _sql("SELECT * FROM dudas_y_hallazgos WHERE campo_afectado = 'T6n:p1:acero_en_losa:AS. ADIC.'")[0]
    assert duda["resuelta"] == 1
    assert duda["id"] in _auditoria("CERRAR_DUDAS_REEXTRACCION")[0]["detalle"]["dudas_cerradas"]


# ---------- Decisión 4: certificar las notas de modificación ----------

def _certificar(c, pid, t, **cuerpo):
    return c.post(f"/api/proyectos/{pid}/tablas-extraidas/{t['id']}/certificar-notas",
                  json={"certifico": True, "extraido_en": t["extraido_en"], **cuerpo})


def test_certificar_la_nota_pone_la_tabla_en_verde_y_no_se_reabre_al_reextraer(entorno):
    c = entorno
    pid = _obra(c, _vectorial(lambda d: _planta(d, nota=True)), DATOS_COMPLETOS)
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:acero_en_losa")
    assert t["resultado"] == "rojo" and [x["comprobacion"] for x in t["comprobaciones"] if not x["ok"]] == [
        ex.COMPROBACION_NOTAS]
    assert any(d["campo"] == "p1:acero_en_losa:nota" for d in _dudas(pid))
    det = c.get(f"/api/proyectos/{pid}/tablas-extraidas/{t['id']}").json()
    assert det["certificable"] and not det["confirmable"]
    assert c.post(f"/api/proyectos/{pid}/tablas-extraidas/{t['id']}/certificar-notas", json={}).status_code == 422

    r = _certificar(c, pid, t)
    assert r.status_code == 200, r.text
    assert r.json()["resultado"] == "verde" and len(r.json()["dudas_cerradas"]) == 1
    t = _tabla(c, pid, "p1:acero_en_losa")
    nota = next(x for x in t["comprobaciones"] if x["comprobacion"] == ex.COMPROBACION_NOTAS)
    assert t["resultado"] == "verde" and nota["ok"] and nota["certificada"]["por"] == "steven"
    assert "PLANO ANTERIOR" in nota["certificada"]["notas"][0]
    aud = _auditoria("CERTIFICAR_NOTAS")
    sha = _sql("SELECT vectorial_sha256 FROM planos WHERE proyecto_id = ?", (pid,))[0]["vectorial_sha256"]
    assert len(aud) == 1 and aud[0]["usuario"] == "steven" and aud[0]["detalle"]["tabla"] == "p1:acero_en_losa"
    assert aud[0]["detalle"]["sha256"] == sha
    assert _certificar(c, pid, t).status_code == 409  # ya certificada
    # volver a extraer: sigue en verde y la duda no se reabre
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:acero_en_losa")
    assert t["resultado"] == "verde" and not any(d["campo"] == "p1:acero_en_losa:nota" for d in _dudas(pid))
    assert _confirmar(c, pid, t).status_code == 200


def test_si_cambia_el_plano_la_certificacion_se_pierde(entorno):
    c = entorno
    pid = _obra(c, _vectorial(lambda d: _planta(d, nota=True)), DATOS_COMPLETOS)
    _extraer(c, pid)
    assert _certificar(c, pid, _tabla(c, pid, "p1:acero_en_losa")).status_code == 200
    # nuevo vectorial (otra revisión, otro sha256) con la misma nota
    r = c.post(f"/api/proyectos/{pid}/planos",
               files={"vectorial": ("vec2.pdf", _vectorial(lambda d: _planta(d, nota=True, sin={("C", "AS. ADIC.")})),
                                    "application/pdf"),
                      "sellado": ("sel2.pdf", _vectorial(lambda d: d.new_page()), "application/pdf")},
               data={"certifico": "true"})
    assert r.status_code == 201, r.text
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:acero_en_losa")
    assert t["resultado"] == "rojo" and any(d["campo"] == "p1:acero_en_losa:nota" for d in _dudas(pid))


def test_una_tabla_sin_notas_no_se_certifica(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), DATOS_COMPLETOS)
    _extraer(c, pid)
    r = _certificar(c, pid, _tabla(c, pid, "p1:acero_en_losa"))
    assert r.status_code == 409 and _auditoria("CERTIFICAR_NOTAS") == []


# ---------- Decisión 5: un solo usuario en la auditoría ----------

def test_lote_mesa_datos_de_la_obra_y_extractor_auditan_como_steven(entorno, monkeypatch):
    monkeypatch.setattr("getpass.getuser", lambda: "OtroUsuarioDelSistema")
    assert database.usuario_auditoria() == "steven" and obras._usuario() == "steven"
    c = entorno
    pid = _obra(c, _vectorial(lambda d: _planta(d, sin={("A", "Bw2")})), DATOS_COMPLETOS)
    _extraer(c, pid)
    duda = next(d for d in c.get("/api/dudas", params={"proyecto_id": pid, "sin_visita": True}).json()
                if d["campo_afectado"] == "T6n:p1:acero_en_losa:Bw2")
    assert c.patch(f"/api/dudas/{duda['id']}", json={"respuesta": "0.156"}).status_code == 200
    assert _confirmar(c, pid, _tabla(c, pid, "p1:fc_por_rango")).status_code == 200
    usuarios = {(r["modulo"], r["accion"]): r["usuario"] for r in _sql("SELECT modulo, accion, usuario FROM auditoria")}
    for clave in (("OBRAS", "GUARDAR_DATOS_OBRA"), ("EXTRACTOR", "EXTRAER_DISENO"), ("MESA_DUDAS", "RESPONDER_DUDA"),
                  ("CONFIRMACION", "CONFIRMAR_LOTE"), ("CONFIRMACION", "CONFIRMAR_CAMPO")):
        assert usuarios[clave] == "steven", clave
    assert "OtroUsuarioDelSistema" not in {r["usuario"] for r in _sql("SELECT usuario FROM auditoria")}
