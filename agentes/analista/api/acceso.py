"""Acceso con usuario y clave compartida para cuando el servicio queda publicado en un hosting.

En local (sin variables) no hace nada. Con ``ANALISTA_PUBLICO=1`` exige que existan
``ACCESO_USUARIO`` y ``ACCESO_CLAVE``: si faltan, el servicio no inicia, para no publicar
por error un agente que consume la cuota del modelo sin ninguna protección.
"""
from __future__ import annotations

import base64
import binascii
import os
import secrets

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

RUTA_SALUD = "/healthz"


class ConfiguracionAccesoError(RuntimeError):
    """El servicio es público pero no tiene credenciales de acceso configuradas."""


def _entorno(nombre: str) -> str:
    return os.environ.get(nombre, "").strip()


def credenciales_desde_entorno() -> tuple[str, str] | None:
    usuario, clave = _entorno("ACCESO_USUARIO"), _entorno("ACCESO_CLAVE")
    publico = _entorno("ANALISTA_PUBLICO") in {"1", "true", "TRUE", "True"}
    if usuario and clave:
        return usuario, clave
    if publico:
        raise ConfiguracionAccesoError(
            "ANALISTA_PUBLICO está activo pero faltan ACCESO_USUARIO y ACCESO_CLAVE; el servicio no iniciará."
        )
    return None


class AccesoBasico:
    """Middleware ASGI: exige Authorization Basic en todo menos en ``/healthz``."""

    def __init__(self, app: ASGIApp, usuario: str, clave: str) -> None:
        self.app = app
        self._usuario = usuario.encode("utf-8")
        self._clave = clave.encode("utf-8")

    def _autorizado(self, encabezado: str) -> bool:
        esquema, _, valor = encabezado.partition(" ")
        if esquema.lower() != "basic" or not valor:
            return False
        try:
            usuario, _, clave = base64.b64decode(valor.strip(), validate=True).partition(b":")
        except (binascii.Error, ValueError):
            return False
        # Se evalúan ambas comparaciones siempre, para no revelar cuál falló.
        usuario_ok = secrets.compare_digest(usuario, self._usuario)
        clave_ok = secrets.compare_digest(clave, self._clave)
        return usuario_ok and clave_ok

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] == RUTA_SALUD:
            await self.app(scope, receive, send)
            return
        encabezados = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        if self._autorizado(encabezados.get("authorization", "")):
            await self.app(scope, receive, send)
            return
        respuesta = PlainTextResponse(
            "Acceso restringido.",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Historias de Usuario", charset="UTF-8"'},
        )
        await respuesta(scope, receive, send)
