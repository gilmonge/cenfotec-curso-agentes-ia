"""Quién hace la solicitud y qué acciones tiene. Cada ruta de la API declara una de estas dependencias:

- ``requiere_accion(ACCION.X, ...)``: la persona necesita al menos una de esas acciones.
- ``requiere_sesion``: basta con haber iniciado sesión.
- ``ruta_publica``: no pide sesión (salud del servicio e inicio de sesión).

La prueba de estructura revisa que ninguna ruta de ``/api`` quede sin declarar.

Sin ``ACCESO_USUARIO`` y ``ACCESO_CLAVE`` (desarrollo local y pruebas) la seguridad está apagada y la
solicitud se atiende como un usuario local con todas las acciones.
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, Request

from agentes.analista.api.errors import WorkflowApiError
from agentes.analista.core.models import ErrorCode
from agentes.seguridad.catalogo import CODIGO_ACCION, accion_de

USUARIO_LOCAL: dict[str, Any] = {
    "id": "local", "usuario": "local", "nombre": "", "activo": True, "roles": [],
    "acciones": sorted(CODIGO_ACCION),
}


def seguridad_activa(request: Request) -> bool:
    return getattr(request.app.state, "seguridad", None) is not None


def _token(request: Request) -> str:
    esquema, _, valor = request.headers.get("authorization", "").partition(" ")
    return valor.strip() if esquema.lower() == "bearer" else ""


def usuario_de_solicitud(request: Request) -> dict[str, Any] | None:
    """El usuario de la sesión, o None si no hay sesión válida. Sin seguridad, el usuario local."""
    if not seguridad_activa(request):
        return USUARIO_LOCAL
    usuario_id = request.app.state.firma_sesion.validar(_token(request))
    if not usuario_id:
        return None
    encontrado = request.app.state.seguridad.obtener_usuario(usuario_id)
    if encontrado is None or not encontrado["activo"]:
        return None
    return encontrado


def _exigir_sesion(request: Request) -> dict[str, Any]:
    encontrado = usuario_de_solicitud(request)
    if encontrado is None:
        raise WorkflowApiError(ErrorCode.SESION_REQUERIDA, "Su sesión no es válida o venció. Inicie sesión de nuevo.",
                               status_code=401)
    request.state.usuario = encontrado
    return encontrado


def exigir_accion(usuario: dict[str, Any], *lista_codigo: str) -> None:
    """Para decisiones que dependen del contenido de la solicitud (por ejemplo, aprobar o devolver)."""
    if not any(codigo in usuario["acciones"] for codigo in lista_codigo):
        nombre = accion_de(lista_codigo[0]).nombre
        raise WorkflowApiError(ErrorCode.PERMISO_DENEGADO, f"No tiene permiso para «{nombre}».", status_code=403)


def requiere_accion(*lista_codigo: str):
    desconocida = set(lista_codigo) - CODIGO_ACCION
    if not lista_codigo or desconocida:
        raise ValueError(f"Acción fuera del catálogo: {sorted(desconocida)}")

    def verificar(request: Request) -> dict[str, Any]:
        encontrado = _exigir_sesion(request)
        exigir_accion(encontrado, *lista_codigo)
        return encontrado

    verificar.acciones = tuple(lista_codigo)
    return Depends(verificar)


def _solo_sesion(request: Request) -> dict[str, Any]:
    return _exigir_sesion(request)


_solo_sesion.acciones = ()
requiere_sesion = Depends(_solo_sesion)


def _publica() -> None:
    return None


_publica.publica = True
ruta_publica = Depends(_publica)


def usuario_actual(request: Request) -> dict[str, Any]:
    """El usuario que ya validó la dependencia de la ruta."""
    return getattr(request.state, "usuario", None) or _exigir_sesion(request)
