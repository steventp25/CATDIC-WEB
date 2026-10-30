# BACKEND/tests/test_dependencias.py
# Etapa 3 · T1 — Prueba de humo de las librerías de la fábrica de documentos.
# Todo se crea en memoria: no toca Dropbox, la BD ni archivos del proyecto.
import io
import warnings

import pytest


def _pdf_de_una_pagina() -> bytes:
    import pymupdf

    doc = pymupdf.open()
    pagina = doc.new_page(width=612, height=792)  # Carta
    pagina.insert_text((72, 72), "SINTÉTICO")
    datos = doc.tobytes()
    doc.close()
    return datos


def test_pymupdf_abre_un_pdf_de_una_pagina_en_memoria():
    import pymupdf

    doc = pymupdf.open(stream=_pdf_de_una_pagina(), filetype="pdf")
    try:
        assert doc.page_count == 1
        assert "SINTÉTICO" in doc[0].get_text()
    finally:
        doc.close()


def test_alias_fitz_sigue_disponible():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import fitz
    assert hasattr(fitz, "open")


def test_pillow_crea_y_recorta_una_imagen():
    from PIL import Image, ImageOps

    imagen = Image.new("RGB", (400, 200), (255, 255, 255))
    recorte = ImageOps.fit(imagen, (100, 100))
    assert recorte.size == (100, 100)
    buffer = io.BytesIO()
    recorte.save(buffer, format="JPEG", quality=72)
    assert buffer.tell() > 0


def test_pypdf_lee_el_pdf_en_memoria():
    from pypdf import PdfReader

    lector = PdfReader(io.BytesIO(_pdf_de_una_pagina()))
    assert len(lector.pages) == 1


def test_playwright_se_importa_y_chromium_esta_instalado():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ruta = p.chromium.executable_path
    from pathlib import Path

    assert Path(ruta).exists(), "Falta: py -3.14 -m playwright install chromium"
