# backend/config.py
# Configuración única del backend (§1.2 desacoplado, §1.3 rutas locales de Dropbox).
# Las rutas se leen de aquí; ningún otro módulo debe quemarlas.
#
# Variables de entorno (se leen en tiempo de llamada, no al importar):
#   CATDIC_DROPBOX_RAIZ -> raíz local de Dropbox
#   CATDIC_DB_PATH      -> archivo SQLite de la aplicación
import os
from pathlib import Path

# Valores por defecto (PC de Steven)
DROPBOX_RAIZ = Path(r"C:\Users\Steve\CATDIC Dropbox")
DB_PATH = Path(__file__).parent / "catdic_local.db"

ENV_DROPBOX_RAIZ = "CATDIC_DROPBOX_RAIZ"
ENV_DB_PATH = "CATDIC_DB_PATH"


def obtener_dropbox_raiz() -> Path:
    """Raíz de Dropbox: variable de entorno si existe; si no, el valor por defecto."""
    valor = os.environ.get(ENV_DROPBOX_RAIZ, "").strip()
    return Path(valor) if valor else Path(DROPBOX_RAIZ)


def obtener_db_path() -> Path:
    """Ruta de la BD: variable de entorno si existe; si no, el valor por defecto."""
    valor = os.environ.get(ENV_DB_PATH, "").strip()
    return Path(valor) if valor else Path(DB_PATH)


# Etapa 3 · T6 (D1): carpeta de salida de pruebas de los generadores. Nada fijo al usuario:
# variable de entorno CATDIC_SALIDA_PRUEBAS o, si no existe, <carpeta del usuario>\CATDIC-SALIDA-PRUEBAS.
ENV_SALIDA_PRUEBAS = "CATDIC_SALIDA_PRUEBAS"


def obtener_salida_pruebas() -> Path:
    """Carpeta donde los generadores escriben mientras se prueban (nunca Dropbox, P3)."""
    valor = os.environ.get(ENV_SALIDA_PRUEBAS, "").strip()
    return Path(valor) if valor else Path.home() / "CATDIC-SALIDA-PRUEBAS"


# Etapa 2 · T4n: carpeta local de las obras (planos subidos, visitas subidas). Nada fijo al usuario ni en Dropbox:
# variable de entorno CATDIC_DATOS_RAIZ o, si no existe, <carpeta del usuario>\CATDIC-DATOS.
ENV_DATOS_RAIZ = "CATDIC_DATOS_RAIZ"


class CarpetaDatosInvalida(ValueError):
    """La carpeta de datos cae dentro de Dropbox o del repositorio."""


def _carpeta_local_valida(valor_env: str, por_defecto: str, variable: str, que: str) -> Path:
    """Resuelve una carpeta local y la rechaza si cae dentro de Dropbox o del repositorio (git)."""
    valor = os.environ.get(valor_env, "").strip()
    raiz = (Path(valor) if valor else Path.home() / por_defecto).resolve()
    repo = Path(__file__).resolve().parent.parent
    dropbox = obtener_dropbox_raiz().resolve()
    for prohibida, nombre in ((dropbox, "Dropbox"), (repo, "el repositorio")):
        if raiz == prohibida or prohibida in raiz.parents:
            raise CarpetaDatosInvalida(
                f"La carpeta {que} '{raiz}' está dentro de {nombre}; define {variable} en otra ubicación.")
    if any("dropbox" in parte.lower() for parte in raiz.parts):
        raise CarpetaDatosInvalida(f"La carpeta {que} '{raiz}' parece estar dentro de Dropbox; usa otra ubicación.")
    return raiz


def obtener_datos_raiz() -> Path:
    """Carpeta de datos de las obras. Se rechaza si cae dentro de Dropbox o del repositorio (git)."""
    return _carpeta_local_valida(ENV_DATOS_RAIZ, "CATDIC-DATOS", ENV_DATOS_RAIZ, "de datos")


# Etapa 2 · T5n: caché local de las páginas rasterizadas del visor (prescindible: se puede borrar). Misma regla.
ENV_CACHE_RAIZ = "CATDIC_CACHE_RAIZ"


def obtener_cache_raiz() -> Path:
    """Caché de imágenes del visor: CATDIC_CACHE_RAIZ o <carpeta del usuario>/CATDIC-CACHE; nunca Dropbox ni el repo."""
    return _carpeta_local_valida(ENV_CACHE_RAIZ, "CATDIC-CACHE", ENV_CACHE_RAIZ, "de caché")
