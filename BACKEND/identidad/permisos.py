# backend/identidad/permisos.py
# Fundación F2 (contrato §4): funciones efectivas de un usuario en una obra, comprobadas en el servidor.
#
# Composición (rev. 2 y rev. 3):
#   - preparar, revisar_autorizar y administrar_obra incluyen consultar en esa obra;
#   - preparar y revisar_autorizar no se incluyen entre sí;
#   - administrar_obra no da preparar ni revisar_autorizar (no confirma revisiones, datos ni pedidos);
#   - no existe la función 'administrar': la base la rechaza (disparador) y, si apareciera, aquí no concede nada
#     ni se traduce a otra;
#   - es_admin NO da acceso a los datos técnicos de una obra: sin membresía, la obra no existe para él (404).
# Obra ajena o inexistente: 404 (no se confirma que exista). Obra propia sin la función pedida: 403.
import json
from typing import FrozenSet, Iterable, Optional, Set

from migracion_fundacion import FUNCIONES_OBRA

CONSULTAR = "consultar"
PREPARAR = "preparar"
REVISAR_AUTORIZAR = "revisar_autorizar"
ADMINISTRAR_OBRA = "administrar_obra"
INCLUYEN_CONSULTAR = frozenset({ADMINISTRAR_OBRA, PREPARAR, REVISAR_AUTORIZAR})


class SinAcceso(Exception):
    """La obra no existe para este usuario (404)."""


class FuncionInsuficiente(Exception):
    """El usuario ve la obra pero no tiene la función que pide la operación (403)."""


def componer(guardadas: Iterable) -> FrozenSet[str]:
    """Funciones efectivas a partir de las guardadas. Lo desconocido (p. ej. 'administrar') no concede nada."""
    validas = {f for f in guardadas if isinstance(f, str) and f in FUNCIONES_OBRA}
    if validas & INCLUYEN_CONSULTAR:
        validas.add(CONSULTAR)
    return frozenset(validas)


def _leer(texto: str) -> list:
    try:
        valor = json.loads(texto or "[]")
    except (TypeError, ValueError):
        return []
    return valor if isinstance(valor, list) else []


def funciones_efectivas(conn, usuario, obra_id: Optional[str]) -> FrozenSet[str]:
    """Funciones del usuario en la obra; vacío si no hay usuario, membresía u obra. Se lee en cada petición."""
    if usuario is None or getattr(usuario, "id", None) is None or obra_id is None:
        return frozenset()
    fila = conn.execute("""
        SELECT m.funciones FROM membresias m JOIN proyectos p ON p.id = m.obra_id
        JOIN usuarios u ON u.id = m.usuario_id
        WHERE m.usuario_id = ? AND m.obra_id = ? AND u.activo = 1
    """, (usuario.id, obra_id)).fetchone()
    return componer(_leer(fila["funciones"])) if fila else frozenset()


def obras_con(conn, usuario, funcion: str = CONSULTAR) -> Set[str]:
    """Ids de las obras donde el usuario tiene `funcion` (para filtrar listados)."""
    if usuario is None or getattr(usuario, "id", None) is None:
        return set()
    filas = conn.execute("""
        SELECT m.obra_id, m.funciones FROM membresias m JOIN proyectos p ON p.id = m.obra_id
        JOIN usuarios u ON u.id = m.usuario_id
        WHERE m.usuario_id = ? AND u.activo = 1
    """, (usuario.id,)).fetchall()
    return {f["obra_id"] for f in filas if funcion in componer(_leer(f["funciones"]))}


def exigir(conn, usuario, obra_id: Optional[str], funcion: str) -> FrozenSet[str]:
    """Lanza SinAcceso (404) o FuncionInsuficiente (403). Devuelve las funciones efectivas."""
    efectivas = funciones_efectivas(conn, usuario, obra_id)
    if not efectivas:
        raise SinAcceso(obra_id)
    if funcion not in efectivas:
        raise FuncionInsuficiente(funcion)
    return efectivas
