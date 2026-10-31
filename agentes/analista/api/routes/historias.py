"""Historias de trabajo del equipo: se guardan en la base de datos y se comparten entre dispositivos."""
from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Body, Path, Request, Response, status

from agentes.analista.memory.repositorio import RepositorioError, RepositorioHU

router = APIRouter()

_ID = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
_MAX_BYTES = 200_000


def _repo(request: Request) -> RepositorioHU:
    return request.app.state.repositorio


@router.get("/historias")
def listar(request: Request) -> list[dict[str, Any]]:
    return _repo(request).listar_historias()


@router.put("/historias/{historia_id}")
def guardar(
    historia_id: Annotated[str, Path(pattern=_ID)],
    request: Request,
    datos: Annotated[dict[str, Any], Body()],
) -> dict[str, Any]:
    if str(datos.get("id", "")) != historia_id:
        raise RepositorioError("El identificador de la historia no coincide con la ruta.")
    if len(json.dumps(datos, ensure_ascii=False).encode("utf-8")) > _MAX_BYTES:
        raise RepositorioError("La historia es demasiado grande para guardarse.")
    return _repo(request).guardar_historia(historia_id, datos)


@router.delete("/historias/{historia_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(historia_id: Annotated[str, Path(pattern=_ID)], request: Request) -> Response:
    _repo(request).eliminar_historia(historia_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
