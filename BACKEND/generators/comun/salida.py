# BACKEND/generators/comun/salida.py
# Etapa 3 · T6 — Salida segura de los generadores (CLAUDE.md §5.2, error #15, P3, D1).
# - Escribe SOLO en la carpeta de salida configurada (config.obtener_salida_pruebas()); nunca en
#   Dropbox, ni siquiera si la carpeta configurada o pedida cae dentro de él.
# - Nunca sobrescribe: si el archivo existe, crea ` v2`, ` v3`...
# - Pasa auditar_archivo_pdf_generado (existencia, peso < 30 MB, sin sobrescritura).
# - Cada acción queda en `auditoria` con el usuario que ejecuta (D1), no uno fijo.
import getpass
from pathlib import Path
from typing import Dict, List, Optional, Union

import config
from database import registrar_auditoria
from reglas_ingenieria import PESO_MAXIMO_PDF_BYTES, auditar_archivo_pdf_generado, obtener_ruta_salida_sin_sobrescribir

MODULO_AUDITORIA = "GENERADORES"
ACCION_GUARDAR = "GUARDAR_PDF"
ACCION_RECHAZAR = "RECHAZAR_PDF"


class SalidaInvalida(ValueError):
    """La salida no cumple las reglas de §5.2 / P3; si ya se escribió el archivo, se retiró."""


def _dentro_de(ruta: Path, carpeta: Path) -> bool:
    try:
        ruta.resolve().relative_to(carpeta.resolve())
        return True
    except ValueError:
        return False


def resolver_carpeta_salida(carpeta: Optional[Union[str, Path]] = None) -> Path:
    """
    Carpeta de salida válida: la configurada, o una subcarpeta suya. Rechaza cualquier ruta dentro
    de Dropbox (P3: mientras se prueba no se escribe allí) y cualquiera fuera de la salida configurada.
    """
    base = config.obtener_salida_pruebas()
    destino = Path(carpeta) if carpeta is not None else base
    dropbox = config.obtener_dropbox_raiz()
    if _dentro_de(destino, dropbox) or _dentro_de(base, dropbox):
        raise SalidaInvalida(f"La salida '{destino}' está dentro de Dropbox ('{dropbox}'): los "
                             "generadores no escriben allí mientras se prueban (P3).")
    if not _dentro_de(destino, base):
        raise SalidaInvalida(f"La salida '{destino}' está fuera de la carpeta de salida configurada "
                             f"('{base}').")
    return destino


def guardar_pdf(nombre_base: str, contenido: bytes, carpeta: Optional[Union[str, Path]] = None,
                formato: str = "", entidad_id: str = "", usuario: Optional[str] = None) -> Dict:
    """
    Escribe `contenido` (bytes de un PDF) con un nombre nuevo (v2/v3 si ya existe) y lo audita.
    Devuelve {"ruta", "bytes", "version_nueva"}. Lanza SalidaInvalida si la carpeta no es válida o
    si el PDF no pasa la auditoría de §5.2 (en ese caso el archivo recién escrito se retira).
    """
    if not nombre_base or Path(nombre_base).name != nombre_base or not nombre_base.lower().endswith(".pdf"):
        raise SalidaInvalida(f"Nombre de salida inválido '{nombre_base}': debe ser un nombre de archivo .pdf, "
                             "sin carpetas.")
    usuario = usuario or getpass.getuser()
    destino = resolver_carpeta_salida(carpeta)
    ruta = obtener_ruta_salida_sin_sobrescribir(destino, nombre_base)
    existia_antes = ruta.exists()
    destino.mkdir(parents=True, exist_ok=True)
    with open(ruta, "xb") as f:  # "x": falla si el archivo apareció entre tanto; nunca sobrescribe
        f.write(contenido)

    errores: List[str] = auditar_archivo_pdf_generado(ruta, existia_antes)
    detalle = {"ruta": str(ruta), "bytes": len(contenido), "formato": formato,
               "limite_bytes": PESO_MAXIMO_PDF_BYTES, "existia_antes": existia_antes}
    entidad = entidad_id or ruta.name
    if errores:
        ruta.unlink()  # es el archivo que acabamos de crear con "x"
        registrar_auditoria(MODULO_AUDITORIA, ACCION_RECHAZAR, entidad, {**detalle, "errores": errores}, usuario)
        raise SalidaInvalida("; ".join(errores))
    registrar_auditoria(MODULO_AUDITORIA, ACCION_GUARDAR, entidad, detalle, usuario)
    return {"ruta": ruta, "bytes": len(contenido), "version_nueva": ruta.name != nombre_base}
