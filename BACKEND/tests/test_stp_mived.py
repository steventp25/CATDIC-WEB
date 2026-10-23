# BACKEND/tests/test_stp_mived.py
# Etapa 3 · T7 — Generador STP-MIVED (PLANES/etapa-3.md, T7; CLAUDE.md §3.2, §4.5–§4.7, §5.2).
# Todo # SINTÉTICO: proyecto, visita, planos y fotos se crean en la prueba; no se usa ningún dato real.
import copy
import io
import re
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

import config
import database
from generators import stp_mived
from generators.comun import salida  # noqa: F401  (se importa para que falle claro si falta T6)
from reglas_ingenieria import PENDIENTE, calcular_cuantia_elemento

RAIZ_GENERADORES = Path(stp_mived.__file__).resolve().parent


# ---------- Material sintético ----------

def _plano_pdf(ruta: Path):
    doc = pymupdf.open()
    hoja = doc.new_page(width=612, height=792)
    hoja.draw_rect(pymupdf.Rect(10, 10, 60, 60), color=(1, 0, 0), fill=(1, 0, 0))
    hoja.insert_text((100, 400), "PLANTA SINTETICO", fontsize=24)
    doc.save(str(ruta))
    doc.close()


def _foto(ruta: Path, color, tam=(640, 480)):
    Image.new("RGB", tam, color).save(ruta, format="JPEG")
    return str(ruta)


def _proyecto(carpeta_planos: Path) -> dict:
    return {"nombre": "Proyecto Sintetico", "no_solicitud": "SOL-SINT", "no_licencia": "LIC-SINT",
            "direccion_obra": "CALLE SINTETICA 1", "provincia": "PROVINCIA SINT", "sector": "SECTOR SINT",
            "residente_obra": "RESIDENTE SINT 0000", "carpeta_planos": str(carpeta_planos)}


def _visita(**cambios) -> dict:
    v = {"id": "visita-sint", "fecha": "15/10/2026", "clase": "Parcial", "elementos_txt": "VIGAS Y LOSAS SINT"}
    v.update(cambios)
    return v


class Mundo:
    """Archivos sintéticos compartidos por las pruebas."""

    def __init__(self, base: Path):
        self.planos = base / "planos"
        self.planos.mkdir()
        self.pdf_plano = self.planos / "plano.pdf"
        _plano_pdf(self.pdf_plano)
        fotos = base / "fotos"
        fotos.mkdir()
        self.fotos = [_foto(fotos / f"f{i}.jpg", c) for i, c in enumerate(
            [(200, 40, 40), (40, 200, 40), (40, 40, 200), (200, 200, 40)])]

    def ficha_viga(self, **cambios) -> dict:
        f = {"titulo": "VIGA HORMIGON-VS1-EJE X ENTRE 1-2", "tipo_elemento": "VIGA HORMIGON", "ejes": "EJE C, ENTRE 2-3",
             "plano": {"b": "350", "e": "3.17", "f": 'Ø3/8"@0.10', "g": 'Ø3/8"@0.20', "h": 'Ø3/8"', "i": '3-Ø3/4"',
                       "j": '3-Ø3/4"', "k": "-", "m": "-"},
             "obra": {"b": "350", "e": "3.17", "f": 'Ø3/8"@0.10', "g": 'Ø3/8"@0.20', "h": 'Ø3/8"', "i": '3-Ø3/4"',
                      "j": '3-Ø3/4"'},
             "medidas": {"c": {"valor_plano_m": 0.40, "medida_acero_campo_m": 0.32},
                         "d": {"valor_plano_m": 0.60, "medida_acero_campo_m": 0.52}},
             "barras": [(3, '3/4"'), (3, '3/4"')],
             "fotos": self.fotos[:2],
             "localizacion": {"pdf": str(self.pdf_plano), "pagina": 0, "caja": (100, 100, 600, 500)},
             "detalle": {"pdf": str(self.pdf_plano), "pagina": 0, "region": (0, 0, 300, 200)}}
        f.update(cambios)
        return f

    def ficha_losa(self, **cambios) -> dict:
        f = {"titulo": "LOSA NERVADA-LS1", "tipo_elemento": "LOSA ALIGERADA", "ejes": "—",
             "plano": {"a": "350", "e": "SI", "h": "MALLA SINT", "i": '2-Ø1/2"', "n": '2-Ø1/2"'},
             "obra": {"a": "350", "e": "SI", "h": "MALLA SINT", "i": '2-Ø1/2"', "n": '2-Ø1/2"'},
             "medidas": {"b": {"valor_plano_m": 0.25, "medida_acero_campo_m": 0.20}},
             "fotos": self.fotos[:3],
             "localizacion": {"pdf": str(self.pdf_plano), "pagina": 0, "caja": (100, 100, 600, 500)},
             "detalle": {"pdf": str(self.pdf_plano), "pagina": 0, "region": (0, 0, 300, 200)}}
        f.update(cambios)
        return f


@pytest.fixture(scope="module")
def mundo(tmp_path_factory):
    return Mundo(tmp_path_factory.mktemp("mundo"))


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    (tmp_path / "bd").mkdir()
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "bd" / "prueba.db"))
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "dropbox"))
    monkeypatch.setenv(config.ENV_SALIDA_PRUEBAS, str(tmp_path / "salida"))
    database.inicializar_bd()
    return tmp_path


def _textos(ruta: Path):
    doc = pymupdf.open(str(ruta))
    try:
        return [p.get_text() for p in doc]
    finally:
        doc.close()


def _generar(mundo, entorno, fichas=None, proyecto=None, visita=None):
    return stp_mived.generar_stp_mived(
        proyecto or _proyecto(mundo.planos), visita or _visita(),
        fichas if fichas is not None else [mundo.ficha_viga(), mundo.ficha_losa()], usuario="prueba")


# ---------- Estructura del documento ----------

def test_orden_de_hojas_numeracion_y_rotulos_literales(mundo, entorno):
    r = _generar(mundo, entorno)
    assert r["ok"] and not r["errores"], r
    textos = _textos(r["ruta"])
    assert len(textos) == 2 + 2 * 2  # portada, inspección y 2 hojas por elemento
    portada, insp, cmp1, fot1, cmp2, fot2 = textos
    # Portada e inspección sin número de página en el pie
    assert "Proyecto" in portada and "Fecha de Inspeccion" in portada
    assert "No. DE LA INSPECCION" in insp and "NOMBRE Y FIRMAS DE LOS INSPECTORES" in insp
    for t in (portada, insp):
        assert not re.search(r"(?m)^\d+$", t)
    # 1..n en el pie de las hojas por elemento; a la izquierda el nombre del proyecto
    for t, n in ((cmp1, 1), (fot1, 2), (cmp2, 3), (fot2, 4)):
        assert re.search(rf"(?m)^{n}$", t) and "PROYECTO SINTETICO" in t
    # Rótulos literales del formato original (con su ortografía)
    assert "IMAGEN DE PLANOS APROVADOS DTTL" in cmp1 and "IMAGEN EN OBRA" in cmp1
    assert "INFORMACION ARMADO EN PLANOS" in cmp1 and "IMFORMACION ARMADO EN OBRA" in cmp1
    assert "1.i. Barras Top:" in cmp1 and "2.i. Barras Top:" in cmp1
    assert "1.a. RESISTENCIA ESPERADA:" in cmp2 and "2.a.RESISTENCIA OBTENIDA:" in cmp2
    assert "VIGA HORMIGON-VS1-EJE X ENTRE 1-2" in fot1 and "LOSA NERVADA-LS1" in fot2
    # Cabecera con los datos del proyecto que se pasaron
    for dato in ("SOL-SINT", "LIC-SINT", "CALLE SINTETICA 1", "15/10/2026"):
        assert dato in cmp1
    for dato in ("PROVINCIA SINT", "SECTOR SINT", "RESIDENTE SINT 0000", "VIGAS Y LOSAS SINT - PARCIAL"):
        assert dato in insp


def test_nombre_de_salida_y_version_nueva_sin_sobrescribir(mundo, entorno):
    r1 = _generar(mundo, entorno)
    r2 = _generar(mundo, entorno)
    assert r1["ruta"].name == "Proyecto Sintetico - STP - Vigas Y Losas Sint Parcial - 15-10-2026.pdf"
    assert r2["ruta"].name.endswith("15-10-2026 v2.pdf") and r2["version_nueva"]
    assert r1["ruta"].read_bytes() != b"" and r1["ruta"].stat().st_size < 30_000_000


def test_fotos_de_1_a_4_generan_y_la_hoja_fotografica_existe(mundo, entorno):
    for n in (1, 3, 4):
        r = _generar(mundo, entorno, [mundo.ficha_losa(fotos=mundo.fotos[:n])])
        assert r["ok"], (n, r)
        assert len(_textos(r["ruta"])) == 4


# ---------- Reglas: lo ausente no se inventa ----------

def test_valor_de_diseno_ausente_no_genera_y_crea_duda(mundo, entorno):
    ficha = mundo.ficha_viga()
    del ficha["plano"]["i"]
    r = _generar(mundo, entorno, [ficha])
    assert not r["ok"] and r["ruta"] is None
    assert any(d["campo_afectado"] == "plano.i" and d["id_elemento"] == ficha["titulo"] for d in r["dudas"])
    assert PENDIENTE in r["dudas"][0]["descripcion_pregunta"]
    assert not (entorno / "salida").exists()  # no se escribió nada


def test_dimension_del_plano_ausente_no_genera(mundo, entorno):
    ficha = mundo.ficha_viga()
    del ficha["medidas"]["d"]
    r = _generar(mundo, entorno, [ficha])
    assert not r["ok"] and any(d["campo_afectado"] == "medidas.d" for d in r["dudas"])


@pytest.mark.parametrize("campo", ["nombre", "no_solicitud", "no_licencia", "direccion_obra", "provincia",
                                   "sector", "residente_obra", "carpeta_planos"])
def test_cabecera_vacia_es_pendiente_con_error_y_no_genera(mundo, entorno, campo):
    proyecto = _proyecto(mundo.planos)
    proyecto[campo] = ""
    r = _generar(mundo, entorno, proyecto=proyecto)
    assert not r["ok"] and r["ruta"] is None
    assert any(d["campo_afectado"] == f"proyecto.{campo}" and PENDIENTE in d["descripcion_pregunta"]
               for d in r["dudas"])
    proyecto[campo] = PENDIENTE  # el texto "pendiente de verificar" tampoco vale
    assert not _generar(mundo, entorno, proyecto=proyecto)["ok"]


@pytest.mark.parametrize("fecha", ["2026-10-15", "5/3/2026", "31/02/2026", ""])
def test_fecha_solo_en_dd_mm_aaaa(mundo, entorno, fecha):
    r = _generar(mundo, entorno, visita=_visita(fecha=fecha))
    assert not r["ok"] and any(d["campo_afectado"] == "visita.fecha" for d in r["dudas"])


def test_tipo_no_soportado_queda_pendiente(mundo, entorno):
    r = _generar(mundo, entorno, [mundo.ficha_losa(titulo="ZAPATA-Z1", tipo_elemento="ZAPATA AISLADA",
                                                    ejes="EJE F-11")])
    assert not r["ok"] and any(d["campo_afectado"] == "tipo_elemento" for d in r["dudas"])


def test_losa_con_ejes_distintos_de_guion_lo_bloquea_el_auditor(mundo, entorno):
    r = _generar(mundo, entorno, [mundo.ficha_losa(ejes="EJE A-1")])
    assert not r["ok"] and any("Error #11" in e for e in r["errores"])


def test_fila_de_obra_sin_dato_queda_vacia_con_duda_que_no_bloquea(mundo, entorno):
    ficha = mundo.ficha_viga()
    del ficha["obra"]["i"]
    r = _generar(mundo, entorno, [ficha])
    assert r["ok"]
    assert any(d["campo_afectado"] == "obra.i" and d["bloquea"] is False for d in r["dudas"])


# ---------- Cálculos del motor ----------

def test_cuantia_recalculada_en_decimal_y_no_se_puede_copiar(mundo, entorno):
    esperado = f"{calcular_cuantia_elemento(0.40, 0.60, [(3, '3/4\"'), (3, '3/4\"')]):.4f}"
    ficha = mundo.ficha_viga()
    ficha["plano"]["p"] = "0.9999"  # un valor copiado de otro informe NO se usa
    r = _generar(mundo, entorno, [ficha])
    assert r["ok"]
    cmp1 = _textos(r["ruta"])[2]
    assert esperado in cmp1 and "0.9999" not in cmp1
    assert esperado == "0.0071"


def test_columna_obra_corregida_por_recubrimiento_y_conformidad_de_la_inspeccion(mundo, entorno):
    # 0.32 + 2*0.04 = 0.40 -> conforme: OBRA lleva el valor del plano
    r = _generar(mundo, entorno)
    insp = _textos(r["ruta"])[1]
    assert "ACORDE A PLANOS APROBADOS" in insp and r["discrepancias"] == []
    # medida que no cuadra -> la columna OBRA lleva la medida corregida y NO va la conformidad
    ficha = mundo.ficha_viga()
    ficha["medidas"]["c"]["medida_acero_campo_m"] = 0.28  # 0.28 + 0.08 = 0.36
    r2 = _generar(mundo, entorno, [ficha])
    assert r2["ok"] and len(r2["discrepancias"]) == 1
    textos = _textos(r2["ruta"])
    assert "0.36" in textos[2] and "ACORDE A PLANOS APROBADOS" not in textos[1]
    assert "DISCREPANCIAS ABIERTAS" in textos[1]


def test_discrepancia_abierta_de_la_visita_quita_la_conformidad(mundo, entorno):
    r = _generar(mundo, entorno, visita=_visita(discrepancias_abiertas=["C1: falta estribo en nudo"]))
    insp = _textos(r["ruta"])[1]
    assert "ACORDE A PLANOS APROBADOS" not in insp and "falta estribo en nudo" in insp


# ---------- Ningún dato fijo de otro proyecto ----------

CADENAS_PROHIBIDAS = ["TERRA", "VUC2037", "AYBAR", "CASTELLANOS", "VERGEL", "JAVIER", "48605", "DISTRITO NACIONAL",
                      "SOTANO S3", "PROYECTO P16", "ZOETRY"]


@pytest.mark.parametrize("archivo", [RAIZ_GENERADORES / "stp_mived.py",
                                     RAIZ_GENERADORES / "plantillas" / "stp_mived.css"])
def test_ninguna_cadena_fija_de_terra_living_en_el_generador(archivo):
    contenido = archivo.read_text(encoding="utf-8").upper()
    for cadena in CADENAS_PROHIBIDAS:
        assert cadena not in contenido, f"{cadena} en {archivo.name}"


def test_el_generador_no_importa_la_bd():
    fuente = (RAIZ_GENERADORES / "stp_mived.py").read_text(encoding="utf-8")
    assert "get_connection" not in fuente and "sqlite3" not in fuente
