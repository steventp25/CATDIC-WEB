# BACKEND/generators/comun/fotos.py
# Etapa 3 · T6 — M1 (CLAUDE.md §4.7): fotos del levantamiento.
# Recorte individual *cover* con ImageOps.fit al aspecto de su celda y gutter blanco entre celdas,
# para no dejar franjas vacías (error #3). Redimensionado de §5.2: máx. 1000×1000, JPG q72,
# con exif_transpose.
import io
from pathlib import Path
from typing import List, Tuple, Union

from PIL import Image, ImageOps

from reglas_ingenieria import PENDIENTE, seleccionar_fotos_m1, seleccionar_fotos_pick4

LADO_MAXIMO_PX = 1000
CALIDAD_JPG = 72
GUTTER_PX = 8
BLANCO = (255, 255, 255)
Caja = Tuple[int, int, int, int]  # x0, y0, x1, y1 (x1 e y1 excluidos)


def preparar_foto(origen: Union[str, Path, bytes, Image.Image]) -> Image.Image:
    """Abre la foto, aplica exif_transpose, la pasa a RGB y la reduce a máx. 1000×1000 (§5.2)."""
    if isinstance(origen, Image.Image):
        img = origen.copy()
    elif isinstance(origen, (bytes, bytearray)):
        img = Image.open(io.BytesIO(origen))
    else:
        img = Image.open(origen)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img.thumbnail((LADO_MAXIMO_PX, LADO_MAXIMO_PX), Image.LANCZOS)
    return img


def foto_a_jpg(img: Image.Image) -> bytes:
    """JPG con calidad 72 (§5.2)."""
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=CALIDAD_JPG)
    return buffer.getvalue()


def recortar_cover(img: Image.Image, ancho: int, alto: int) -> Image.Image:
    """Recorte *cover* individual al aspecto de la celda: llena la celda sin deformar ni dejar franjas."""
    if ancho <= 0 or alto <= 0:
        raise ValueError(f"{PENDIENTE}: la celda de la foto debe tener ancho y alto positivos.")
    return ImageOps.fit(img.convert("RGB"), (ancho, alto), Image.LANCZOS)


def _partir(total: int, partes: int, gutter: int) -> List[Tuple[int, int]]:
    """Reparte `total` px en `partes` tramos separados por `gutter`, sin sobrar ni faltar px."""
    util = total - gutter * (partes - 1)
    if util < partes:
        raise ValueError(f"{PENDIENTE}: la zona de fotos es demasiado pequeña para {partes} celdas.")
    base, resto = divmod(util, partes)
    tramos, inicio = [], 0
    for i in range(partes):
        largo = base + (1 if i < resto else 0)
        tramos.append((inicio, inicio + largo))
        inicio += largo + gutter
    return tramos


def celdas_cuadricula(n: int, ancho: int, alto: int, gutter: int = GUTTER_PX) -> List[Caja]:
    """
    Celdas de la cuadrícula para n fotos (1 a 4). Las celdas más el gutter cubren TODA la zona:
    1 -> una grande; 2 -> dos columnas; 3 -> una ancha arriba y dos abajo; 4 -> 2×2.
    """
    if n == 1:
        return [(0, 0, ancho, alto)]
    if n not in (2, 3, 4):
        raise ValueError(f"{PENDIENTE}: la cuadrícula admite de 1 a 4 fotos, llegaron {n}.")
    if n == 2:
        return [(x0, 0, x1, alto) for x0, x1 in _partir(ancho, 2, gutter)]
    filas = _partir(alto, 2, gutter)
    columnas = _partir(ancho, 2, gutter)
    if n == 4:
        return [(x0, y0, x1, y1) for y0, y1 in filas for x0, x1 in columnas]
    (a0, a1), (b0, b1) = filas
    return [(0, a0, ancho, a1)] + [(x0, b0, x1, b1) for x0, x1 in columnas]


def armar_cuadricula(fotos: List[Image.Image], ancho: int, alto: int, gutter: int = GUTTER_PX) -> Image.Image:
    """Cuadrícula de 1 a 4 fotos: cada una recortada *cover* a su celda, separadas por gutter blanco."""
    lienzo = Image.new("RGB", (ancho, alto), BLANCO)
    for foto, (x0, y0, x1, y1) in zip(fotos, celdas_cuadricula(len(fotos), ancho, alto, gutter)):
        lienzo.paste(recortar_cover(foto, x1 - x0, y1 - y0), (x0, y0))
    return lienzo


def seleccionar_para_stp(fotos: List[str]) -> List[str]:
    """STP-MIVED: hasta 4 fotos repartidas en la secuencia (pick4); con 1 va 1 grande."""
    return seleccionar_fotos_pick4(fotos)


def seleccionar_para_hv(fotos: List[str], tipo_elemento: str) -> List[str]:
    """HV-LEV: todas las fotos, salvo escaleras (máx. 9 repartidas)."""
    return seleccionar_fotos_m1(fotos, tipo_elemento)
