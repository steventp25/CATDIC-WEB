# BACKEND/sync/escaner_dropbox.py
# Etapa 1 · T4 — Escáner de la carpeta de un proyecto de Supervisión (CLAUDE.md §5.1).
#
# SOLO LECTURA sobre Dropbox (§1.3): únicamente iterdir / stat / exists / is_dir / is_file.
# Nunca escribe, mueve, renombra ni borra, y no abre los PDFs.
# Las rutas que no existen se reportan como "pendiente de verificar" en `avisos`, sin excepción.
# La fecha de modificación (mtime) es solo informativa: nunca es la fecha de la visita (P1).
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from reglas_ingenieria import PENDIENTE
from sync.parser_visitas import (
    combinar_datos_visita,
    interpretar_nombre_carpeta_visita,
    interpretar_nombre_pdf_visita,
)

# Subcarpetas del layout de Supervisión (§5.1), relativas a la carpeta del proyecto
SUBRUTA_PLANOS_SELLADOS = Path("ARCHIVOS DEL CLIENTE", "PLANOS ESTRUCTURALES", "PLANOS SELLADOS")
SUBRUTA_VISITAS = Path("LEVANTAMIENTO", "VISITA A OBRA")
SUBRUTA_INFORMES_PROCESADOS = Path("INFORMES", "2.DATA PROCESADA")

LAYOUT_SUPERVISION = "supervision 5.1"
LAYOUT_NO_SOPORTADO = "no soportado en esta etapa"

# Archivos de sistema que se ignoran sin aviso
_IGNORADOS = {"desktop.ini", "thumbs.db"}


def _es_ignorado(nombre: str) -> bool:
    return nombre.startswith(".") or nombre.casefold() in _IGNORADOS


def _es_pdf(nombre: str) -> bool:
    return nombre.casefold().endswith(".pdf")


def _clave_orden(ruta: Path) -> Tuple[str, str]:
    """Orden estable por nombre (sin distinguir mayúsculas; desempate exacto)."""
    return ruta.name.casefold(), ruta.name


def _listar(carpeta: Path, avisos: List[str]) -> Optional[List[Path]]:
    """Entradas de una carpeta, ordenadas. None (con aviso) si no se puede leer."""
    try:
        return sorted(carpeta.iterdir(), key=_clave_orden)
    except OSError as error:
        avisos.append(f"{PENDIENTE}: no se pudo leer la carpeta '{carpeta}' ({error.__class__.__name__})")
        return None


def _info_archivo(ruta: Path, avisos: List[str]) -> Optional[Dict]:
    """Nombre, ruta, tamaño y mtime de un archivo (solo stat)."""
    try:
        st = ruta.stat()
    except OSError as error:
        avisos.append(f"{PENDIENTE}: no se pudo leer el archivo '{ruta}' ({error.__class__.__name__})")
        return None
    return {
        "nombre": ruta.name,
        "ruta": str(ruta),
        "tamano_bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
    }


def _ruta_existe(ruta: Path) -> bool:
    try:
        return ruta.is_dir()
    except OSError:
        return False


def _escanear_planos(carpeta: Path, avisos: List[str]) -> List[Dict]:
    if not _ruta_existe(carpeta):
        avisos.append(f"{PENDIENTE}: no existe la carpeta de planos sellados '{carpeta}'")
        return []
    entradas = _listar(carpeta, avisos)
    if entradas is None:
        return []
    planos = []
    for entrada in entradas:
        if _es_ignorado(entrada.name) or not entrada.is_file() or not _es_pdf(entrada.name):
            continue
        info = _info_archivo(entrada, avisos)
        if info:
            planos.append(info)
    if not planos:
        avisos.append(f"{PENDIENTE}: la carpeta de planos sellados '{carpeta}' no tiene PDF")
    return planos


def _escanear_visita(carpeta: Path) -> Dict:
    """Una carpeta de visita: sus PDFs (primer nivel) y la interpretación de T3 (regla P1)."""
    avisos: List[str] = []
    archivos: List[Dict] = []
    entradas = _listar(carpeta, avisos) or []
    for entrada in entradas:
        if _es_ignorado(entrada.name):
            continue
        if entrada.is_dir():
            avisos.append(f"subcarpeta '{entrada.name}' no se recorre en esta etapa")
            continue
        if not _es_pdf(entrada.name):
            avisos.append(f"archivo '{entrada.name}' no es PDF; no se usa")
            continue
        info = _info_archivo(entrada, avisos)
        if info:
            archivos.append(info)

    if not archivos:
        avisos.append("la carpeta no tiene PDF de la visita")

    datos_carpeta = interpretar_nombre_carpeta_visita(carpeta.name)
    datos_pdfs = [interpretar_nombre_pdf_visita(a["nombre"]) for a in archivos]
    return {
        "nombre_carpeta": carpeta.name,
        "ruta_carpeta": str(carpeta),
        "archivos": archivos,
        "sin_pdf": not archivos,
        "avisos": avisos,
        "interpretacion": combinar_datos_visita(datos_carpeta, datos_pdfs),
    }


def _escanear_visitas(carpeta: Path, avisos: List[str]) -> List[Dict]:
    entradas = _listar(carpeta, avisos)
    if entradas is None:
        return []
    visitas = []
    for entrada in entradas:
        if _es_ignorado(entrada.name):
            continue
        if not entrada.is_dir():
            avisos.append(f"'{entrada.name}' en '{carpeta}' no es una carpeta de visita; no se usa")
            continue
        visita = _escanear_visita(entrada)
        for aviso in visita["avisos"] + visita["interpretacion"]["avisos"]:
            avisos.append(f"visita '{visita['nombre_carpeta']}': {aviso}")
        visitas.append(visita)
    if not visitas:
        avisos.append(f"{PENDIENTE}: la carpeta '{carpeta}' no tiene carpetas de visita")
    return visitas


def _escanear_informes(carpeta: Path, avisos: List[str]) -> List[Dict]:
    if not _ruta_existe(carpeta):
        avisos.append(f"{PENDIENTE}: no existe la carpeta de informes procesados '{carpeta}'")
        return []
    entradas = _listar(carpeta, avisos)
    if entradas is None:
        return []
    return [
        {"nombre": e.name, "ruta": str(e)}
        for e in entradas
        if not _es_ignorado(e.name) and e.is_file()
    ]


def escanear_proyecto(carpeta_proyecto: Union[str, Path]) -> Dict:
    """Escanea en solo lectura la carpeta de un proyecto de Supervisión (§5.1).

    Devuelve:
      carpeta_proyecto, layout (LAYOUT_SUPERVISION | LAYOUT_NO_SOPORTADO | PENDIENTE),
      rutas ({planos_sellados, visitas, informes_procesados}: {ruta, existe}),
      planos_sellados [{nombre, ruta, tamano_bytes, mtime}],
      visitas [{nombre_carpeta, ruta_carpeta, archivos, sin_pdf, avisos, interpretacion}],
      informes_procesados [{nombre, ruta}],
      avisos (lista de textos; incluye los de cada visita con su nombre de carpeta).
    Nunca lanza excepción por rutas inexistentes o ilegibles.
    """
    carpeta = Path(carpeta_proyecto)
    ruta_planos = carpeta / SUBRUTA_PLANOS_SELLADOS
    ruta_visitas = carpeta / SUBRUTA_VISITAS
    ruta_informes = carpeta / SUBRUTA_INFORMES_PROCESADOS
    avisos: List[str] = []

    resultado = {
        "carpeta_proyecto": str(carpeta),
        "layout": PENDIENTE,
        "rutas": {
            "planos_sellados": {"ruta": str(ruta_planos), "existe": _ruta_existe(ruta_planos)},
            "visitas": {"ruta": str(ruta_visitas), "existe": _ruta_existe(ruta_visitas)},
            "informes_procesados": {"ruta": str(ruta_informes), "existe": _ruta_existe(ruta_informes)},
        },
        "planos_sellados": [],
        "visitas": [],
        "informes_procesados": [],
        "avisos": avisos,
    }

    if not _ruta_existe(carpeta):
        avisos.append(f"{PENDIENTE}: no existe la carpeta del proyecto '{carpeta}'")
        return resultado

    # Sin LEVANTAMIENTO\VISITA A OBRA no es el layout de Supervisión §5.1 (p. ej. P16, Zoetry)
    if not resultado["rutas"]["visitas"]["existe"]:
        resultado["layout"] = LAYOUT_NO_SOPORTADO
        avisos.append(
            f"layout {LAYOUT_NO_SOPORTADO}: no existe '{SUBRUTA_VISITAS}' dentro de '{carpeta}' "
            "(estructura distinta de CLAUDE.md 5.1); no se escanea"
        )
        return resultado

    resultado["layout"] = LAYOUT_SUPERVISION
    resultado["planos_sellados"] = _escanear_planos(ruta_planos, avisos)
    resultado["visitas"] = _escanear_visitas(ruta_visitas, avisos)
    resultado["informes_procesados"] = _escanear_informes(ruta_informes, avisos)
    return resultado
