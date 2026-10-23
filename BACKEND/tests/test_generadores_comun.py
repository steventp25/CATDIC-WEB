# BACKEND/tests/test_generadores_comun.py
# Etapa 3 · T6 — Módulos visuales comunes M1–M4 y salida segura (CLAUDE.md §4.7, §5.2; errores
# #1, #2, #3, #4 y #15). Todo el material es # SINTÉTICO (imágenes y PDF creados en la prueba):
# no se usa ningún plano ni foto reales y no se escribe nada fuera de tmp_path.
import io
import json
import sqlite3

import pymupdf
import pytest
from PIL import Image

import config
import database
from generators.comun import detalle, fotos, localizacion, salida
from reglas_ingenieria import PESO_MAXIMO_PDF_BYTES

BLANCO = (255, 255, 255)


# ---------- Material sintético ----------

def _foto_color(color, tam=(400, 300)):
    return Image.new("RGB", tam, color)


def _plano_pdf(ruta, ancho=612, alto=792):
    """PDF de 1 hoja con un cuadrado de color en cada esquina (para comprobar que es la hoja entera)."""
    doc = pymupdf.open()
    hoja = doc.new_page(width=ancho, height=alto)
    colores = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0)]  # sup-izq, sup-der, inf-izq, inf-der
    puntos = [(10, 10), (ancho - 60, 10), (10, alto - 60), (ancho - 60, alto - 60)]
    for (x, y), c in zip(puntos, colores):
        hoja.draw_rect(pymupdf.Rect(x, y, x + 50, y + 50), color=c, fill=c)
    hoja.insert_text((100, 400), "PLANTA SINTETICO", fontsize=24)
    doc.save(str(ruta))
    doc.close()
    return ruta


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """BD, Dropbox y salida de pruebas temporales."""
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "bd" / "catdic_prueba.db"))
    (tmp_path / "bd").mkdir()
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "dropbox"))
    monkeypatch.setenv(config.ENV_SALIDA_PRUEBAS, str(tmp_path / "salida"))
    database.inicializar_bd()
    return tmp_path


def _acciones_auditoria():
    conn = sqlite3.connect(config.obtener_db_path())
    conn.row_factory = sqlite3.Row
    try:
        return [dict(f) for f in conn.execute(
            "SELECT * FROM auditoria WHERE modulo = 'GENERADORES' ORDER BY id")]
    finally:
        conn.close()


# ---------- config ----------

def test_salida_pruebas_por_variable_y_por_defecto(tmp_path, monkeypatch):
    monkeypatch.setenv(config.ENV_SALIDA_PRUEBAS, str(tmp_path / "x"))
    assert config.obtener_salida_pruebas() == tmp_path / "x"
    monkeypatch.delenv(config.ENV_SALIDA_PRUEBAS)
    por_defecto = config.obtener_salida_pruebas()
    assert por_defecto.name == "CATDIC-SALIDA-PRUEBAS" and por_defecto.parent == config.Path.home()


# ---------- M1 · fotos ----------

@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_cuadricula_sin_franjas_vacias_error_3(n):
    """#3: las celdas más el gutter cubren toda la zona; cada celda queda llena de foto (cover)."""
    ancho, alto, g = 600, 400, 8
    colores = [(200, 30, 30), (30, 200, 30), (30, 30, 200), (200, 200, 30)][:n]
    fotos_in = [_foto_color(c, (123, 321 + 50 * i)) for i, c in enumerate(colores)]  # aspectos distintos
    img = fotos.armar_cuadricula(fotos_in, ancho, alto, g)
    celdas = fotos.celdas_cuadricula(n, ancho, alto, g)
    assert img.size == (ancho, alto)
    pix = img.load()
    dentro = set()
    for (x0, y0, x1, y1), color in zip(celdas, colores):
        assert x1 > x0 and y1 > y0
        for y in range(y0, y1):
            for x in range(x0, x1):
                assert pix[x, y] == color, (n, x, y)  # ni un píxel blanco dentro de una celda
                dentro.add((x, y))
    # Todo lo que no es celda es gutter blanco y es una franja del ancho del gutter
    fuera = [(x, y) for y in range(alto) for x in range(ancho) if (x, y) not in dentro]
    assert all(pix[x, y] == BLANCO for x, y in fuera)
    if n == 1:
        assert fuera == []
    else:
        assert len(fuera) > 0
        # sin márgenes exteriores: la primera fila y la primera columna tocan una celda
        assert (0, 0) in dentro and (ancho - 1, alto - 1) in dentro


def test_cuadricula_rechaza_cero_o_mas_de_cuatro_fotos():
    with pytest.raises(ValueError):
        fotos.celdas_cuadricula(0, 100, 100)
    with pytest.raises(ValueError):
        fotos.celdas_cuadricula(5, 100, 100)


def test_recorte_cover_no_deforma_y_llena_la_celda():
    img = Image.new("RGB", (400, 100), (255, 0, 0))
    img.paste((0, 0, 255), (150, 0, 250, 100))  # franja azul central, SINTÉTICO
    celda = fotos.recortar_cover(img, 100, 100)
    assert celda.size == (100, 100)
    assert celda.getpixel((50, 50)) == (0, 0, 255)  # recorta el centro en vez de encoger


def test_preparar_foto_exif_transpose_1000_y_jpg_q72():
    grande = Image.new("RGB", (3000, 2000), (10, 120, 200))
    exif = grande.getexif()
    exif[0x0112] = 6  # Orientation: rotar 90° (la foto se ve vertical)
    buffer = io.BytesIO()
    grande.save(buffer, format="JPEG", exif=exif)
    img = fotos.preparar_foto(buffer.getvalue())
    assert max(img.size) <= 1000 and img.size[1] > img.size[0]  # quedó vertical
    datos = fotos.foto_a_jpg(img)
    assert datos[:2] == b"\xff\xd8"
    assert Image.open(io.BytesIO(datos)).format == "JPEG"


def test_seleccion_stp_y_hv_usan_las_reglas_del_motor():
    lista = [f"f{i}.jpg" for i in range(10)]  # SINTÉTICO
    assert fotos.seleccionar_para_stp(lista) == ["f0.jpg", "f3.jpg", "f6.jpg", "f9.jpg"]
    assert fotos.seleccionar_para_hv(lista, "COLUMNA") == lista
    assert len(fotos.seleccionar_para_hv(lista, "ESCALERA")) == 9
    assert fotos.seleccionar_para_stp(["unica.jpg"]) == ["unica.jpg"]


# ---------- M3 · localización ----------

def test_localizacion_es_la_pagina_completa_error_1(tmp_path):
    pdf = _plano_pdf(tmp_path / "plano.pdf")
    img = localizacion.rasterizar_pagina_completa(pdf, 0)
    assert img.size == (round(612 * 200 / 72), round(792 * 200 / 72))  # 200 dpi, hoja entera
    w, h = img.size
    esperados = {(40, 40): (255, 0, 0), (w - 40, 40): (0, 255, 0),
                 (40, h - 40): (0, 0, 255), (w - 40, h - 40): (255, 255, 0)}
    for (x, y), color in esperados.items():
        assert img.getpixel((x, y)) == color  # las 4 esquinas del plano están en la imagen


def test_recuadro_rojo_visible_a_tamano_final_error_4(tmp_path):
    pdf = _plano_pdf(tmp_path / "plano.pdf")
    planta = localizacion.rasterizar_pagina_completa(pdf, 0)
    celda = (500, 650)  # tamaño final en la hoja, SINTÉTICO
    caja = (300, 700, 900, 1300)
    img, grosor = localizacion.dibujar_recuadro_rojo(planta, caja, *celda)
    assert grosor >= 4
    final = img.resize(celda, Image.LANCZOS)  # lo que se ve en el PDF
    escala = celda[0] / planta.width
    fila = int(1000 * (celda[1] / planta.height))
    rojos = [x for x in range(celda[0])
             if final.getpixel((x, fila))[0] > 150 and final.getpixel((x, fila))[1] < 90
             and final.getpixel((x, fila))[2] < 90]
    assert len(rojos) >= 2 * 3  # cada borde vertical (2) conserva >= 3 px de rojo
    assert abs(min(rojos) - caja[0] * escala) < 6
    # el original sigue intacto
    assert planta.getpixel((300, 1000)) != (220, 0, 0)


def test_recuadro_no_se_deduce_coordenadas_invalidas(tmp_path):
    pdf = _plano_pdf(tmp_path / "plano.pdf")
    planta = localizacion.rasterizar_pagina_completa(pdf, 0, dpi=50)
    for caja in [(-1, 0, 10, 10), (0, 0, planta.width + 1, 10), (10, 10, 10, 20), (20, 0, 10, 10)]:
        with pytest.raises(ValueError, match="pendiente de verificar"):
            localizacion.dibujar_recuadro_rojo(planta, caja, 100, 100)
    with pytest.raises(ValueError):
        localizacion.rasterizar_pagina_completa(pdf, 3)


# ---------- M4 · detalle ----------

def test_detalle_recorta_de_forma_nitida_del_plano(tmp_path):
    (tmp_path / "planos").mkdir()
    pdf = _plano_pdf(tmp_path / "planos" / "plano.pdf")
    img = detalle.recortar_detalle(pdf, 0, (0, 0, 100, 100), carpeta_planos=tmp_path / "planos")
    assert img.size == (round(100 * 300 / 72), round(100 * 300 / 72))
    assert img.getpixel((60, 60)) == (255, 0, 0)  # el cuadrado rojo sintético, sin suavizado


def test_detalle_rechaza_foto_de_campo_error_2(tmp_path):
    foto = tmp_path / "foto.jpg"
    Image.new("RGB", (800, 600), (90, 90, 90)).save(foto)
    with pytest.raises(ValueError, match="Error #2"):
        detalle.recortar_detalle(foto, 0, (0, 0, 100, 100))


def test_detalle_rechaza_pdf_fuera_de_la_carpeta_de_planos_y_regiones_malas(tmp_path):
    (tmp_path / "planos").mkdir()
    (tmp_path / "otras").mkdir()
    afuera = _plano_pdf(tmp_path / "otras" / "visita.pdf")
    with pytest.raises(ValueError, match="Error #2"):
        detalle.recortar_detalle(afuera, 0, (0, 0, 100, 100), carpeta_planos=tmp_path / "planos")
    with pytest.raises(ValueError, match="pendiente de verificar"):
        detalle.recortar_detalle(afuera, 0, (0, 0, 9999, 100))
    with pytest.raises(ValueError, match="ilegible"):
        detalle.recortar_detalle(afuera, 0, (0, 0, 10, 10))


# ---------- salida segura ----------

def test_guarda_sin_sobrescribir_crea_v2_y_audita_error_15(entorno):
    pdf = _plano_pdf(entorno / "plano.pdf").read_bytes()
    r1 = salida.guardar_pdf("Informe.pdf", pdf, formato="STP-MIVED", usuario="prueba")
    r2 = salida.guardar_pdf("Informe.pdf", pdf, formato="STP-MIVED", usuario="prueba")
    r3 = salida.guardar_pdf("Informe.pdf", pdf, usuario="prueba")
    assert r1["ruta"].name == "Informe.pdf" and not r1["version_nueva"]
    assert r2["ruta"].name == "Informe v2.pdf" and r2["version_nueva"]
    assert r3["ruta"].name == "Informe v3.pdf"
    assert r1["ruta"].read_bytes() == pdf  # el original no se tocó
    filas = _acciones_auditoria()
    assert [f["accion"] for f in filas] == ["GUARDAR_PDF"] * 3
    assert all(f["usuario"] == "prueba" for f in filas)
    assert json.loads(filas[1]["detalle_json"])["ruta"].endswith("Informe v2.pdf")


def test_auditoria_usa_el_usuario_que_ejecuta_no_uno_fijo(entorno, monkeypatch):
    monkeypatch.setattr(salida.getpass, "getuser", lambda: "usuario_sintetico")
    salida.guardar_pdf("A.pdf", b"%PDF-1.4 sintetico")
    assert _acciones_auditoria()[0]["usuario"] == "usuario_sintetico"


def test_rechaza_una_ruta_de_salida_dentro_de_dropbox(entorno):
    dentro = entorno / "dropbox" / "SUPERVISION" / "INFORMES"
    with pytest.raises(salida.SalidaInvalida, match="Dropbox"):
        salida.guardar_pdf("X.pdf", b"%PDF-1.4 sintetico", carpeta=dentro)
    assert not (entorno / "dropbox").exists()  # no se creó nada allí


def test_rechaza_salida_configurada_dentro_de_dropbox(entorno, monkeypatch):
    monkeypatch.setenv(config.ENV_SALIDA_PRUEBAS, str(entorno / "dropbox" / "pruebas"))
    with pytest.raises(salida.SalidaInvalida, match="Dropbox"):
        salida.guardar_pdf("X.pdf", b"%PDF-1.4 sintetico")


def test_rechaza_carpeta_fuera_de_la_salida_configurada(entorno):
    with pytest.raises(salida.SalidaInvalida, match="fuera"):
        salida.guardar_pdf("X.pdf", b"%PDF-1.4 sintetico", carpeta=entorno / "otra")
    sub = salida.guardar_pdf("X.pdf", b"%PDF-1.4 sintetico", carpeta=entorno / "salida" / "sub")
    assert sub["ruta"].parent.name == "sub"


@pytest.mark.parametrize("nombre", ["", "../X.pdf", "a/b.pdf", "X.txt"])
def test_rechaza_nombres_peligrosos(entorno, nombre):
    with pytest.raises(salida.SalidaInvalida):
        salida.guardar_pdf(nombre, b"%PDF-1.4 sintetico")


def test_pdf_de_30_mb_o_mas_se_rechaza_y_se_retira(entorno):
    grande = b"%PDF-1.4 " + b"0" * PESO_MAXIMO_PDF_BYTES  # SINTÉTICO: justo sobre el límite
    with pytest.raises(salida.SalidaInvalida, match="30 MB"):
        salida.guardar_pdf("Grande.pdf", grande, usuario="prueba")
    assert not (entorno / "salida" / "Grande.pdf").exists()
    filas = _acciones_auditoria()
    assert [f["accion"] for f in filas] == ["RECHAZAR_PDF"]
    assert "Error #15" in json.loads(filas[0]["detalle_json"])["errores"][0]
