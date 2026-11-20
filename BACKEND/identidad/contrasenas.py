# backend/identidad/contrasenas.py
# Fundación F2 (contrato §4.1): contraseñas con hashlib.scrypt, con su sal y sus parámetros. Biblioteca estándar.
# Formato guardado: scrypt$<n>$<r>$<p>$<sal_b64>$<hash_b64>. Nunca se guarda ni se devuelve la contraseña.
import base64
import hashlib
import hmac
import secrets

N, R, P = 2 ** 14, 8, 1        # parámetros recomendados para uso interactivo (~16 MiB de memoria)
LARGO_HASH = 32
LARGO_SAL = 16
MAXMEM = 64 * 1024 * 1024
MINIMO_CARACTERES = 10


class ContrasenaInvalida(ValueError):
    """La contraseña no cumple el mínimo."""


def validar_nueva(contrasena: str) -> None:
    if not isinstance(contrasena, str) or len(contrasena) < MINIMO_CARACTERES:
        raise ContrasenaInvalida(f"La contraseña debe tener al menos {MINIMO_CARACTERES} caracteres.")


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def generar_hash(contrasena: str) -> str:
    validar_nueva(contrasena)
    sal = secrets.token_bytes(LARGO_SAL)
    h = hashlib.scrypt(contrasena.encode("utf-8"), salt=sal, n=N, r=R, p=P, maxmem=MAXMEM, dklen=LARGO_HASH)
    return f"scrypt${N}${R}${P}${_b64(sal)}${_b64(h)}"


def verificar(contrasena: str, guardado: str) -> bool:
    """True si la contraseña corresponde al hash guardado. Un hash con otro formato nunca coincide."""
    try:
        esquema, n, r, p, sal, h = guardado.split("$")
        if esquema != "scrypt":
            return False
        esperado = base64.b64decode(h)
        calculado = hashlib.scrypt((contrasena or "").encode("utf-8"), salt=base64.b64decode(sal), n=int(n),
                                   r=int(r), p=int(p), maxmem=MAXMEM, dklen=len(esperado))
    except (ValueError, TypeError, AttributeError):
        return False
    return hmac.compare_digest(calculado, esperado)


# Hash de relleno: si el usuario no existe se verifica contra él, para que el tiempo de respuesta no revele
# qué nombres de usuario existen.
_HASH_RELLENO = None


def hash_relleno() -> str:
    global _HASH_RELLENO
    if _HASH_RELLENO is None:
        _HASH_RELLENO = generar_hash(secrets.token_urlsafe(24))
    return _HASH_RELLENO
