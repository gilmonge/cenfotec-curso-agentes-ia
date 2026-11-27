"""Pendientes de la persona: lo que espera su decisión y los avisos sobre sus historias.

- Espera su decisión: sale de los flujos guardados (``espera``) según las acciones de la persona:
  con «Aprobar historia», las historias por aprobar; con «Decidir sobre un cambio», los cambios por decidir.
- Avisos: su historia fue aprobada, devuelta (con el motivo) o rechazada. Se marcan como leídos.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request, status

from agentes.analista.api.sesion import requiere_sesion, usuario_actual
from agentes.seguridad.catalogo import ACCION

router = APIRouter()

_ID = r"^[0-9a-fA-F-]{36}$"
# Qué espera cada flujo → acción que hace falta para decidir y cómo se le llama a la persona.
_POR_DECIDIR = {
    "product_owner_approval": (ACCION.HISTORIA_APROBAR, "por_aprobar"),
    "change_decision": (ACCION.CAMBIO_DECIDIR, "cambio_por_decidir"),
}


def _repositorio(request: Request):
    return getattr(request.app.state, "repositorio", None)


@router.get("/pendientes", dependencies=[requiere_sesion])
def listar_pendiente(request: Request, usuario: Annotated[dict[str, Any], Depends(usuario_actual)]) -> dict[str, Any]:
    runtime = getattr(request.app.state, "workflow_runtime", None)
    lista_flujo = runtime.listar() if runtime is not None else []
    por_decidir = []
    for flujo in lista_flujo:
        regla = _POR_DECIDIR.get(flujo.get("espera") or "")
        if regla and regla[0] in usuario["acciones"]:
            por_decidir.append({
                "tipo": regla[1], "workflow_id": flujo["id"], "titulo": flujo.get("titulo") or "Sin título",
                "modo": flujo.get("modo"), "creado_por": flujo.get("creado_por"),
                "actualizado_en": flujo.get("actualizado_en"),
            })
    repositorio = _repositorio(request)
    avisos = repositorio.listar_aviso(usuario["id"]) if repositorio is not None else []
    return {"por_decidir": por_decidir, "avisos": avisos, "total": len(por_decidir) + len(avisos)}


@router.post("/pendientes/avisos/{aviso_id}/leido", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[requiere_sesion])
def marcar_leido(
    aviso_id: Annotated[str, Path(pattern=_ID)], request: Request,
    usuario: Annotated[dict[str, Any], Depends(usuario_actual)],
) -> None:
    repositorio = _repositorio(request)
    if repositorio is not None:
        repositorio.marcar_aviso_leido(aviso_id, usuario["id"])
