# BACKEND/generators/comun/localizacion.py
# Etapa 3 · T6 — M3 (CLAUDE.md §4.7): LOCALIZACION.
# Planta estructural COMPLETA del nivel (nunca un zoom, error #1) con recuadro rojo RGB(220,0,0)
# cuyo grosor en la imagen fuente compensa la reducción (error #4). Las coordenadas del recuadro
# llegan como parámetro: este módulo nunca las deduce.
from pathlib import Path
from typing import Tuple, Union

import pymupdf
from PIL import Image, ImageDraw

from reglas_ingenieria import PENDIENTE, calcular_grosor_recuadro_rojo

DPI_PLANTA = 200
ROJO = (220, 0, 0)
Caja = Tuple[float, float, float, float]  # x0, y0, x1, y1 en píxeles de la imagen rasterizada


def rasterizar_pagina_completa(ruta_pdf: Union[str, Path], pagina: int, dpi: int = DPI_PLANTA) -> Image.Image:
    """Rasteriza la página ENTERA del plano (pagina es 0-based), sin recorte."""
    if dpi <= 0:
        raise ValueError(f"{PENDIENTE}: dpi inválido.")
    with pymupdf.open(str(ruta_pdf)) as doc:
        if not 0 <= pagina < doc.page_count:
            raise ValueError(f"{PENDIENTE}: la hoja {pagina} no existe en el plano ({doc.page_count} hojas).")
        pix = doc[pagina].get_pixmap(dpi=dpi, alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def dibujar_recuadro_rojo(planta: Image.Image, caja: Caja, ancho_celda_px: int, alto_celda_px: int
                          ) -> Tuple[Image.Image, int]:
    """
    Dibuja el recuadro rojo en una copia de la planta. `caja` viene dada (px de la planta);
    si no cabe en la imagen o es degenerada -> ValueError 'pendiente de verificar'.
    Devuelve (imagen, grosor_en_px_de_la_fuente).
    """
    x0, y0, x1, y1 = caja
    if not (0 <= x0 < x1 <= planta.width and 0 <= y0 < y1 <= planta.height):
        raise ValueError(f"{PENDIENTE}: el recuadro {caja} no cabe en la planta de "
                         f"{planta.width}×{planta.height} px; las coordenadas no se deducen.")
    grosor = calcular_grosor_recuadro_rojo(planta.width, planta.height, ancho_celda_px, alto_celda_px)
    salida = planta.convert("RGB").copy()
    ImageDraw.Draw(salida).rectangle([x0, y0, x1, y1], outline=ROJO, width=grosor)
    return salida, grosor


def generar_localizacion(ruta_pdf: Union[str, Path], pagina: int, caja: Caja, ancho_celda_px: int,
                         alto_celda_px: int, dpi: int = DPI_PLANTA) -> Image.Image:
    """Planta completa a 200 dpi + recuadro rojo con grosor compensado. Lista para pegar en la celda."""
    planta = rasterizar_pagina_completa(ruta_pdf, pagina, dpi)
    imagen, _ = dibujar_recuadro_rojo(planta, caja, ancho_celda_px, alto_celda_px)
    return imagen
