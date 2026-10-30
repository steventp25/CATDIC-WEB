# BACKEND/tests/test_confirmacion.py
# Etapa 2 · T7n — Confirmación de los datos extraídos del plano (PLANES/etapa-2.md, T7n).
# Todo # SINTÉTICO: los vectoriales se generan con PyMuPDF (fixtures de test_extractor); ningún plano ni dato real.
import json

import pytest

import database
from importadores.validador_diseno import CONFIRMADO, PENDIENTE_ESTADO
from plano import confirmacion as cf
from reglas_ingenieria import PENDIENTE
from test_extractor import (DATOS_COMPLETOS, _dudas, _elementos, _extraer, _hoja, _obra, _planta_basica, _t,  # noqa: F401
                            _tabla, _vectorial, entorno)

CAMPOS_DE_LA_TABLA = {"H", "Bw1", "Bw2", "h1", "h2", "DIR. X", "DIR. Y", "AS. ADIC."}
IDENTIDAD = {"id_elemento", "nivel_rango", "ejes", "hoja_plano_origen", "archivo_plano_origen"}
DEL_USUARIO = {"datos_diseno.tipo_losa"}  # T7n-b: el L#→tipo de "Datos de la obra" llega confirmado
IDENTIDAD = {"id_elemento", "nivel_rango", "ejes", "hoja_plano_origen", "archivo_plano_origen"}
DEL_USUARIO = {"datos_diseno.tipo_losa"}  # T7n-b: el L#→tipo de "Datos de la obra" llega confirmado


def _sql(consulta, params=()):
    conn = database.get_connection()
    try:
        filas = [dict(r) for r in conn.execute(consulta, params)]
        conn.commit()
        return filas
    finally:
        conn.close()


def _estado(pid, id_elemento, nivel="NIVEL 2"):
    return json.loads(_elementos(pid)[(id_elemento, nivel)]["estado_campos_json"])


def _auditoria(accion):
    return [{**a, "detalle": json.loads(a["detalle_json"])} for a in
            _sql("SELECT * FROM auditoria WHERE accion = ? ORDER BY id", (accion,))]


def _sin_confirmar(estado):
    """Nada confirmado salvo lo que el usuario dio en "Datos de la obra" (T7n-b)."""
    return not {k for k, v in estado.items() if v == CONFIRMADO} - DEL_USUARIO


def _auditoria_lote():
    """Filas CONFIRMAR_CAMPO del lote o de la Mesa (las del extractor son las del L#→tipo de "Datos de la obra")."""
    return [a for a in _auditoria("CONFIRMAR_CAMPO") if a["modulo"] == cf.MODULO]


def _confirmar(c, pid, tabla, **cuerpo):
    return c.post(f"/api/proyectos/{pid}/tablas-extraidas/{tabla['id']}/confirmar",
                  json={"confirmo": True, "extraido_en": tabla["extraido_en"], **cuerpo})


def _obra_verde(c):
    pid = _obra(c, _vectorial(_planta_basica), DATOS_COMPLETOS)
    _extraer(c, pid)
    return pid


# ---------- Lote en verde ----------

def test_confirmar_una_tabla_verde_confirma_sus_celdas_con_auditoria_por_campo(entorno):
    c = entorno
    pid = _obra_verde(c)
    t = _tabla(c, pid, "p1:acero_en_losa")
    assert t["resultado"] == "verde" and t["vigente"] and t["motivos_no_vigente"] == []
    det = c.get(f"/api/proyectos/{pid}/tablas-extraidas/{t['id']}").json()
    assert det["confirmable"] and len(det["campos"]) == 16 and len(det["recorte"]) == 4
    assert all(x["valor"] == x["valor_tabla"] for x in det["campos"])

    r = _confirmar(c, pid, t)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["confirmados"] == 16 and res["elementos"] == 2 and res["conflictos"] == 0
    for lid in ("L1", "L2"):
        e = _estado(pid, lid)
        assert {k.removeprefix("datos_diseno.") for k, v in e.items() if v == CONFIRMADO} \
            == CAMPOS_DE_LA_TABLA | IDENTIDAD | {"tipo_losa"}
        # lo que no viene de esta tabla ni del usuario sigue pendiente (f'c de otra tabla, tipo de elemento)
        for k in ("datos_diseno.fc_kgcm2", "tipo_elemento"):
            assert e[k] == PENDIENTE_ESTADO
        pend = set(json.loads(_elementos(pid)[(lid, "NIVEL 2")]["pendientes_json"]))
        assert pend == {k for k, v in e.items() if v != CONFIRMADO}
    assert res["identidad_confirmados"] == 10 and res["elementos_identidad"] == 2
    aud = [a for a in _auditoria("CONFIRMAR_CAMPO") if a["detalle"]["lote"]]
    assert len(aud) == 26 and {a["detalle"]["lote"] for a in aud} == {res["lote"]}
    h = next(a for a in aud if a["detalle"]["id_elemento"] == "L1" and a["detalle"]["campo"] == "H")
    assert h["detalle"]["valor"] == "0.25" and h["usuario"]
    f = h["detalle"]["fuente"]
    assert f["archivo"] == "vec.pdf" and f["revision"] == 1 and f["pagina"] == 1 and f["hoja"] == "20"
    assert f["fila"] == "A" and f["columna"] == "H" and len(f["bbox"]) == 4 and len(f["sha256"]) == 64
    lote = _auditoria("CONFIRMAR_LOTE")
    assert len(lote) == 1 and lote[0]["detalle"]["confirmados"] == 16
    # la fuente del campo guarda el lote; una segunda confirmación ya no tiene nada pendiente
    fuente = json.loads(_elementos(pid)[("L1", "NIVEL 2")]["fuente_json"])
    assert fuente["valores"]["H"]["confirmado"]["lote"] == res["lote"]
    assert _confirmar(c, pid, t).status_code == 409


def test_la_tabla_de_fc_confirma_el_fc_de_las_losas(entorno):
    c = entorno
    pid = _obra_verde(c)
    t = _tabla(c, pid, "p1:fc_por_rango")
    assert t["resultado"] == "verde"
    res = _confirmar(c, pid, t).json()
    assert res["confirmados"] == 2
    assert _estado(pid, "L1")["datos_diseno.fc_kgcm2"] == CONFIRMADO
    assert _estado(pid, "L1")["datos_diseno.H"] == PENDIENTE_ESTADO


def test_sin_la_confirmacion_explicita_422_y_nada_cambia(entorno):
    c = entorno
    pid = _obra_verde(c)
    t = _tabla(c, pid, "p1:acero_en_losa")
    r = c.post(f"/api/proyectos/{pid}/tablas-extraidas/{t['id']}/confirmar", json={})
    assert r.status_code == 422
    assert _sin_confirmar(_estado(pid, "L1")) and _auditoria_lote() == []


# ---------- Rechazos (409): rojo y extracción no vigente ----------

def test_una_tabla_roja_no_se_confirma(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), {"equivalencia_nivel": {"E-2": "NIVEL 2"}})  # sin L#→tipo: rojo
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:acero_en_losa")
    assert t["resultado"] == "rojo"
    det = c.get(f"/api/proyectos/{pid}/tablas-extraidas/{t['id']}").json()
    assert not det["confirmable"] and any("rojo" in m for m in det["motivos_no_confirmable"])
    r = _confirmar(c, pid, t)
    assert r.status_code == 409 and "Mesa de Dudas" in r.json()["detail"]
    assert _auditoria("CONFIRMAR_CAMPO") == []


def test_datos_de_la_obra_cambiados_despues_de_extraer_obligan_a_reextraer(entorno):
    c = entorno
    pid = _obra_verde(c)
    c.put(f"/api/proyectos/{pid}/datos-obra", json={"tipo": "losa_tipo", "items": [{"clave": "L2", "valor": "B"}]})
    t = _tabla(c, pid, "p1:acero_en_losa")
    assert not t["vigente"] and "vuelve a extraer" in t["motivos_no_vigente"][0]
    assert _confirmar(c, pid, t).status_code == 409
    _extraer(c, pid)
    t = _tabla(c, pid, "p1:acero_en_losa")
    assert t["vigente"] and _confirmar(c, pid, t).status_code == 200
    assert json.loads(_elementos(pid)[("L2", "NIVEL 2")]["datos_diseno_json"])["DIR. X"] == '2Ø1/2"'  # tipo B


def test_una_fila_de_una_extraccion_anterior_queda_marcada_y_no_se_confirma(entorno):
    c = entorno
    pid = _obra_verde(c)
    t = _tabla(c, pid, "p1:acero_en_losa")
    # una tabla que la última corrida ya no leyó conserva su extraido_en viejo
    _sql("UPDATE tablas_extraidas SET extraido_en = '2000-01-01T00:00:00' WHERE id = ?", (t["id"],))
    t = _tabla(c, pid, "p1:acero_en_losa")
    assert not t["vigente"] and "extracción anterior" in t["motivos_no_vigente"][0]
    r = c.post(f"/api/proyectos/{pid}/tablas-extraidas/{t['id']}/confirmar", json={"confirmo": True})
    assert r.status_code == 409 and _auditoria_lote() == []


def test_otra_revision_o_sha256_no_se_confirma(entorno):
    c = entorno
    pid = _obra_verde(c)
    t = _tabla(c, pid, "p1:acero_en_losa")
    fuente = {**t["fuente"], "sha256": "0" * 64}
    _sql("UPDATE tablas_extraidas SET fuente_json = ? WHERE id = ?", (json.dumps(fuente), t["id"]))
    r = _confirmar(c, pid, _tabla(c, pid, "p1:acero_en_losa"))
    assert r.status_code == 409 and "sha256" in r.json()["detail"]


def test_si_el_plano_cambio_la_tabla_vieja_no_se_confirma(entorno):
    c = entorno
    pid = _obra_verde(c)
    t = _tabla(c, pid, "p1:acero_en_losa")
    from test_extractor import _sellado
    r = c.post(f"/api/proyectos/{pid}/planos", files={"vectorial": ("vec2.pdf", _vectorial(_planta_basica), "application/pdf"),
                                                       "sellado": ("sel2.pdf", _sellado(), "application/pdf")},
               data={"certifico": "true"})
    assert r.status_code == 201, r.text
    assert _tabla_ids(c, pid) == []  # el plano nuevo aún no se extrajo: no hay tablas vigentes
    r = _confirmar(c, pid, t)
    assert r.status_code == 409 and "ya no es el vigente" in r.json()["detail"]


def _tabla_ids(c, pid):
    return [t["id"] for t in c.get(f"/api/proyectos/{pid}/tablas-extraidas").json()["tablas"]]


def test_una_tabla_reextraida_mientras_se_revisaba_pide_abrirla_de_nuevo(entorno):
    c = entorno
    pid = _obra_verde(c)
    t = _tabla(c, pid, "p1:acero_en_losa")
    r = _confirmar(c, pid, {**t, "extraido_en": "2000-01-01T00:00:00"})
    assert r.status_code == 409 and "Ábrela de nuevo" in r.json()["detail"]


def test_un_valor_guardado_distinto_de_la_tabla_detiene_el_lote(entorno):
    c = entorno
    pid = _obra_verde(c)
    l1 = _elementos(pid)[("L1", "NIVEL 2")]
    datos = json.loads(l1["datos_diseno_json"])
    datos["Bw1"] = "0.999"  # pendiente, pero ya no es lo que dice la tabla
    _sql("UPDATE elementos_diseno SET datos_diseno_json = ? WHERE uid = ?", (json.dumps(datos), l1["uid"]))
    r = _confirmar(c, pid, _tabla(c, pid, "p1:acero_en_losa"))
    assert r.status_code == 409 and "Bw1" in r.json()["detail"]
    assert _sin_confirmar(_estado(pid, "L2"))  # atómico: tampoco L2


# ---------- Atomicidad y campos ya confirmados ----------

def test_si_falla_un_campo_no_se_guarda_nada(entorno, monkeypatch):
    c = entorno
    pid = _obra_verde(c)
    t = _tabla(c, pid, "p1:acero_en_losa")
    original, llamadas = cf._auditar_campo, []

    def falla_al_quinto(*a, **k):
        llamadas.append(1)
        if len(llamadas) == 5:
            raise RuntimeError("fallo simulado")
        return original(*a, **k)

    monkeypatch.setattr(cf, "_auditar_campo", falla_al_quinto)
    with pytest.raises(RuntimeError):
        cf.confirmar_tabla(pid, t["id"], t["extraido_en"], usuario="prueba")
    for lid in ("L1", "L2"):
        assert _sin_confirmar(_estado(pid, lid))
    assert _auditoria_lote() == [] and _auditoria("CONFIRMAR_LOTE") == []


def test_un_campo_confirmado_con_otro_valor_no_se_sobrescribe_y_abre_duda(entorno):
    c = entorno
    pid = _obra_verde(c)
    l1 = _elementos(pid)[("L1", "NIVEL 2")]
    datos, estado = json.loads(l1["datos_diseno_json"]), json.loads(l1["estado_campos_json"])
    datos["H"], estado["datos_diseno.H"] = "0.30", CONFIRMADO
    _sql("UPDATE elementos_diseno SET datos_diseno_json = ?, estado_campos_json = ? WHERE uid = ?",
         (json.dumps(datos), json.dumps(estado), l1["uid"]))
    _extraer(c, pid)  # el confirmado se respeta al volver a extraer
    res = _confirmar(c, pid, _tabla(c, pid, "p1:acero_en_losa")).json()
    assert res["confirmados"] == 15 and res["conflictos"] == 1
    assert json.loads(_elementos(pid)[("L1", "NIVEL 2")]["datos_diseno_json"])["H"] == "0.30"
    duda = _sql("SELECT * FROM dudas_y_hallazgos WHERE campo_afectado LIKE 'T7n:%' AND resuelta = 0")
    assert len(duda) == 1 and duda[0]["id_elemento"] == "L1" and "'0.25'" in duda[0]["descripcion_pregunta"]
    assert not any(a["detalle"]["campo"] == "H" and a["detalle"]["id_elemento"] == "L1"
                   for a in _auditoria("CONFIRMAR_CAMPO"))


def test_al_confirmar_se_cierran_las_dudas_t6n_de_esos_campos(entorno):
    c = entorno
    pid = _obra_verde(c)
    _sql("""INSERT INTO dudas_y_hallazgos (proyecto_id, id_elemento, categoria, campo_afectado, descripcion_pregunta, creado)
            VALUES (?, 'L1', 'DUDA_BLOQUEANTE', 'T6n:datos_diseno.H@NIVEL 2', 'sintética', 'x'),
                   (?, 'L1', 'DUDA_BLOQUEANTE', 'T6n:otra_cosa', 'sintética', 'x')""", (pid, pid))
    res = _confirmar(c, pid, _tabla(c, pid, "p1:acero_en_losa")).json()
    assert len(res["dudas_cerradas"]) == 1
    abiertas = {d["campo_afectado"] for d in _sql("SELECT * FROM dudas_y_hallazgos WHERE resuelta = 0")}
    assert "T6n:datos_diseno.H@NIVEL 2" not in abiertas and "T6n:otra_cosa" in abiertas
    assert _auditoria("CERRAR_DUDAS_CONFIRMACION")[0]["detalle"]["lote"] == res["lote"]


# ---------- Uno por uno, por la Mesa de Dudas ----------

def _zapata_con_celda_vacia(doc):
    pag = _hoja(doc, "05", None)
    x0, y0 = 700, 300
    _t(pag, x0, y0, "TABLA DE APLICACION PARA", 10)
    _t(pag, x0 + 3, y0 + 12, "ZAPATA DE MURO LINDERO", 10)
    for col, dx in {"MURO": 0, "B": 38, "h": 70, "Df": 100, "ACERO Ast": 130, "ACERO Asl": 190}.items():
        _t(pag, x0 + dx, y0 + 40, col, 8)
    for i, fila in enumerate([('6"', "0.60", "0.30", "0.80", 'Ø 3/8" @ 0.15', '4 Ø 3/8"'),
                              ('8"', "0.80", "0.30", None, 'Ø 3/8" @ 0.10', '5 Ø 3/8"')]):
        for dx, v in zip((0, 38, 70, 100, 130, 190), fila):
            if v is not None:
                _t(pag, x0 + dx, y0 + 58 + 17 * i, v, 8)


def test_la_mesa_muestra_las_dudas_de_la_obra_y_responder_una_confirma_el_campo(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_zapata_con_celda_vacia))
    _extraer(c, pid)
    assert _tabla(c, pid, "p1:zapata_muro_lindero")["resultado"] == "rojo"
    dudas = c.get("/api/dudas", params={"proyecto_id": pid, "sin_visita": True, "resuelta": False}).json()
    assert dudas and all(d["visita_id"] is None for d in dudas)
    vacia = next(d for d in dudas if d["campo_afectado"] == "T6n:p1:zapata_muro_lindero:Df")
    assert vacia["id_elemento"] == '8"'
    assert vacia["campo_confirmable"]["id_elemento"] == 'ZAPATA MURO LINDERO 8"' and vacia["campo_confirmable"]["campo"] == "Df"
    # una duda que no apunta a un único campo (nivel de la zapata) no es confirmable
    nivel = next(d for d in dudas if d["campo_afectado"] == f"T6n:nivel_rango@{PENDIENTE}")
    assert nivel["campo_confirmable"] is None

    r = c.patch(f"/api/dudas/{vacia['id']}", json={"respuesta": "1,00"})
    assert r.status_code == 422  # no es una dimensión en metros: nada cambia
    z = _elementos(pid)[('ZAPATA MURO LINDERO 8"', PENDIENTE)]
    assert json.loads(z["estado_campos_json"])["datos_diseno.Df"] == PENDIENTE_ESTADO
    r = c.patch(f"/api/dudas/{vacia['id']}", json={"respuesta": "1.00"})
    assert r.status_code == 200, r.text
    assert r.json()["valor_aplicado"] == "1.00"
    z = _elementos(pid)[('ZAPATA MURO LINDERO 8"', PENDIENTE)]
    assert json.loads(z["datos_diseno_json"])["Df"] == "1.00"
    assert json.loads(z["estado_campos_json"])["datos_diseno.Df"] == CONFIRMADO
    f = json.loads(z["fuente_json"])["valores"]["Df"]
    assert f["origen"] == "usuario" and f["duda_id"] == vacia["id"] and f["valor_propuesto"] == PENDIENTE
    aud = _auditoria("CONFIRMAR_CAMPO")
    assert len(aud) == 1 and aud[0]["detalle"]["lote"] is None and aud[0]["detalle"]["valor"] == "1.00"
    assert aud[0]["detalle"]["fuente"]["origen"] == "usuario" and aud[0]["detalle"]["fuente"]["archivo"] == "vec.pdf"
    # al volver a extraer, el campo confirmado no se toca y su duda no se reabre
    _extraer(c, pid)
    z = _elementos(pid)[('ZAPATA MURO LINDERO 8"', PENDIENTE)]
    assert json.loads(z["datos_diseno_json"])["Df"] == "1.00"
    assert not any(d["campo"] == "p1:zapata_muro_lindero:Df" for d in _dudas(pid))


def test_la_mesa_lista_las_dudas_de_obra_y_las_no_confirmables_solo_guardan_la_respuesta(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_planta_basica), {"losa_tipo": {"L1": "A", "L2": "C"}})  # sin E-n ↔ nivel
    _extraer(c, pid)
    dudas = c.get("/api/dudas", params={"proyecto_id": pid, "sin_visita": True}).json()
    obra = next(d for d in dudas if d["campo_afectado"] == "T6n:equivalencia_nivel:NIVEL 2")
    assert obra["id_elemento"] == "(obra)" and obra["campo_confirmable"] is None
    r = c.patch(f"/api/dudas/{obra['id']}", json={"respuesta": "lo cargo en Datos de la obra"})
    assert r.status_code == 200 and r.json()["valor_aplicado"] is None
    assert _auditoria_lote() == []


def test_la_mesa_no_sobrescribe_un_campo_ya_confirmado_con_otro_valor(entorno):
    c = entorno
    pid = _obra(c, _vectorial(_zapata_con_celda_vacia))
    _extraer(c, pid)
    z = _elementos(pid)[('ZAPATA MURO LINDERO 8"', PENDIENTE)]
    datos, estado = json.loads(z["datos_diseno_json"]), json.loads(z["estado_campos_json"])
    datos["Df"], estado["datos_diseno.Df"] = "0.90", CONFIRMADO
    _sql("UPDATE elementos_diseno SET datos_diseno_json = ?, estado_campos_json = ? WHERE uid = ?",
         (json.dumps(datos), json.dumps(estado), z["uid"]))
    d = _sql("SELECT id FROM dudas_y_hallazgos WHERE campo_afectado = 'T6n:p1:zapata_muro_lindero:Df'")[0]
    r = c.patch(f"/api/dudas/{d['id']}", json={"respuesta": "1.00"})
    assert r.status_code == 422 and "no se sobrescribe" in r.json()["detail"]
    assert json.loads(_elementos(pid)[('ZAPATA MURO LINDERO 8"', PENDIENTE)]["datos_diseno_json"])["Df"] == "0.90"


@pytest.mark.parametrize("campo, bueno, malo", [
    ("H", "0.25", "25"), ("DIR. X", '3Ø1/2"', "3 barras"), ("ACERO Ast", 'Ø 3/8" @ 0.15', "3/8 @ 15"),
    ("fc_kgcm2", "280", "280 kg"), ("tipo_losa", None, "A"),
])
def test_validar_valor_usa_las_reglas_de_la_tabla(campo, bueno, malo):
    if bueno is not None:
        assert cf.validar_valor(campo, bueno) == bueno
    with pytest.raises(cf.ValorInvalido):
        cf.validar_valor(campo, malo)
    with pytest.raises(cf.ValorInvalido):
        cf.validar_valor(campo, PENDIENTE)
