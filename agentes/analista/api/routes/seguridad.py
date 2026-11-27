"""Inicio de sesión y Mantenimiento: usuarios con sus roles y roles con sus acciones."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from agentes.analista.api.errors import WorkflowApiError
from agentes.analista.api.sesion import (
    requiere_accion, requiere_sesion, ruta_publica, seguridad_activa, usuario_actual, usuario_de_solicitud,
)
from agentes.analista.core.models import ErrorCode
from agentes.seguridad.catalogo import ACCION, LISTA_ACCION

router = APIRouter()


class InicioSesion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    usuario: str = Field(min_length=1, max_length=60)
    clave: str = Field(min_length=1, max_length=200)


class UsuarioNuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    usuario: str = Field(min_length=3, max_length=60)
    nombre: str = Field(min_length=1, max_length=120)
    clave: str = Field(min_length=8, max_length=200)
    roles: list[str] = Field(default_factory=list, max_length=50)


class UsuarioCambio(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str | None = Field(default=None, max_length=120)
    activo: bool | None = None
    clave: str | None = Field(default=None, max_length=200)
    roles: list[str] | None = Field(default=None, max_length=50)


class RolDatos(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str | None = Field(default=None, max_length=80)
    descripcion: str | None = Field(default=None, max_length=300)
    acciones: list[str] | None = Field(default=None, max_length=200)


def _seguridad(request: Request):
    repositorio = getattr(request.app.state, "seguridad", None)
    if repositorio is None:
        raise WorkflowApiError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            "La seguridad no está activa en este ambiente (falta ACCESO_USUARIO y ACCESO_CLAVE).",
            status_code=503,
        )
    return repositorio


def _sesion(request: Request, encontrado: dict[str, Any] | None) -> dict[str, Any]:
    return {"seguridad": seguridad_activa(request), "usuario": encontrado}


# --- Sesión ----------------------------------------------------------------
@router.get("/sesion", dependencies=[ruta_publica])
def leer_sesion(request: Request) -> dict[str, Any]:
    """Si la seguridad está activa y no hay sesión, ``usuario`` es null y la interfaz pide iniciar sesión."""
    return _sesion(request, usuario_de_solicitud(request))


@router.post("/sesion", dependencies=[ruta_publica])
def iniciar_sesion(body: InicioSesion, request: Request) -> dict[str, Any]:
    encontrado = _seguridad(request).autenticar(body.usuario, body.clave)
    if encontrado is None:
        raise WorkflowApiError(ErrorCode.SESION_REQUERIDA, "Usuario o contraseña incorrectos.", status_code=401)
    return {**_sesion(request, encontrado), "token": request.app.state.firma_sesion.emitir(encontrado["id"])}


@router.get("/sesion/aprobadores", dependencies=[requiere_sesion])
def listar_aprobador(request: Request) -> list[dict[str, str]]:
    """Personas que pueden aprobar historias (para indicar a quién le queda pendiente)."""
    if not seguridad_activa(request):
        return []
    return [{"id": u["id"], "nombre": u["nombre"]} for u in request.app.state.seguridad.listar_usuario()
            if u["activo"] and ACCION.HISTORIA_APROBAR in u["acciones"]]


# --- Mantenimiento ---------------------------------------------------------
@router.get("/mantenimiento/acciones", dependencies=[requiere_accion(ACCION.MANTENIMIENTO_VER)])
def listar_accion() -> list[dict[str, str]]:
    return [{"codigo": a.codigo, "nombre": a.nombre, "modulo": a.modulo} for a in LISTA_ACCION]


@router.get("/mantenimiento/usuarios", dependencies=[requiere_accion(ACCION.MANTENIMIENTO_VER)])
def listar_usuario(request: Request, busqueda: Annotated[str, Query(max_length=120)] = "") -> list[dict[str, Any]]:
    return _seguridad(request).listar_usuario(busqueda)


@router.post("/mantenimiento/usuarios", status_code=status.HTTP_201_CREATED,
             dependencies=[requiere_accion(ACCION.USUARIO_ADMINISTRAR)])
def crear_usuario(body: UsuarioNuevo, request: Request) -> dict[str, Any]:
    return _seguridad(request).crear_usuario(body.usuario, body.nombre, body.clave, body.roles)


@router.put("/mantenimiento/usuarios/{usuario_id}", dependencies=[requiere_accion(ACCION.USUARIO_ADMINISTRAR)])
def actualizar_usuario(
    usuario_id: str, body: UsuarioCambio, request: Request,
    actual: Annotated[dict[str, Any], Depends(usuario_actual)],
) -> dict[str, Any]:
    if usuario_id == actual["id"] and body.activo is False:
        raise WorkflowApiError(ErrorCode.INVALID_INPUT, "No puede desactivar su propio usuario.", status_code=400)
    return _seguridad(request).actualizar_usuario(
        usuario_id, nombre=body.nombre, activo=body.activo, clave=body.clave, lista_rol_id=body.roles)


@router.get("/mantenimiento/roles", dependencies=[requiere_accion(ACCION.MANTENIMIENTO_VER)])
def listar_rol(request: Request) -> list[dict[str, Any]]:
    return _seguridad(request).listar_rol()


@router.post("/mantenimiento/roles", status_code=status.HTTP_201_CREATED,
             dependencies=[requiere_accion(ACCION.ROL_ADMINISTRAR)])
def crear_rol(body: RolDatos, request: Request) -> dict[str, Any]:
    return _seguridad(request).crear_rol(body.nombre or "", body.descripcion or "", body.acciones or [])


@router.put("/mantenimiento/roles/{rol_id}", dependencies=[requiere_accion(ACCION.ROL_ADMINISTRAR)])
def actualizar_rol(rol_id: str, body: RolDatos, request: Request) -> dict[str, Any]:
    return _seguridad(request).actualizar_rol(
        rol_id, nombre=body.nombre, descripcion=body.descripcion, lista_accion=body.acciones)


@router.delete("/mantenimiento/roles/{rol_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[requiere_accion(ACCION.ROL_ADMINISTRAR)])
def eliminar_rol(rol_id: str, request: Request) -> None:
    _seguridad(request).eliminar_rol(rol_id)
