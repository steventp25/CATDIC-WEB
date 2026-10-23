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
