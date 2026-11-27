"""Credenciales del administrador inicial para cuando el servicio queda publicado en un hosting.

Con ellas se activa la seguridad por usuario (ver ``sesion.py``): en una base nueva se crea el
administrador con ese usuario y esa clave. En local (sin variables) la seguridad queda apagada.
Con ``ANALISTA_PUBLICO=1`` exige que existan ``ACCESO_USUARIO`` y ``ACCESO_CLAVE``: si faltan, el
servicio no inicia, para no publicar por error un agente que consume la cuota del modelo sin protección.
"""
from __future__ import annotations

import os

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
