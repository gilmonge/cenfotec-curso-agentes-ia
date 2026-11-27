"""Contraseñas (PBKDF2) y tokens de sesión firmados (HMAC), solo con la biblioteca estándar."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

_ITERACION = 240_000
_DURACION_SESION_SEGUNDO = 12 * 60 * 60


def cifrar_clave(clave: str) -> str:
    sal = secrets.token_bytes(16)
    huella = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, _ITERACION)
    return f"pbkdf2_sha256${_ITERACION}${sal.hex()}${huella.hex()}"


def verificar_clave(clave: str, guardada: str | None) -> bool:
    try:
        algoritmo, iteracion, sal, huella = (guardada or "").split("$")
    except ValueError:
        return False
    if algoritmo != "pbkdf2_sha256":
        return False
    calculada = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), bytes.fromhex(sal), int(iteracion))
    return hmac.compare_digest(calculada.hex(), huella)


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode("ascii")


def _desde_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


class FirmaSesion:
    """Emite y valida tokens ``datos.firma``. El permiso se consulta en la base en cada solicitud,
    así que un cambio de roles aplica de inmediato; el token solo dice quién es la persona."""

    def __init__(self, secreto: str) -> None:
        self._secreto = hashlib.sha256(f"sesion:{secreto}".encode("utf-8")).digest()

    def _firmar(self, datos: str) -> str:
        return _b64(hmac.new(self._secreto, datos.encode("ascii"), hashlib.sha256).digest())

    def emitir(self, usuario_id: str, *, ahora: float | None = None) -> str:
        vence = int((ahora or time.time()) + _DURACION_SESION_SEGUNDO)
        datos = _b64(json.dumps({"u": usuario_id, "v": vence}).encode("utf-8"))
        return f"{datos}.{self._firmar(datos)}"

    def validar(self, token: str, *, ahora: float | None = None) -> str | None:
        datos, _, firma = (token or "").partition(".")
        if not datos or not firma or not hmac.compare_digest(firma, self._firmar(datos)):
            return None
        try:
            contenido = json.loads(_desde_b64(datos))
        except (ValueError, UnicodeDecodeError):
            return None
        if int(contenido.get("v", 0)) < (ahora or time.time()):
            return None
        return contenido.get("u")
