# BACKEND/tests/test_validador_diseno.py
# Etapa 2 · T2 — Validador de elementos de diseño (CLAUDE.md §4.1, §4.2, §4.4, §4.5, error #11).
# Convención (Regla de Oro #1): "# SINTÉTICO" = valor inventado solo para probar;
# los EJES de ejemplo son los del CLAUDE.md §4.4. Nada se guarda en la BD.
import pytest

from importadores.validador_diseno import validar_elemento_diseno
from reglas_ingenieria import PENDIENTE


def _elemento(**cambios):
    base = {  # SINTÉTICO: no es dato de proyecto
        "id_elemento": "C1",
        "tipo_elemento": "COLUMNA",
        "nivel_rango": "S-4",
        "ejes": "EJE F-11",  # NORMA: CLAUDE.md §4.4
        "hoja_plano_origen": "ES-05",
        "archivo_plano_origen": "sintetico.pdf",
        "datos_diseno": {"b_m": 0.40, "h_m": 0.60},  # SINTÉTICO
    }
    base.update(cambios)
    return base


def _campos_en_duda(r):
    return {d["campo_afectado"] for d in r["dudas"]}


def test_elemento_completo_no_genera_dudas():
    r = validar_elemento_diseno(_elemento())
    assert r["dudas"] == []
    n = r["elemento_normalizado"]
    assert n["categoria"] == "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A."
    assert n["recubrimiento_por_lado_m"] == 0.040  # NORMA: CLAUDE.md §4.5
    assert n["datos_diseno_json"] == {"b_m": 0.40, "h_m": 0.60}
    assert all(v == "confirmado" for v in r["estado_campos"].values())


@pytest.mark.parametrize("tipo,ejes", [
    ("COLUMNA", "EJE F-11"),                       # NORMA: CLAUDE.md §4.4
    ("MURO H.A.", "EJE D-E,4"),
    ("VIGA HORMIGON", "EJE C, ENTRE 2-3"),
    ("VIGA HORMIGON", "—"),
    ("PORTICO", "EJE F ENTRE 10-11"),
    ("PLATEA", "(A-B),(1-2)"),
    ("COLUMNA", "EJE A'-1"),
    ("LOSA", "—"),
    ("LOSA ALIGERADA", "—"),
])
def test_ejes_validos_por_tipo(tipo, ejes):
    r = validar_elemento_diseno(_elemento(tipo_elemento=tipo, ejes=ejes))
    assert r["dudas"] == []
    assert r["elemento_normalizado"]["ejes"] == ejes


@pytest.mark.parametrize("ejes", ["EJE F-11", "EJE C, ENTRE 2-3", "(A-B),(1-2)", "", "A1"])
def test_losa_con_ejes_distinto_de_guion_es_duda(ejes):
    r = validar_elemento_diseno(_elemento(tipo_elemento="LOSA MACIZA", ejes=ejes))
    assert "ejes" in _campos_en_duda(r)
    assert r["estado_campos"]["ejes"] == "pendiente_de_verificar"


def test_muro_con_fila_es_duda_y_no_se_reformatea():
    r = validar_elemento_diseno(_elemento(tipo_elemento="MURO H.A.", ejes="EJE D-E, FILA 4"))
    assert "ejes" in _campos_en_duda(r)
    assert r["elemento_normalizado"]["ejes"] == "EJE D-E, FILA 4"  # tal cual, sin adivinar


@pytest.mark.parametrize("ejes", ["eje F-11", "EJE F11", "EJE 11-F", "F-11"])
def test_ejes_mal_formados_son_duda(ejes):
    r = validar_elemento_diseno(_elemento(ejes=ejes))
    assert "ejes" in _campos_en_duda(r)


def test_formato_de_otro_tipo_es_duda():
    # Una columna no lleva formato de muro ni de pórtico
    assert "ejes" in _campos_en_duda(
        validar_elemento_diseno(_elemento(tipo_elemento="COLUMNA", ejes="EJE D-E,4")))
    assert "ejes" in _campos_en_duda(
        validar_elemento_diseno(_elemento(tipo_elemento="PORTICO", ejes="EJE F-11")))


@pytest.mark.parametrize("campo", [
    "id_elemento", "tipo_elemento", "nivel_rango", "ejes",
    "hoja_plano_origen", "archivo_plano_origen",
])
def test_falta_campo_obligatorio_queda_pendiente_con_duda(campo):
    datos = _elemento()
    del datos[campo]
    r = validar_elemento_diseno(datos)
    assert r["elemento_normalizado"][campo] == PENDIENTE
    assert r["estado_campos"][campo] == "pendiente_de_verificar"
    assert campo in _campos_en_duda(r)


def test_falta_hoja_plano_origen_no_inventa_valor():
    r = validar_elemento_diseno(_elemento(hoja_plano_origen=None))
    assert r["elemento_normalizado"]["hoja_plano_origen"] == PENDIENTE
    assert len(r["dudas"]) == 1
    assert r["dudas"][0]["categoria"] == "DUDA_BLOQUEANTE"
    assert r["dudas"][0]["id_elemento"] == "C1"


@pytest.mark.parametrize("tipo", ["PERFIL W", "TUBO", "ANGULAR", "CANAL", "METALDECK", "TIPO RARO"])
def test_tipo_metalico_o_desconocido_queda_pendiente(tipo):
    r = validar_elemento_diseno(_elemento(tipo_elemento=tipo))
    assert r["estado_campos"]["tipo_elemento"] == "pendiente_de_verificar"
    assert r["elemento_normalizado"]["categoria"] is None
    assert r["elemento_normalizado"]["recubrimiento_por_lado_m"] is None
    assert "tipo_elemento" in _campos_en_duda(r)


def test_platea_usa_recubrimiento_de_cimentacion():
    r = validar_elemento_diseno(_elemento(tipo_elemento="PLATEA", ejes="(A-B),(1-2)"))
    assert r["elemento_normalizado"]["recubrimiento_por_lado_m"] == 0.075  # NORMA: respuesta de Steven


def test_dato_de_diseno_pendiente_o_ausente():
    r = validar_elemento_diseno(
        _elemento(datos_diseno={"b_m": 0.40, "h_m": PENDIENTE, "acero": None}),  # SINTÉTICO
        campos_esperados=["b_m", "h_m", "acero", "estribos"])
    d = r["elemento_normalizado"]["datos_diseno_json"]
    assert d == {"b_m": 0.40, "h_m": PENDIENTE, "acero": PENDIENTE, "estribos": PENDIENTE}
    assert r["estado_campos"]["datos_diseno.b_m"] == "confirmado"
    for c in ("h_m", "acero", "estribos"):
        assert r["estado_campos"][f"datos_diseno.{c}"] == "pendiente_de_verificar"
        assert f"datos_diseno.{c}" in _campos_en_duda(r)


def test_no_calcula_cuantias_ni_recubrimientos_sumados():
    r = validar_elemento_diseno(_elemento())
    n = r["elemento_normalizado"]
    assert "cuantia" not in n and "cuantia" not in n["datos_diseno_json"]
    assert set(n["datos_diseno_json"]) == {"b_m", "h_m"}  # solo lo que trajo la fuente


def test_no_modifica_la_entrada():
    datos = _elemento()
    copia = {**datos, "datos_diseno": dict(datos["datos_diseno"])}
    validar_elemento_diseno(datos)
    assert datos == copia
