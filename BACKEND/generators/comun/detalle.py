# BACKEND/generators/comun/detalle.py
# Etapa 3 · T6 — M4 (CLAUDE.md §4.7): DETALLE.
# Siempre un recorte nítido del PLANO estructural; nunca una foto de campo (error #2).
# La región llega como parámetro (en puntos del PDF); este módulo no la deduce.
from pathlib import Path
from typing import Tuple, Union

import pymupdf
from PIL import Image

from reglas_ingenieria import PENDIENTE

DPI_DETALLE = 300
LADO_MINIMO_PX = 200  # por debajo, el recorte sería ilegible
Region = Tuple[float, float, float, float]  # x0, y0, x1, y1 en puntos del PDF (72 por pulgada)


def recortar_detalle(ruta_plano: Union[str, Path], pagina: int, region_pt: Region,
                     carpeta_planos: Union[str, Path], dpi: int = DPI_DETALLE) -> Image.Image:
    """
    Recorta una región de la hoja `pagina` (0-based) del plano.
    `carpeta_planos` es OBLIGATORIA: un PDF de visita (fotos de campo) también es .pdf, así que la
    única garantía de que es un plano es que esté en la carpeta de planos estructurales.
    Rechaza (ValueError) lo que no sea un plano: un archivo que no es PDF (una foto), un PDF fuera
    de `carpeta_planos`, una región fuera de la hoja o tan chica que sería ilegible.
    """
    ruta = Path(ruta_plano)
    if ruta.suffix.lower() != ".pdf":
        raise ValueError(f"Error #2: DETALLE solo se recorta de un plano en PDF, no de '{ruta.name}' "
                         "(una foto de campo nunca va en DETALLE).")
    if not carpeta_planos or not str(carpeta_planos).strip():
        raise ValueError(f"{PENDIENTE}: falta la carpeta de planos; sin ella no se puede garantizar "
                         "que el origen sea un plano (error #2).")
    try:
        ruta.resolve().relative_to(Path(carpeta_planos).resolve())
    except ValueError:
        raise ValueError(f"Error #2: '{ruta.name}' no está en la carpeta de planos; DETALLE solo "
                         "sale de los planos estructurales.") from None
    x0, y0, x1, y1 = region_pt
    with pymupdf.open(str(ruta)) as doc:
        if not 0 <= pagina < doc.page_count:
            raise ValueError(f"{PENDIENTE}: la hoja {pagina} no existe en el plano ({doc.page_count} hojas).")
        hoja = doc[pagina]
        if not (hoja.rect.x0 <= x0 < x1 <= hoja.rect.x1 and hoja.rect.y0 <= y0 < y1 <= hoja.rect.y1):
            raise ValueError(f"{PENDIENTE}: la región {region_pt} no cabe en la hoja {hoja.rect}; "
                             "las coordenadas no se deducen.")
        escala = dpi / 72.0
        if min(x1 - x0, y1 - y0) * escala < LADO_MINIMO_PX:
            raise ValueError(f"Error #2: el recorte de DETALLE sería ilegible (menos de {LADO_MINIMO_PX} px).")
        pix = hoja.get_pixmap(dpi=dpi, clip=pymupdf.Rect(x0, y0, x1, y1), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
