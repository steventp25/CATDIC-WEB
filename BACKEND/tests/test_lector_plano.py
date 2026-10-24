# BACKEND/tests/test_lector_plano.py
# Etapa 2 · T6n-a — Núcleo del lector de planos (PLANES/etapa-2.md, T6n-a).
# Todo # SINTÉTICO: los PDF se generan aquí con PyMuPDF; no se usa ningún plano ni dato real.
from pathlib import Path

import pymupdf
import pytest

from plano import lector_plano as lp
from reglas_ingenieria import PENDIENTE

RAIZ_PLANO = Path(lp.__file__).resolve().parent


def _texto(pag, x, y, t, tam=8.0):
    pag.insert_text((x, y), t, fontsize=tam)


def _guardar(doc, ruta: Path) -> Path:
    doc.save(str(ruta))
    doc.close()
    return ruta


# ---------- Índice de hojas ----------

def test_indice_numero_junto_a_barra_36_y_titulos_bajo_cada_dibujo(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=1200, height=800)
    _texto(pag, 1100, 770, "13", 14)
    _texto(pag, 1116, 770, "/36", 14)
    _texto(pag, 300, 700, "PLANTA ESTRUCTURAL NIVEL 2", 15)
    _texto(pag, 700, 700, "SECCION DE FUNDACIONES A-A'", 15)
    _texto(pag, 100, 100, "una nota pequeña en minusculas", 8)
    _texto(pag, 100, 300, "1/4", 14)  # una fracción del dibujo no es el número de hoja
    h = lp.indice_hojas(_guardar(doc, tmp_path / "p.pdf"))
    assert len(h) == 1 and h[0]["hoja"] == "13" and h[0]["total"] == "36" and h[0]["pagina"] == 1
    assert {t["texto"] for t in h[0]["titulos"]} == {"PLANTA ESTRUCTURAL NIVEL 2", "SECCION DE FUNDACIONES A-A'"}
    assert h[0]["fuente"]["archivo"] == "p.pdf" and h[0]["fuente"]["hoja"] == "13"


def test_indice_hoja_girada_270_usa_la_rotation_matrix(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=1200, height=800)
    _texto(pag, 1100, 770, "37", 14)  # en el marco sin girar, "37" y "/36" van uno junto al otro…
    _texto(pag, 1116, 770, "/36", 14)
    _texto(pag, 300, 700, "PORTICO ESTRUCTURAL EJE A", 15)
    pag.set_rotation(270)               # …y al girar la hoja quedan uno encima del otro
    h = lp.indice_hojas(_guardar(doc, tmp_path / "g.pdf"))[0]
    assert h["rotacion"] == 270 and h["hoja"] == "37" and h["total"] == "36"
    x0, y0, x1, y1 = h["bbox_numero"]
    assert 0 <= x0 < x1 <= 800 and 0 <= y0 < y1 <= 1200  # bbox en el marco visual (la hoja girada es 800 x 1200)
    assert [t["texto"] for t in h["titulos"]] == ["PORTICO ESTRUCTURAL EJE A"]


def test_indice_sin_numero_queda_pendiente_y_no_se_deduce_del_orden(tmp_path):
    doc = pymupdf.open()
    for _ in range(2):
        doc.new_page(width=600, height=400)
    h = lp.indice_hojas(_guardar(doc, tmp_path / "s.pdf"))
    assert [x["hoja"] for x in h] == [PENDIENTE, PENDIENTE]


# ---------- Tablas por posición ----------

def _tabla_losa(pag, x0=1000, y0=200, jitter=None, quitar=(), extra=()):
    """TABLA DE ACERO EN LOSA sintética: 3 filas A/B/C; `jitter` {(fila, col): (dx, dy)}; `quitar` celdas ausentes."""
    jitter = jitter or {}
    _texto(pag, x0, y0, "TABLA DE ACERO EN LOSA", 10)
    cols = {"TIPO DE": 0, "H": 45, "Bw1": 75, "Bw2": 115, "h1": 150, "h2": 185, "DIR. X": 230, "DIR. Y": 290, "AS. ADIC.": 350}
    for c, dx in cols.items():
        _texto(pag, x0 + dx, y0 + 30, c, 8)
    filas = [("A", "0.25", "0.125", "0.156", "0.20", "0.05", '3Ø1/2"', '3Ø1/2"', None),
             ("B", "0.25", "0.125", "0.156", "0.20", "0.05", '2Ø1/2"', '2Ø1/2"', None),
             ("C", "0.25", "0.125", "0.156", "0.20", "0.05", '3Ø3/8"', '3Ø3/8"', '2Ø3/8"')]
    for i, fila in enumerate(filas):
        for j, (c, dx) in enumerate(cols.items()):
            v = fila[j]
            if v is None or (i, c) in quitar:
                continue
            jx, jy = jitter.get((i, c), (0, 0))
            _texto(pag, x0 + dx + jx, y0 + 50 + 17 * i + jy, v, 8)
    for x, y, t in extra:
        _texto(pag, x, y, t, 8)


def test_tabla_losa_con_celdas_desalineadas_3_pt_se_lee_completa(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=1600, height=900)
    desal = {(0, "H"): (3, 3), (0, "Bw2"): (-3, -3), (1, "h1"): (3, -3), (1, "DIR. X"): (-3, 3), (2, "DIR. Y"): (3, 0),
             (2, "AS. ADIC."): (-3, 3)}
    _tabla_losa(pag, jitter=desal)
    t = lp.tabla_acero_losa(_guardar(doc, tmp_path / "t.pdf"), 1)
    assert [f["etiqueta"]["valor"] for f in t["filas"]] == ["A", "B", "C"]
    por = {f["etiqueta"]["valor"]: {c: v["valor"] for c, v in f["celdas"].items()} for f in t["filas"]}
    assert por["A"]["H"] == "0.25" and por["A"]["Bw2"] == "0.156" and por["B"]["h1"] == "0.20"
    assert por["B"]["DIR. X"] == '2Ø1/2"' and por["C"]["DIR. Y"] == '3Ø3/8"' and por["C"]["AS. ADIC."] == '2Ø3/8"'
    assert t["descartadas"] == [] and t["filas"][2]["pendientes"] == []
    # cada celda trae su bbox y la tabla su fuente
    assert t["filas"][0]["celdas"]["H"]["bbox"] and t["fuente"]["pagina"] == 1 and t["tabla"] == "acero_en_losa"


def test_celda_ausente_queda_pendiente_y_no_se_rellena_con_la_del_vecino(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=1600, height=900)
    _tabla_losa(pag, quitar={(1, "Bw1")})
    t = lp.tabla_acero_losa(_guardar(doc, tmp_path / "t.pdf"), 1)
    b = next(f for f in t["filas"] if f["etiqueta"]["valor"] == "B")
    assert b["celdas"]["Bw1"] == {"valor": PENDIENTE, "bbox": None} and "Bw1" in b["pendientes"]
    assert b["celdas"]["Bw2"]["valor"] == "0.156"
    # AS. ADIC. de A y B: no hay valor en el plano → pendiente (no se copia el de C)
    a = next(f for f in t["filas"] if f["etiqueta"]["valor"] == "A")
    assert a["celdas"]["AS. ADIC."]["valor"] == PENDIENTE


def test_celda_que_no_encaja_en_ninguna_columna_se_descarta_con_motivo(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=1600, height=900)
    # un valor entre Bw2 y h1 (a medio camino, fuera de ambas columnas) y otro lejos de toda fila
    _tabla_losa(pag, extra=[(1000 + 132, 200 + 50 + 17, "9.99"), (1000 + 75, 200 + 50 + 17 * 2 + 9, "7.77")])
    t = lp.tabla_acero_losa(_guardar(doc, tmp_path / "t.pdf"), 1)
    motivos = {d["texto"]: d["motivo"] for d in t["descartadas"]}
    assert "9.99" in motivos and "7.77" in motivos
    b = next(f for f in t["filas"] if f["etiqueta"]["valor"] == "B")
    assert "9.99" not in {v["valor"] for v in b["celdas"].values()}


def test_tabla_zapata_lindero_con_un_valor_desplazado_4_pt(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=1600, height=900)
    x0, y0 = 700, 300
    _texto(pag, x0, y0, "TABLA DE APLICACION PARA", 10)
    _texto(pag, x0 + 3, y0 + 12, "ZAPATA DE MURO LINDERO", 10)
    for c, dx in {"MURO": 0, "B": 38, "h": 70, "Df": 100, "ACERO Ast": 130, "ACERO Asl": 190}.items():
        _texto(pag, x0 + dx, y0 + 40, c, 8)
    for i, fila in enumerate([('6"', "0.60", "0.30", "0.80", 'Ø 3/8" @ 0.15', '4 Ø 3/8"'),
                              ('8"', "0.80", "0.30", "1.00", 'Ø 3/8" @ 0.10', '5 Ø 3/8"')]):
        for dx, v, c in zip((0, 38, 70, 100, 130, 190), fila, range(6)):
            _texto(pag, x0 + dx, y0 + 58 + 17 * i + (-4 if (i, c) == (1, 3) else 0), v, 8)  # Df de la 2.ª fila, 4 pt arriba
    t = lp.tabla_zapata_lindero(_guardar(doc, tmp_path / "z.pdf"), 1)
    assert [f["etiqueta"]["valor"] for f in t["filas"]] == ['6"', '8"']
    assert t["filas"][1]["celdas"]["Df"]["valor"] == "1.00" and t["filas"][0]["celdas"]["Df"]["valor"] == "0.80"
    assert t["filas"][1]["celdas"]["ACERO Asl"]["valor"] == '5 Ø 3/8"' and t["descartadas"] == []


def test_fc_por_rango_literal_y_valor_sin_rango_queda_descartado(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=1600, height=900)
    _texto(pag, 1200, 700, "CONCRETO F'c", 8)
    for i, (rg, v) in enumerate([("FUND.@ E3", "350 Kg/cm2"), ("E3 @ E10", "350 Kg/cm2"), ("E10 @ E16", "280 Kg/cm2"),
                                 (None, "240 Kg/cm2")]):
        if rg:
            _texto(pag, 1190, 720 + 11 * i, rg, 8)
        _texto(pag, 1250, 720 + 11 * i + (2 if i == 1 else 0), v, 8)
    t = lp.tabla_fc_por_rango(_guardar(doc, tmp_path / "f.pdf"), 1)
    assert [(f["rango"]["valor"], f["fc_kgcm2"]["valor"]) for f in t["filas"]] == [
        ("FUND.@ E3", "350"), ("E3 @ E10", "350"), ("E10 @ E16", "280")]
    assert [d["texto"] for d in t["descartadas"]] == ["240 Kg/cm2"]  # sin rango: no se le pone el del vecino
    assert (t["filas"][0]["desde"], t["filas"][0]["hasta"]) == ("FUND.", "E3")  # el rango no se expande ni se traduce


def test_pagina_sin_la_tabla_devuelve_none(tmp_path):
    doc = pymupdf.open()
    doc.new_page(width=600, height=400)
    ruta = _guardar(doc, tmp_path / "v.pdf")
    assert lp.tabla_acero_losa(ruta, 1) is None and lp.tabla_zapata_lindero(ruta, 1) is None
    assert lp.tabla_fc_por_rango(ruta, 1) is None


# ---------- Globos de eje ----------

def _globo(pag, cx, cy, t, r=9.5):
    pag.draw_circle((cx, cy), r, color=(0, 0, 0), width=0.7)
    pag.insert_text((cx - 3 * len(t), cy + 3), t, fontsize=9)


def test_globos_de_eje_solo_circulos_alineados_con_rotulos_distintos(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=1200, height=900)
    for i, t in enumerate(["A", "B", "C", "D"]):   # fila de letras abajo
        _globo(pag, 300 + 120 * i, 850, t)
    for i, t in enumerate(["1", "2", "3"]):        # columna de números a la izquierda
        _globo(pag, 100, 300 + 130 * i, t)
    for x in (400, 520, 640):                      # marcas de apoyo: la MISMA "A" en círculos más chicos, alineadas
        _globo(pag, x, 200, "A", r=7.6)
    pag.insert_text((700, 500), "A", fontsize=9)   # una "A" suelta, sin círculo
    pag.insert_text((710, 520), "B", fontsize=9)
    _globo(pag, 900, 300, "L8")                    # ID de losa circulado: no es un eje
    _globo(pag, 900, 400, "L6")
    g = lp.globos_de_eje(_guardar(doc, tmp_path / "g.pdf"), 1)
    assert sorted(x["texto"] for x in g if x["orientacion"] == "fila") == ["A", "B", "C", "D"]
    assert sorted(x["texto"] for x in g if x["orientacion"] == "columna") == ["1", "2", "3"]
    assert len(g) == 7 and all(x["diametro"] == 19.0 for x in g)   # ninguna "A" de apoyo, ninguna suelta, ningún L#
    assert all(x["confianza"] == "media" and x["fuente"]["pagina"] == 1 for x in g)  # capa sin nombre "EJE"


def test_una_letra_repetida_en_circulos_alineados_no_es_un_eje(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=800, height=600)
    for x in (100, 200, 300):
        _globo(pag, x, 100, "A")
    assert lp.globos_de_eje(_guardar(doc, tmp_path / "r.pdf"), 1) == []


# ---------- IDs, notas, rótulos de sección ----------

def test_ids_en_planta_con_bbox_sin_cruce_de_ejes(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=800, height=600)
    for i, t in enumerate(["C5", "L13", "MH3", "V-40X60", "H=0.25M", "ESCALERA #1", "A", "1"]):
        _texto(pag, 100 + 70 * i, 200, t, 8)
    ids = lp.ids_en_planta(_guardar(doc, tmp_path / "i.pdf"), 1)
    assert [(i["texto"], i["tipo"]) for i in ids] == [("C5", "columna"), ("L13", "losa"), ("MH3", "muro"),
                                                      ("V-40X60", "viga")]
    assert all(len(i["bbox"]) == 4 and "cruce" not in i and "ejes" not in i for i in ids)


def test_nota_de_modificacion_partida_en_tres_lineas_se_une_y_se_detecta(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=800, height=600)
    lineas = ["NOTA ESTRUCTURAL: LA LOSA ENTRE LOS NIVELES NPT = -19.05 Y NPT = -17.75 SE",
              "MODIFICO, SUSTITUYENDO LA LOSA APOYADA SOBRE RELLENO POR UNA LOSA ALIGERADA, EN",
              "REEMPLAZO DE LA SOLUCION INDICADA EN EL PLANO ANTERIOR APROBADO."]
    for i, l in enumerate(lineas):
        _texto(pag, 100, 100 + 12 * i, l, 10)
    _texto(pag, 100, 300, "NOTA EMPALME EN VIGAS: SE DEBEN TRASLAPAR LAS BARRAS EN LA ZONA CENTRAL.", 10)
    n = lp.notas_de_modificacion(_guardar(doc, tmp_path / "n.pdf"), 1)
    assert len(n) == 1 and n[0]["lineas"] == 3
    assert set(n[0]["claves"]) == {"se_modifico", "en_reemplazo", "plano_anterior"}
    assert "SE MODIFICO, SUSTITUYENDO" in n[0]["texto"] and n[0]["fuente"]["pagina"] == 1


def test_rotulos_de_seccion_llevan_la_hoja_en_su_clave(tmp_path):
    doc = pymupdf.open()
    for hoja in ("05", "06"):
        pag = doc.new_page(width=800, height=600)
        _texto(pag, 700, 570, hoja, 14)
        _texto(pag, 716, 570, "/36", 14)
        _texto(pag, 100, 100, "S-1", 9)
        _texto(pag, 200, 100, "S-1'", 9)
        _texto(pag, 300, 100, "SECCION DE ALGO", 9)
    ruta = _guardar(doc, tmp_path / "s.pdf")
    assert [r["clave"] for r in lp.rotulos_de_seccion(ruta, 1)] == ["05:S-1", "05:S-1'"]
    assert [r["clave"] for r in lp.rotulos_de_seccion(ruta, 2)] == ["06:S-1", "06:S-1'"]  # mismo S-1, otra hoja


# ---------- Pureza ----------

def test_el_lector_es_puro_no_importa_la_bd_ni_escribe():
    fuente = (RAIZ_PLANO / "lector_plano.py").read_text(encoding="utf-8")
    for prohibido in ("sqlite3", "import database", "from database", "get_connection", ".write(", ".save("):
        assert prohibido not in fuente, prohibido


def test_el_lector_no_modifica_el_pdf(tmp_path):
    doc = pymupdf.open()
    pag = doc.new_page(width=600, height=400)
    _texto(pag, 500, 380, "01", 14)
    _texto(pag, 516, 380, "/36", 14)
    ruta = _guardar(doc, tmp_path / "m.pdf")
    antes = ruta.read_bytes()
    lp.indice_hojas(ruta)
    lp.ids_en_planta(ruta, 1)
    lp.globos_de_eje(ruta, 1)
    assert ruta.read_bytes() == antes
