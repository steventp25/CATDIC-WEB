# BACKEND/tests/test_fi_mived.py
# Etapa 3 · T8 — Actualizador de los FI-01/02/03 (PLANES/etapa-3.md, T8; CLAUDE.md §3.2; errores #15–#18).
# Los FI sintéticos reproducen la GEOMETRÍA medida en el reconocimiento de T0b (rótulo "Nivel a inspeccionar"
# en la línea base 130,1; "Fecha" en 401,3; filas con "Sí" en x≈525 y su caja de ≈48×9 pt en x≈505; sección
# de Observaciones y de firmas en la última hoja; firma = anotación Square). Todo # SINTÉTICO.
import hashlib
import io
import re
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

import config
import database
from generators import fi_mived
from generators.fi_mived import FILAS_SI

RAIZ = Path(fi_mived.__file__).resolve().parent
NIVEL = "LOSAS Y VIGAS ENTREPISO SOTANO -4"  # SINTÉTICO


def _png_caja() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (405, 77), (230, 230, 230)).save(buf, format="PNG")
    return buf.getvalue()


EXTRA_NO_MARCAR = {
    "FI-01": ["2a", "3a", "5a", "6a"],
    "FI-02": ["3a", "8a", "8b", "8c", "8d", "9a", "9b", "9c", "9d"],  # 8-9: dinteles (solo si la visita los trae)
    "FI-03": ["3a", "8a", "8b", "8c", "8d", "8e", "8f", "8g", "9a", "9b", "9c"],  # 8: mampostería; 9: cerramiento
}


ROTULOS_CABECERA = [  # (rótulo, x del rótulo, base, clave, x del valor, base del valor) medidos en los FI
    ("Nombre del proyecto", 19.0, 116.2, "nombre", 123.1, 115.9),
    ("Licencia No.", 438.9, 116.2, "no_licencia", 505.0, 113.2),
    ("Sol. Licencia No.", 421.0, 130.1, "no_solicitud", 505.0, 130.0),
    ("Encargado de obra", 16.7, 144.0, "residente_obra", 132.2, 142.6),
    ("Dirección", 16.7, 157.9, "direccion_obra", 119.8, 157.1),
]


def crear_fi(ruta: Path, tipo: str, nivel: str = "", fecha: str = "", obs=(), omitir=(), firmas=True,
             anotacion=True, cabecera=None, sin_caja=(), fechas_aut=("llena", "libre"), tabla=False,
             y_filas=(789.9, 809.9, 829.9), hoja_siguiente=False, vacias=0, rayas_obs=False) -> Path:
    """FI sintético: filas con 'Sí'/'No' y su caja en las hojas 1..n-1; observaciones y firmas en la última."""
    doc = pymupdf.open()
    codigos = sorted(FILAS_SI[tipo] | set(EXTRA_NO_MARCAR[tipo]), key=lambda c: (int(re.match(r"\d+", c).group()), c))
    codigos = [c for c in codigos if c not in omitir]
    por_hoja = 20
    hojas = [codigos[i:i + por_hoja] for i in range(0, len(codigos), por_hoja)]
    png = _png_caja()
    for n, grupo in enumerate(hojas):
        pag = doc.new_page(width=595.32, height=841.92)
        pag.insert_text((223.4, 35.5), "FORMULARIO INSPECCION", fontsize=13)
        if n == 0:
            pag.insert_text((16.7, 130.1), "Nivel a inspeccionar", fontsize=10.6)
            pag.insert_text((401.3, 144.0), "Fecha", fontsize=10.6)
            for rotulo, xr, yr, clave, xv, yv in ROTULOS_CABECERA:
                pag.insert_text((xr, yr), rotulo, fontsize=10.6)
                if cabecera and cabecera.get(clave):
                    pag.insert_text((xv, yv), cabecera[clave], fontsize=10.6)
            if nivel:
                pag.insert_text((132.2, 130.0), nivel, fontsize=10.6)
            if fecha:
                pag.insert_text((487.0, 144.7), fecha, fontsize=10.6)
            else:
                for x, t in ((477.6, "dd"), (498.8, "/"), (511.8, "mm"), (535.9, "/"), (551.0, "aaaa")):
                    pag.insert_text((x, 144.1), t, fontsize=10.6)
        y = 190.0 if n == 0 else 100.0
        for i, c in enumerate(grupo):
            pag.insert_text((16.7, y + 10), f"{c}. Texto de la fila {c} segun planos aprobados", fontsize=10.6)
            if i % 7 == 3:  # un rótulo de dos líneas: la fila de "Sí" cae junto a la primera línea
                pag.insert_text((16.7, y + 24), "continuacion del rotulo", fontsize=10.6)
                paso = 40
            else:
                paso = 27
            pag.insert_text((524.9, y + 10), "Sí", fontsize=10.6)
            pag.insert_text((564.6, y + 10), "No", fontsize=10.6)
            if c not in sin_caja:  # la fila 7c del FI-02 real no trae caja propia
                pag.insert_image(pymupdf.Rect(505.3, y + 2.6, 553.9, y + 11.8), stream=png)
            y += paso
    pag = doc.new_page(width=595.32, height=841.92)
    pag.insert_text((194.6, 484.8), "13. OBSERVACIONES", fontsize=10.6, fontname="hebo")
    for i, linea in enumerate(obs):
        pag.insert_text((26.8, 502.6 + i * 15.8), linea, fontsize=10.6)
    pag.insert_text((185.8, y_filas[0] - 36.2), "14. NOMBRES Y FIRMAS", fontsize=10.6, fontname="hebo")
    pag.insert_text((298.7, y_filas[0] - 15.7), "Firma", fontsize=10.6)
    if firmas:
        # Filas de autorización: "llena" (con cifras), "libre" (con el dd / mm / aaaa impreso) o "vacia" (solo barras)
        for y_base, estado in zip(y_filas, fechas_aut):
            pag.insert_text((176.5, y_base), "NOMBRE SINT", fontsize=10.6)
            pag.insert_text((487.6, y_base), "/ ", fontsize=10.6)
            pag.insert_text((518.5, y_base), "/ ", fontsize=10.6)
            if estado == "llena":
                for x, t in ((466.7, "02"), (500.6, "10"), (540.2, "2026")):
                    pag.insert_text((x, y_base), t, fontsize=10.6)
            elif estado == "libre":
                for x, t in ((473.2, "dd"), (506.6, "mm"), (546.4, "aaaa")):
                    pag.insert_text((x, y_base), t, fontsize=10.6)
    if tabla and firmas:
        # Tabla de firmas: una línea fina bajo cada fila, borde inferior grueso y verticales hasta el borde
        filas_y = list(y_filas[:len(fechas_aut)])
        filas_y += [filas_y[-1] + 20.0 * (k + 1) for k in range(vacias)]  # filas vacías del bloque de inspectores
        arriba = filas_y[0] - 14
        fondo_y = filas_y[-1] + 5
        for i, y_base in enumerate(filas_y[:-1]):
            # con filas vacías, desde la última fecha hay celda combinada "Inspectores": las rayas arrancan en x=163.3
            x0 = 163.3 if vacias and i >= len(fechas_aut) - 1 else 16.0
            pag.draw_rect(pymupdf.Rect(x0, y_base + 5, 578.3, y_base + 5.9), color=None, fill=(0, 0, 0))
        pag.draw_rect(pymupdf.Rect(16.0, fondo_y, 580.1, fondo_y + 1.8), color=None, fill=(0, 0, 0))
        for x0, x1 in ((14.2, 16.0), (162.4, 163.3), (304.2, 305.2), (403.2, 404.2), (468.1, 469.1), (578.3, 580.1)):
            pag.draw_rect(pymupdf.Rect(x0, arriba, x1, fondo_y), color=None, fill=(0, 0, 0))
    if anotacion:
        a = pag.add_rect_annot(pymupdf.Rect(329.6, 796.5, 365.8, 816.2))
        a.set_info(title="Inspector")
        a.update()
    if rayas_obs:  # rayas de la tabla de observaciones: una bajo cada renglón
        for i in range(9):
            pag.draw_rect(pymupdf.Rect(16.0, 506.6 + i * 15.8, 578.3, 507.5 + i * 15.8), color=None, fill=(0, 0, 0))
    if hoja_siguiente:
        doc.new_page(width=595.32, height=841.92)
    doc.save(str(ruta))
    doc.close()
    return ruta


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    (tmp_path / "bd").mkdir()
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "bd" / "prueba.db"))
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "dropbox"))
    monkeypatch.setenv(config.ENV_SALIDA_PRUEBAS, str(tmp_path / "salida"))
    database.inicializar_bd()
    return tmp_path


PROYECTO = {"nombre": "Proyecto Sintetico", "no_licencia": "LIC-SINT", "no_solicitud": "SOL-SINT",
            "residente_obra": "RESIDENTE SINT", "direccion_obra": "CALLE SINTETICA 1"}  # SINTÉTICO


def _visita(**cambios):
    v = {"id": "visita-sint", "fecha": "15/10/2026", "clase": "Parcial"}
    v.update(cambios)
    return v


def _llamar(entorno, tipo="FI-02", **kw):
    args = dict(tipo_fi=tipo, proyecto=PROYECTO, visita=_visita(), nivel_txt=NIVEL, nivel_clave="SOTANO -4",
                elementos=["L1", "L2", "pórticos de los ejes A y B"], usuario="prueba")
    args.update(kw)
    return fi_mived.actualizar_fi(**args)


def _marcas(ruta: Path):
    doc = pymupdf.open(str(ruta))
    try:
        return [(i, d["rect"]) for i, p in enumerate(doc) for d in p.get_drawings()
                if d["rect"].x0 > 480 and d["rect"].width < 20 and d["rect"].height < 20 and d["rect"].y0 > 90
                and d.get("color") is not None and d.get("fill") is None]  # trazos, no los rellenos de redacción
    finally:
        doc.close()


def _texto(ruta: Path) -> str:
    doc = pymupdf.open(str(ruta))
    try:
        return fi_mived.limpiar_extraido("\n".join(p.get_text() for p in doc))
    finally:
        doc.close()


def _hash(ruta: Path) -> str:
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


# ---------- Actualizar un FI existente ----------

@pytest.fixture
def existente(entorno):
    return crear_fi(entorno / "FI-02-existente.pdf", "FI-02", nivel=NIVEL, fecha="05/10/2026",
                    obs=["Observacion anterior UNO de otra visita.", "Observacion anterior DOS."])


def test_agrega_la_visita_sin_borrar_las_observaciones_anteriores(entorno, existente):
    r = _llamar(entorno, existente=existente)
    assert r["ok"], r
    texto = _texto(r["ruta"])
    assert "Observacion anterior UNO de otra visita." in texto and "Observacion anterior DOS." in texto
    assert "15/10/2026 - PARCIAL: Se supervisaron L1, L2, pórticos de los ejes A y B." in " ".join(texto.split())
    # La visita nueva va DEBAJO de las anteriores
    doc = pymupdf.open(str(r["ruta"]))
    ultima = doc[-1]
    palabras = ultima.get_text("words")
    y_ant = next(w[1] for w in palabras if w[4] == "DOS.")
    y_nueva = next(w[1] for w in palabras if w[4].strip("\u00a0") == "PARCIAL:")
    assert y_nueva > y_ant
    # Nivel y fecha nuevos; la fecha vieja ya no está
    p1 = fi_mived.limpiar_extraido(doc[0].get_text())
    assert NIVEL in p1 and "15/10/2026" in p1 and "05/10/2026" not in p1
    doc.close()


def test_el_original_no_se_toca_y_la_version_nueva_no_sobrescribe_error_15(entorno, existente):
    antes = _hash(existente)
    r1 = _llamar(entorno, existente=existente)
    r2 = _llamar(entorno, existente=existente)
    assert _hash(existente) == antes  # el FI de partida queda intacto
    assert r1["ruta"].name == "MIVED - PROYECTO SINTETICO-LOSAS Y VIGAS ENTREPISO SOTANO -4.PDF"
    assert r2["ruta"].name.endswith("SOTANO -4 v2.PDF") and r2["version_nueva"]
    assert r1["ruta"].exists() and r1["ruta"] != r2["ruta"]


def test_la_firma_se_elimina_error_16(entorno, existente):
    doc = pymupdf.open(str(existente))
    assert sum(len(list(p.annots() or [])) for p in doc) == 1
    imagenes_antes = sum(len(p.get_images()) for p in doc)
    doc.close()
    r = _llamar(entorno, existente=existente)
    out = pymupdf.open(str(r["ruta"]))
    assert sum(len(list(p.annots() or [])) for p in out) == 0
    assert sum(len(p.get_images()) for p in out) == imagenes_antes  # no se inserta ninguna firma ni imagen
    out.close()
    assert r["avisos"] and "anotaciones" in " ".join(r["avisos"])


@pytest.mark.parametrize("tipo", ["FI-01", "FI-02", "FI-03"])
def test_marca_los_si_obligatorios_y_nunca_mamposteria_ni_dinteles_error_17(entorno, tipo):
    base = crear_fi(entorno / f"{tipo}.pdf", tipo, nivel=NIVEL, obs=["Anterior."])
    assert _marcas(base) == []
    r = _llamar(entorno, tipo=tipo, existente=base)
    assert r["ok"], r
    marcas = _marcas(r["ruta"])
    assert len(marcas) == len(FILAS_SI[tipo]) == r["marcas"]
    # Cada marca es un cuadro de 12x12 pt
    assert all(abs(m.width - 12) < 3 and abs(m.height - 12) < 3 for _, m in marcas)
    # Ninguna marca en las filas prohibidas (mampostería / dinteles / no marcables) ni en la columna del "No"
    doc = pymupdf.open(str(r["ruta"]))
    prohibidas_y = []
    for i, p in enumerate(doc):
        for s in [s for b in p.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]]:
            m = re.match(r"^(\d{1,2}[a-z])\.", s["text"])
            if m and m.group(1) in EXTRA_NO_MARCAR[tipo]:
                prohibidas_y.append((i, s["bbox"][1], s["bbox"][3]))
    doc.close()
    assert prohibidas_y
    for pagina, y0, y1 in prohibidas_y:
        assert not [m for i, m in marcas if i == pagina and y0 - 3 < (m.y0 + m.y1) / 2 < y1 + 14 and m.x0 < 530]
    assert all(m.x0 < 530 for _, m in marcas)  # jamás una marca en "No"


def _codigos_marcados(ruta: Path):
    doc = pymupdf.open(str(ruta))
    rotulos = [(i, s["bbox"][1], s["bbox"][3], re.match(r"^(\d{1,2}[a-z])\.", s["text"]).group(1))
               for i, p in enumerate(doc) for b in p.get_text("dict")["blocks"] for l in b.get("lines", [])
               for s in l["spans"] if s["bbox"][0] < 40 and re.match(r"^(\d{1,2}[a-z])\.", s["text"])]
    doc.close()
    codigos = set()
    for i, m in _marcas(ruta):
        for pagina, y0, y1, c in rotulos:
            if pagina == i and y0 - 3 < (m.y0 + m.y1) / 2 < y1 + 14:
                codigos.add(c)
    return codigos


FILAS_DINTELES = {"8a", "8b", "8c", "8d", "9a", "9b", "9c", "9d"}


@pytest.mark.parametrize("elementos,esperadas", [
    (["L1", "L2"], set()),
    (["L1", "DINTEL D1"], FILAS_DINTELES),
    (["Dinteles de la escalera", "V1"], FILAS_DINTELES),
])
def test_fi02_marca_dinteles_solo_si_la_visita_los_incluye(entorno, elementos, esperadas):
    base = crear_fi(entorno / "FI-02.pdf", "FI-02", nivel=NIVEL, obs=["Anterior."])
    r = _llamar(entorno, tipo="FI-02", existente=base, elementos=elementos)
    assert r["ok"], r
    codigos = _codigos_marcados(r["ruta"])
    assert codigos & FILAS_DINTELES == esperadas
    assert codigos >= FILAS_SI["FI-02"] and r["marcas"] == len(FILAS_SI["FI-02"]) + len(esperadas)
    assert ("dinteles" in " ".join(r["avisos"])) == bool(esperadas)


@pytest.mark.parametrize("elementos,esperadas", [
    (["C1", "M2"], set()),
    (["C1", "MURO DE CERRAMIENTO EJE 3"], {"9a", "9b", "9c"}),
    (["Pandereta del eje A"], {"9a", "9b", "9c"}),
    (["DINTEL D1"], set()),  # un dintel no activa el cerramiento del FI-03
])
def test_fi03_marca_cerramiento_solo_si_la_visita_lo_incluye_y_nunca_mamposteria(entorno, elementos, esperadas):
    base = crear_fi(entorno / "FI-03.pdf", "FI-03", nivel=NIVEL, obs=["Anterior."])
    r = _llamar(entorno, tipo="FI-03", existente=base, elementos=elementos)
    assert r["ok"], r
    codigos = _codigos_marcados(r["ruta"])
    assert codigos & {"9a", "9b", "9c"} == esperadas
    assert not codigos & {"8a", "8b", "8c", "8d", "8e", "8f", "8g"}  # MAMPOSTERÍA: nunca


def test_fi01_no_marca_dinteles_ni_cerramiento_aunque_se_nombren(entorno):
    base = crear_fi(entorno / "FI-01.pdf", "FI-01", nivel=NIVEL, obs=["Anterior."])
    r = _llamar(entorno, tipo="FI-01", existente=base, elementos=["DINTEL D1", "MURO DE CERRAMIENTO"])
    assert r["ok"] and r["marcas"] == len(FILAS_SI["FI-01"])


def test_si_falta_una_fila_obligatoria_no_marca_a_ciegas(entorno):
    base = crear_fi(entorno / "FI-02.pdf", "FI-02", nivel=NIVEL, obs=["x"], omitir=["11c"])
    r = _llamar(entorno, existente=base)
    assert not r["ok"] and r["ruta"] is None and "11c" in r["errores"][0]
    assert not (entorno / "salida").exists()


def _palabras_de_firmas(ruta: Path):
    """(palabra, y) de la zona de fechas de autorización de la última hoja."""
    doc = pymupdf.open(str(ruta))
    try:
        return [(w[4], round(w[1])) for w in doc[-1].get_text("words") if w[1] > 770 and w[0] >= 455]
    finally:
        doc.close()


def test_la_fecha_de_autorizacion_va_en_la_siguiente_fila_libre_y_las_anteriores_se_conservan(entorno, existente):
    r = _llamar(entorno, existente=existente)
    assert r["ok"], r
    palabras = _palabras_de_firmas(r["ruta"])
    fila1 = sorted(w for w, y in palabras if y < 800)
    fila2 = sorted(w for w, y in palabras if y >= 800)
    assert {"02", "10", "2026"} <= set(fila1)  # la fila llena de una visita anterior, intacta
    assert {"15", "10", "2026"} <= set(fila2) and not {"dd", "mm", "aaaa"} & set(fila2)  # la de esta visita


def test_una_fila_con_solo_barras_tambien_es_libre_y_se_usa_la_primera(entorno):
    base = crear_fi(entorno / "base.pdf", "FI-02", nivel=NIVEL, obs=["x"], fechas_aut=("llena", "vacia", "libre"))
    r = _llamar(entorno, existente=base)
    assert r["ok"], r
    palabras = _palabras_de_firmas(r["ruta"])
    assert {"15", "10", "2026"} <= {w for w, y in palabras if 796 <= y < 816}  # la 2.ª fila (la 1.ª libre)
    assert {"dd", "mm", "aaaa"} <= {w for w, y in palabras if y >= 816}        # la 3.ª sigue libre


def test_sin_fila_libre_es_error_y_no_se_sobrescribe_ninguna(entorno):
    base = crear_fi(entorno / "base.pdf", "FI-02", nivel=NIVEL, obs=["x"], fechas_aut=("llena", "llena"))
    r = _llamar(entorno, existente=base)
    assert not r["ok"] and r["ruta"] is None and "ninguna fila libre" in r["errores"][0]
    assert not (entorno / "salida").exists()


def _palabras_en(ruta: Path, pagina: int):
    doc = pymupdf.open(str(ruta))
    try:
        return [(w[4], w[1], w[3]) for w in doc[pagina].get_text("words")]
    finally:
        doc.close()


def _lineas_anchas(ruta: Path, pagina: int):
    doc = pymupdf.open(str(ruta))
    try:
        return sorted(r.y0 for d in doc[pagina].get_drawings() for it in d["items"] if it[0] == "re"
                      for r in [pymupdf.Rect(it[1])] if r.width >= 540 and r.height <= 2.5)
    finally:
        doc.close()


def test_sin_fila_libre_agrega_una_fila_nueva_debajo_de_la_ultima_con_la_geometria_de_la_anterior(entorno):
    base = crear_fi(entorno / "base.pdf", "FI-02", nivel=NIVEL, obs=["x"], fechas_aut=("llena", "llena"),
                    tabla=True, y_filas=(600.0, 620.0))
    hash_antes = _hash(base)
    lineas_antes = _lineas_anchas(base, len(pymupdf.open(str(base))) - 1)
    r = _llamar(entorno, existente=base)
    assert r["ok"] and r["fila_agregada"], r
    assert _hash(base) == hash_antes
    assert any("fila nueva" in a for a in r["avisos"])
    ultima = len(pymupdf.open(str(r["ruta"]))) - 1
    nuevas = [y for y in _lineas_anchas(r["ruta"], ultima) if y > 625]
    assert len(nuevas) == 1 and abs(nuevas[0] - (lineas_antes[-1] + 1.8 + 20)) < 1.0  # misma altura de fila (20 pt)
    palabras = _palabras_en(r["ruta"], ultima)
    nuevas_p = {w for w, y0, y1 in palabras if y0 > 626}
    assert {"15", "10", "2026"} <= nuevas_p and "dd" not in nuevas_p
    # misma posición horizontal que la fecha de la fila anterior
    doc = pymupdf.open(str(r["ruta"]))
    xs = {w[4]: w[0] for w in doc[ultima].get_text("words") if w[4] in ("02", "10", "2026", "15")}
    doc.close()
    assert abs(xs["15"] - xs["02"]) < 1.5
    assert len(_marcas(r["ruta"])) == len(FILAS_SI["FI-02"])  # y todo lo demás sigue como antes


def test_antes_de_agregar_una_fila_se_usa_la_primera_fila_vacia_del_bloque_de_inspectores(entorno):
    base = crear_fi(entorno / "base.pdf", "FI-02", nivel=NIVEL, obs=["x"], fechas_aut=("llena", "llena"),
                    tabla=True, y_filas=(600.0, 620.0), vacias=2)
    antes = _lineas_anchas(base, len(pymupdf.open(str(base))) - 1)
    r = _llamar(entorno, existente=base)
    assert r["ok"] and not r["fila_agregada"], r
    assert any("primera fila vacía" in a for a in r["avisos"])
    ultima = len(pymupdf.open(str(r["ruta"]))) - 1
    assert _lineas_anchas(r["ruta"], ultima) == antes  # la tabla no cambia: no se agregó ninguna fila
    nuevas = {w for w, y0, y1 in _palabras_en(r["ruta"], ultima) if 625 < y0 < 646}  # 1.ª fila vacía: 625-645
    assert {"15", "10", "2026"} <= nuevas
    assert not {"15"} & {w for w, y0, y1 in _palabras_en(r["ruta"], ultima) if y0 > 646}  # la 2.ª sigue vacía


def test_la_fila_nueva_que_no_cabe_va_en_la_hoja_siguiente(entorno):
    base = crear_fi(entorno / "base.pdf", "FI-02", nivel=NIVEL, obs=["x"], fechas_aut=("llena", "llena"),
                    tabla=True, hoja_siguiente=True)
    r = _llamar(entorno, existente=base)
    assert r["ok"] and r["fila_agregada"], r
    assert any("hoja siguiente" in a for a in r["avisos"])
    doc = pymupdf.open(str(r["ruta"]))
    siguiente = doc[len(doc) - 1]
    assert {"15", "10", "2026"} <= {w[4] for w in siguiente.get_text("words")}
    assert not {"15"} & {w[4] for w in doc[len(doc) - 2].get_text("words") if w[1] > 826}
    doc.close()


def test_la_fila_nueva_sin_espacio_ni_hoja_siguiente_es_error_y_no_escribe(entorno):
    base = crear_fi(entorno / "base.pdf", "FI-02", nivel=NIVEL, obs=["x"], fechas_aut=("llena", "llena"), tabla=True)
    r = _llamar(entorno, existente=base)
    assert not r["ok"] and r["ruta"] is None and "no cabe" in r["errores"][0]
    assert not (entorno / "salida").exists()
    # con hoja siguiente pero ocupada tampoco hay sitio
    base2 = crear_fi(entorno / "base2.pdf", "FI-02", nivel=NIVEL, obs=["x"], fechas_aut=("llena", "llena"),
                     tabla=True, hoja_siguiente=True)
    doc = pymupdf.open(str(base2))
    doc[len(doc) - 1].insert_text((60, 120), "CONTENIDO PREVIO", fontsize=10.6)
    ruta = entorno / "base3.pdf"
    doc.save(str(ruta))
    doc.close()
    r = _llamar(entorno, existente=ruta)
    assert not r["ok"] and "no cabe" in r["errores"][0]


def _rayas_de_observaciones(ruta: Path):
    """Rectángulos de dibujo entre OBSERVACIONES y NOMBRES Y FIRMAS (las rayas de la tabla de observaciones)."""
    doc = pymupdf.open(str(ruta))
    try:
        for p in doc:
            spans = [s for b in p.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]]
            cab = next((s for s in spans if re.match(r"^\d{1,2}\.\s*OBSERVACIONES", s["text"].strip(), re.I)), None)
            fir = next((s for s in spans if re.match(r"^\d{1,2}\.\s*NOMBRES Y FIRMAS", s["text"].strip(), re.I)), None)
            if cab and fir:
                return sorted((round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1))
                              for d in p.get_drawings() for it in d["items"] if it[0] == "re"
                              for r in [pymupdf.Rect(it[1])] if cab["bbox"][3] < r.y0 < fir["bbox"][1])
        return []
    finally:
        doc.close()


@pytest.mark.parametrize("cierre", ["Todo segun los planos estructurales.", "CONFORME A PLANOS APROBADOS"])
def test_mover_el_cierre_no_corta_ninguna_raya_y_el_conforme_anterior_tambien_se_mueve(entorno, cierre):
    base = crear_fi(entorno / "base.pdf", "FI-02", nivel=NIVEL, rayas_obs=True,
                    obs=["Observacion anterior UNO.", "Observacion anterior DOS.", "", cierre])
    rayas_antes = _rayas_de_observaciones(base)
    assert len(rayas_antes) == 9
    r = _llamar(entorno, existente=base, visita=_visita(clase="Parcial"))
    assert r["ok"] and r["cierre_movido"] == [cierre], r
    assert _rayas_de_observaciones(r["ruta"]) == rayas_antes  # ni una raya cortada o tapada
    texto = fi_mived.limpiar_extraido(" ".join(p.get_text() for p in pymupdf.open(str(r["ruta"]))))
    assert texto.index("15/10/2026 - PARCIAL") < texto.index(cierre)  # el cierre quedó después de la observación nueva
    doc = pymupdf.open(str(r["ruta"]))  # y ningún relleno blanco quedó en la página
    assert not [d for p in doc for d in p.get_drawings() if d.get("fill") == (1.0, 1.0, 1.0)]
    doc.close()


def test_el_cierre_anterior_queda_al_final_con_el_mismo_texto(entorno):
    cierre = "Todo segun los planos estructurales."
    base = crear_fi(entorno / "con_cierre.pdf", "FI-02", nivel=NIVEL,
                    obs=["Observacion anterior UNO.", "Observacion anterior DOS.", "", cierre])
    r = _llamar(entorno, existente=base, visita=_visita(clase="Completivo"))
    assert r["ok"], r
    assert r["cierre_movido"] == [cierre] and "se movió" in " ".join(r["avisos"])
    doc = pymupdf.open(str(r["ruta"]))
    palabras = doc[-1].get_text("words")
    doc.close()

    def y_de(texto):
        return min(w[1] for w in palabras if fi_mived.limpiar_extraido(w[4]) == texto)
    assert y_de("UNO.") < y_de("DOS.") < y_de("PARCIAL:".replace("PARCIAL", "COMPLETIVO")) < y_de("Todo")
    assert y_de("CONFORME") < y_de("Todo")  # la conformidad nueva también va antes del cierre anterior
    texto = " ".join(_texto(r["ruta"]).split())
    assert texto.count(cierre) == 1  # no se duplica ni se pierde


def test_sin_cierre_anterior_no_se_mueve_nada(entorno, existente):
    r = _llamar(entorno, existente=existente)
    assert r["ok"] and r["cierre_movido"] == []


# ---------- P5 y #18 ----------

def test_no_actualiza_el_fi_de_otro_nivel_error_18(entorno):
    otro = crear_fi(entorno / "otro.pdf", "FI-02", nivel="LOSAS Y VIGAS ENTREPISO SOTANO -5", obs=["x"])
    r = _llamar(entorno, existente=otro)
    assert not r["ok"] and "otro nivel" in r["errores"][0]
    assert not (entorno / "salida").exists()


def test_la_clave_de_nivel_respeta_limites_de_palabra_y_rechaza_claves_genericas_o3(entorno):
    otro = crear_fi(entorno / "n30.pdf", "FI-02", nivel="LOSAS Y VIGAS ENTREPISO SOTANO -30", obs=["x"])
    r = _llamar(entorno, existente=otro, nivel_clave="SOTANO -3")  # no encaja en SOTANO -30
    assert not r["ok"] and "otro nivel" in r["errores"][0]
    ok = crear_fi(entorno / "n3.pdf", "FI-02", nivel="LOSAS Y VIGAS ENTREPISO SOTANO -3 PARCIAL", obs=["x"])
    assert _llamar(entorno, existente=ok, nivel_clave="SOTANO -3")["ok"]
    generico = _llamar(entorno, existente=ok, nivel_clave="SOTANO")  # sin número y no es el nivel completo
    assert not generico["ok"] and "genérica" in generico["errores"][0]
    # Una clave sin número vale solo si es el nivel completo del FI (p. ej. 'FUNDACIONES')
    fund = crear_fi(entorno / "fund.pdf", "FI-02", nivel="FUNDACIONES", obs=["x"])
    assert _llamar(entorno, existente=fund, nivel_clave="FUNDACIONES", nivel_txt="FUNDACIONES")["ok"]


def test_parte_del_fi_en_blanco_si_no_existe_uno(entorno):
    blanco = crear_fi(entorno / "blanco.pdf", "FI-02")
    r = _llamar(entorno, en_blanco=blanco)
    assert r["ok"], r
    doc = pymupdf.open(str(r["ruta"]))
    p1 = fi_mived.limpiar_extraido(doc[0].get_text())
    doc.close()
    assert NIVEL in p1 and "15/10/2026" in p1
    for marcador in ("dd", "mm", "aaaa"):
        assert marcador not in p1  # el 'dd / mm / aaaa' del formulario se tapa


def _valor_en_fila(ruta: Path, rotulo: str, lado_der: bool = False) -> str:
    """Texto escrito en la fila del rótulo (a la derecha de él), de la mitad izquierda o derecha del formulario."""
    doc = pymupdf.open(str(ruta))
    try:
        p1 = doc[0]
        r = min(p1.search_for(rotulo), key=lambda h: h.y0)  # "Licencia No." también aparece dentro de "Sol. Licencia No."
        palabras = [w for w in p1.get_text("words") if abs(w[3] - r.y1) < 5 and w[0] >= r.x1 - 3
                    and (w[0] >= 400 if lado_der else w[0] < 398)]
        return fi_mived.limpiar_extraido(" ".join(w[4] for w in sorted(palabras, key=lambda w: w[0])))
    finally:
        doc.close()


def test_la_plantilla_en_blanco_recibe_los_5_campos_del_proyecto(entorno):
    blanco = crear_fi(entorno / "blanco.pdf", "FI-02", anotacion=False, fechas_aut=("libre", "libre"))
    r = _llamar(entorno, en_blanco=blanco)
    assert r["ok"], r
    assert _valor_en_fila(r["ruta"], "Nombre del proyecto") == "Proyecto Sintetico"
    assert _valor_en_fila(r["ruta"], "Licencia No.", lado_der=True) == "LIC-SINT"
    assert _valor_en_fila(r["ruta"], "Sol. Licencia No.", lado_der=True) == "SOL-SINT"
    assert _valor_en_fila(r["ruta"], "Encargado de obra") == "RESIDENTE SINT"
    assert _valor_en_fila(r["ruta"], "Dirección") == "CALLE SINTETICA 1"
    assert r["avisos"] == []


def test_un_valor_ya_escrito_no_se_sobrescribe_y_si_difiere_hay_aviso(entorno):
    previo = {"nombre": "Proyecto Sintetico", "no_licencia": "LIC-VIEJA", "direccion_obra": "OTRA CALLE 9"}
    base = crear_fi(entorno / "con_datos.pdf", "FI-02", nivel=NIVEL, obs=["x"], cabecera=previo)
    r = _llamar(entorno, existente=base)
    assert r["ok"], r
    assert _valor_en_fila(r["ruta"], "Licencia No.", lado_der=True) == "LIC-VIEJA"  # no se cambió
    assert _valor_en_fila(r["ruta"], "Dirección") == "OTRA CALLE 9"
    assert _valor_en_fila(r["ruta"], "Nombre del proyecto") == "Proyecto Sintetico"  # igual: sin aviso
    assert _valor_en_fila(r["ruta"], "Sol. Licencia No.", lado_der=True) == "SOL-SINT"  # estaba vacío: se escribe
    avisos = " ".join(r["avisos"])
    assert "LIC-VIEJA" in avisos and "OTRA CALLE 9" in avisos and "Proyecto Sintetico" not in avisos


def test_un_valor_muy_largo_se_reduce_o_no_cabe(entorno):
    blanco = crear_fi(entorno / "blanco.pdf", "FI-02", fechas_aut=("libre", "libre"))
    r = _llamar(entorno, en_blanco=blanco, proyecto={**PROYECTO, "direccion_obra": "CALLE LARGUISIMA " * 3})
    assert r["ok"] and "LARGUISIMA" in _valor_en_fila(r["ruta"], "Dirección")
    r2 = _llamar(entorno, en_blanco=blanco, proyecto={**PROYECTO, "direccion_obra": "X" * 400})
    assert not r2["ok"] and "no cabe" in r2["errores"][0]


def test_fila_sin_caja_propia_usa_la_x_de_las_cajas_vecinas_o1(entorno):
    base = crear_fi(entorno / "sin_caja.pdf", "FI-02", nivel=NIVEL, obs=["x"], sin_caja=("7c",))
    r = _llamar(entorno, existente=base)
    assert r["ok"], r
    marcas = _marcas(r["ruta"])
    assert len(marcas) == len(FILAS_SI["FI-02"])
    centros = sorted((m.x0 + m.x1) / 2 for _, m in marcas)
    assert centros[-1] - centros[0] < 1.0  # todas en la misma columna, incluida la fila sin caja


def test_sin_fi_de_partida_es_error(entorno):
    r = _llamar(entorno)
    assert not r["ok"] and "No hay FI de partida" in r["errores"][0]
    r2 = _llamar(entorno, existente=entorno / "no_existe.pdf")
    assert not r2["ok"] and "no existe" in r2["errores"][0]


# ---------- Conformidad y cabecera ----------

def test_cierre_de_conformidad_solo_en_completivo_sin_discrepancias(entorno, existente):
    cierre = "CONFORME A PLANOS APROBADOS"
    assert cierre not in _texto(_llamar(entorno, existente=existente)["ruta"])  # parcial
    r = _llamar(entorno, existente=existente, visita=_visita(clase="Completivo"))
    assert cierre in _texto(r["ruta"])
    r = _llamar(entorno, existente=existente, visita=_visita(clase="Completivo", discrepancias_abiertas=["C1 sin estribo"]))
    assert cierre not in _texto(r["ruta"])


@pytest.mark.parametrize("cambios,fragmento", [
    ({"visita": _visita(fecha="")}, "visita.fecha"),
    ({"visita": _visita(fecha="2026-10-15")}, "DD/MM/AAAA"),
    ({"visita": _visita(clase="Mixta")}, "Parcial o Completivo"),
    ({"nivel_txt": ""}, "nivel_txt"),
    ({"nivel_clave": "pendiente de verificar"}, "nivel_clave"),
    ({"proyecto": {**PROYECTO, "nombre": ""}}, "proyecto.nombre"),
    ({"proyecto": {**PROYECTO, "no_licencia": ""}}, "proyecto.no_licencia"),
    ({"proyecto": {**PROYECTO, "no_solicitud": "pendiente de verificar"}}, "proyecto.no_solicitud"),
    ({"proyecto": {**PROYECTO, "residente_obra": None}}, "proyecto.residente_obra"),
    ({"proyecto": {**PROYECTO, "direccion_obra": "  "}}, "proyecto.direccion_obra"),
    ({"elementos": []}, "elementos supervisados"),
    ({"tipo_fi": "FI-09"}, "desconocido"),
])
def test_cabecera_vacia_o_invalida_no_genera(entorno, existente, cambios, fragmento):
    r = _llamar(entorno, existente=existente, **cambios)
    assert not r["ok"] and r["ruta"] is None
    assert fragmento in " ".join(r["errores"])
    assert not (entorno / "salida").exists()


def test_observaciones_que_no_caben_no_generan(entorno, existente):
    r = _llamar(entorno, existente=existente, elementos=[f"elemento numero {i} de la visita" for i in range(400)])
    assert not r["ok"] and "no caben" in r["errores"][0]
    assert not (entorno / "salida").exists()


def test_auditoria_de_la_escritura_con_el_usuario_que_ejecuta(entorno, existente):
    import sqlite3
    r = _llamar(entorno, existente=existente)
    assert r["ok"]
    conn = sqlite3.connect(config.obtener_db_path())
    fila = conn.execute("SELECT usuario, accion FROM auditoria WHERE modulo='GENERADORES'").fetchone()
    conn.close()
    assert fila == ("prueba", "GUARDAR_PDF")


# ---------- Ningún dato fijo ----------

def test_ninguna_cadena_fija_de_proyecto_ni_se_lee_la_bd():
    fuente = (RAIZ / "fi_mived.py").read_text(encoding="utf-8")
    for cadena in ("TERRA", "VUC2037", "AYBAR", "VERGEL", "JAVIER", "48605", "Miguel"):
        assert cadena.upper() not in fuente.upper(), cadena
    assert "get_connection" not in fuente and "sqlite3" not in fuente


# ---------- Copias de los FI reales (solo lectura del original; se omite si no están en esta máquina) ----------

RAIZ_FI = Path(r"C:\Users\Steve\CATDIC Dropbox\SUPERVISION\EN CURSO\TERRA LIVING\FORMULARIOS\MIVED\FORMULARIOS NO FIRMADOS")
FI_REALES = [
    ("FI-02", "12. FI-02-26-STP-TERRALIVING LOSAS Y VIGAS ENTREPISO SOTANO -4 02-10-2026.pdf", "SOTANO -4", 1),
    ("FI-03", "10. FI-03-26-STP-TERRALIVING VERTICALES SOTANO -4 28-09-2026.pdf", "SOTANO -4", 1),
    ("FI-01", "1.FI-01-26-STP-TERRALIVING CIMENTACIONES 06.05.2026.pdf", "FUNDACIONES", 0),
]


def _limite_tabla_firmas(ruta: Path):
    """(pagina, y del borde inferior) de la tabla NOMBRES Y FIRMAS: la línea ancha más baja de la hoja de la fecha."""
    doc = pymupdf.open(str(ruta))
    try:
        fechas = [(i, s["origin"][1]) for i, p in enumerate(doc) for b in p.get_text("dict")["blocks"]
                  for l in b.get("lines", []) for s in l["spans"]
                  if s["bbox"][0] >= 455 and re.match(r"^(\d{2}/\d{2}/\d{4}|\d{4})$", s["text"].strip())]
        pagina, base = fechas[-1]
        anchas = [r for d in doc[pagina].get_drawings() for it in d["items"] if it[0] == "re"
                  for r in [pymupdf.Rect(it[1])] if r.width >= 540 and r.height <= 2.5 and r.y0 > base]
        return pagina, max(r.y1 for r in anchas), base
    finally:
        doc.close()


def _comprobar_fila_vacia_usada(antes: Path, despues: Path):
    """La fecha cae en la primera fila vacía del bloque de inspectores: la tabla no crece y queda dentro de ella."""
    pag, fondo_antes, base_antes = _limite_tabla_firmas(antes)
    pag2, fondo_despues, base_despues = _limite_tabla_firmas(despues)
    assert pag2 == pag and abs(fondo_despues - fondo_antes) < 0.01   # misma tabla
    assert base_antes < base_despues < fondo_antes                   # la fecha nueva, bajo la última y dentro de la tabla
    doc = pymupdf.open(str(despues))
    try:
        palabras = {w[4] for w in doc[pag].get_text("words") if base_antes < w[3] <= fondo_antes}
    finally:
        doc.close()
    assert {"15", "10", "2026"} <= palabras or "15/10/2026" in palabras


@pytest.mark.parametrize("tipo,archivo,clave,anotaciones_antes", FI_REALES)
def test_corrida_sobre_una_copia_de_un_fi_real(entorno, tipo, archivo, clave, anotaciones_antes):
    """
    Solo el FI-02 #12 trae filas de autorización libres (en su 4.ª hoja). El FI-01 #1 y el FI-03 #10 ya tienen todas
    sus filas llenas: ahí el generador agrega una fila nueva debajo de la última (respuesta "c." de Steven).
    """
    import shutil
    original = RAIZ_FI / archivo
    if not original.is_file():
        pytest.skip("el FI real no está en esta máquina")
    hash_antes = _hash(original)
    copia = entorno / "copia.pdf"
    shutil.copyfile(original, copia)
    doc = pymupdf.open(str(copia))
    cabecera_antes = fi_mived.limpiar_extraido(doc[0].get_text("text", clip=pymupdf.Rect(0, 100, 600, 165)))
    nivel_actual = fi_mived._texto_nivel_existente(doc[0])
    obs_antes = fi_mived.limpiar_extraido(" ".join(p.get_text() for p in doc))
    anotaciones = sum(len(list(p.annots() or [])) for p in doc)
    doc.close()
    assert anotaciones == anotaciones_antes
    if tipo == "FI-01":
        clave = nivel_actual  # este FI-01 no trae número: la clave debe ser el nivel completo
        assert clave
    r = fi_mived.actualizar_fi(tipo, PROYECTO, _visita(), nivel_actual or "FUNDACIONES", clave,
                               ["ELEMENTO SINTETICO 1", "ELEMENTO SINTETICO 2"], existente=copia, usuario="prueba")
    assert r["ok"], r
    assert _hash(original) == hash_antes  # el original no cambió (ni el de la copia de partida)
    assert _rayas_de_observaciones(copia) == _rayas_de_observaciones(r["ruta"])  # ninguna raya cortada
    assert r["fila_agregada"] is False  # hay fila libre (FI-02) o fila vacía del bloque de inspectores (FI-01/03)
    if tipo != "FI-02":
        _comprobar_fila_vacia_usada(copia, r["ruta"])
    out = pymupdf.open(str(r["ruta"]))
    # Los datos de cabecera que ya traía el FI no se tocan (ni siquiera con otros datos de proyecto)
    cabecera_despues = fi_mived.limpiar_extraido(out[0].get_text("text", clip=pymupdf.Rect(0, 100, 600, 165)))
    for linea in cabecera_antes.splitlines():
        if linea.strip() and not re.fullmatch(r"[\d\s/]+", linea.strip()):  # la fecha sí se reescribe
            assert linea.strip() in cabecera_despues, linea
    texto = fi_mived.limpiar_extraido(" ".join(p.get_text() for p in out))
    assert "15/10/2026 - PARCIAL: Se supervisaron ELEMENTO SINTETICO 1, ELEMENTO SINTETICO 2." in " ".join(texto.split())
    assert sum(len(list(p.annots() or [])) for p in out) == 0
    out.close()
    # Las observaciones anteriores siguen: todas las líneas de observaciones del original están en el resultado
    for fragmento in ("Se supervisaron", "Todo segun") if tipo != "FI-01" else ("Se realizaron", "Todo segun"):
        if fragmento in obs_antes:
            assert fragmento in texto
    assert len(_marcas(r["ruta"])) == len(FILAS_SI[tipo])  # el mismo número de marcas que la tabla de T0b
    assert any("distinto del proyecto" in a for a in r["avisos"])  # el FI real trae otros datos: solo avisos


@pytest.mark.parametrize("tipo", ["FI-01", "FI-02", "FI-03"])
def test_plantilla_en_blanco_real_recibe_los_5_campos_sinteticos(entorno, tipo):
    blanco = RAIZ_FI.parent.parent / f"{tipo}-26-STP-TERRALIVING.pdf"
    if not blanco.is_file():
        pytest.skip("la plantilla en blanco real no está en esta máquina")
    hash_antes = _hash(blanco)
    r = fi_mived.actualizar_fi(tipo, PROYECTO, _visita(), "NIVEL SINTETICO -9", "-9", ["ELEMENTO SINTETICO"],
                               en_blanco=blanco, usuario="prueba")
    assert r["ok"], r
    assert _hash(blanco) == hash_antes
    assert _valor_en_fila(r["ruta"], "Nombre del proyecto") == "Proyecto Sintetico"
    assert _valor_en_fila(r["ruta"], "Licencia No.", lado_der=True) == "LIC-SINT"
    assert _valor_en_fila(r["ruta"], "Encargado de obra") == "RESIDENTE SINT"
    assert _valor_en_fila(r["ruta"], "Dirección") == "CALLE SINTETICA 1"
    assert len(_marcas(r["ruta"])) == len(FILAS_SI[tipo]) and r["avisos"] == []
