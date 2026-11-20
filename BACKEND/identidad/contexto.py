# backend/identidad/contexto.py
# Fundación F2: quién hace la petición, disponible para todo el código de la petición (auditoría incluida).
#
# La guardia de la API (identidad/guardia.py) fija el usuario autenticado al empezar cada petición. El código que
# escribe en `auditoria` no necesita recibirlo: get_connection() instala en cada conexión un disparador TEMPORAL
# que copia el usuario del contexto en la fila nueva, dentro de la misma transacción (contrato §1, mutaciones
# atómicas). Fuera de una petición (scripts locales, arranque, migraciones) no hay usuario y las filas se escriben
# como hasta ahora.
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Usuario:
    id: Optional[int]
    usuario: str                 # el nombre de entrada (login)
    nombre_visible: str = ""
    es_admin: bool = False
    sesion_id: Optional[int] = None


_usuario_actual: ContextVar[Optional[Usuario]] = ContextVar("catdic_usuario_actual", default=None)


def fijar(usuario: Optional[Usuario]):
    """Fija el usuario de la petición; devuelve el token para restaurarlo (pruebas y hilos)."""
    return _usuario_actual.set(usuario)


def restaurar(token) -> None:
    _usuario_actual.reset(token)


def actual() -> Optional[Usuario]:
    return _usuario_actual.get()


def usuario_id() -> Optional[int]:
    u = _usuario_actual.get()
    return u.id if u else None


def login() -> Optional[str]:
    u = _usuario_actual.get()
    return u.usuario if u else None
