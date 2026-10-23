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
    "FI-02": ["3a", "8a", "8b", "9a", "9b"],  # 8-9: dinteles
    "FI-03": ["3a", "8a", "8b", "9a", "9b"],  # 8: mampostería, 9: cerramiento y pandereta
}


def crear_fi(ruta: Path, tipo: str, nivel: str = "", fecha: str = "", obs=(), omitir=(), firmas=True,
             anotacion=True) -> Path:
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
            pag.insert_image(pymupdf.Rect(505.3, y + 2.6, 553.9, y + 11.8), stream=png)
            y += paso
    pag = doc.new_page(width=595.32, height=841.92)
    pag.insert_text((194.6, 484.8), "13. OBSERVACIONES", fontsize=10.6, fontname="hebo")
    for i, linea in enumerate(obs):
        pag.insert_text((26.8, 502.6 + i * 15.8), linea, fontsize=10.6)
    pag.insert_text((185.8, 753.7), "14. NOMBRES Y FIRMAS", fontsize=10.6, fontname="hebo")
    pag.insert_text((298.7, 774.2), "Firma", fontsize=10.6)
    if firmas:
        for y_base in (789.9, 809.9):
            pag.insert_text((176.5, y_base), "NOMBRE SINT", fontsize=10.6)
            for x, t in ((466.7, "02"), (500.6, "10"), (540.2, "2026")):
                pag.insert_text((x, y_base), t, fontsize=10.6)
    if anotacion:
        a = pag.add_rect_annot(pymupdf.Rect(329.6, 796.5, 365.8, 816.2))
        a.set_info(title="Inspector")
        a.update()
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


PROYECTO = {"nombre": "Proyecto Sintetico"}


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


def test_si_falta_una_fila_obligatoria_no_marca_a_ciegas(entorno):
    base = crear_fi(entorno / "FI-02.pdf", "FI-02", nivel=NIVEL, obs=["x"], omitir=["11c"])
    r = _llamar(entorno, existente=base)
    assert not r["ok"] and r["ruta"] is None and "11c" in r["errores"][0]
    assert not (entorno / "salida").exists()


def test_fechas_de_autorizacion_quedan_en_blanco(entorno, existente):
    r = _llamar(entorno, existente=existente)
    doc = pymupdf.open(str(r["ruta"]))
    palabras = [w[4] for w in doc[-1].get_text("words") if w[1] > 770 and w[0] >= 460]
    textos = doc[-1].get_text()
    doc.close()
    assert "NOMBRE SINT" in textos  # el resto de la sección de firmas sigue
    assert not [w for w in palabras if w in ("02", "10", "2026")]


# ---------- P5 y #18 ----------

def test_no_actualiza_el_fi_de_otro_nivel_error_18(entorno):
    otro = crear_fi(entorno / "otro.pdf", "FI-02", nivel="LOSAS Y VIGAS ENTREPISO SOTANO -5", obs=["x"])
    r = _llamar(entorno, existente=otro)
    assert not r["ok"] and "otro nivel" in r["errores"][0]
    assert not (entorno / "salida").exists()


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
    ({"proyecto": {"nombre": ""}}, "proyecto.nombre"),
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


@pytest.mark.parametrize("tipo,archivo,clave,anotaciones_antes", FI_REALES)
def test_corrida_sobre_una_copia_de_un_fi_real(entorno, tipo, archivo, clave, anotaciones_antes):
    import shutil
    original = RAIZ_FI / archivo
    if not original.is_file():
        pytest.skip("el FI real no está en esta máquina")
    hash_antes = _hash(original)
    copia = entorno / "copia.pdf"
    shutil.copyfile(original, copia)
    doc = pymupdf.open(str(copia))
    nivel_actual = fi_mived._texto_nivel_existente(doc[0])
    obs_antes = fi_mived.limpiar_extraido(" ".join(p.get_text() for p in doc))
    anotaciones = sum(len(list(p.annots() or [])) for p in doc)
    doc.close()
    assert anotaciones == anotaciones_antes
    if tipo == "FI-01":
        clave = "FUNDACIONES"  # el nivel que trae este FI-01 en la fila 'Nivel a inspeccionar'
        assert clave in fi_mived._normalizar_texto(nivel_actual or "")
    r = fi_mived.actualizar_fi(tipo, PROYECTO, _visita(), nivel_actual or "FUNDACIONES", clave,
                               ["ELEMENTO SINTETICO 1", "ELEMENTO SINTETICO 2"], existente=copia, usuario="prueba")
    assert r["ok"], r
    assert _hash(original) == hash_antes  # el original no cambió (ni el de la copia de partida)
    out = pymupdf.open(str(r["ruta"]))
    texto = fi_mived.limpiar_extraido(" ".join(p.get_text() for p in out))
    assert "15/10/2026 - PARCIAL: Se supervisaron ELEMENTO SINTETICO 1, ELEMENTO SINTETICO 2." in " ".join(texto.split())
    assert sum(len(list(p.annots() or [])) for p in out) == 0
    out.close()
    # Las observaciones anteriores siguen: todas las líneas de observaciones del original están en el resultado
    for fragmento in ("Se supervisaron", "Todo segun") if tipo != "FI-01" else ("Se realizaron", "Todo segun"):
        if fragmento in obs_antes:
            assert fragmento in texto
    assert len(_marcas(r["ruta"])) == len(FILAS_SI[tipo])  # el mismo número de marcas que la tabla de T0b
