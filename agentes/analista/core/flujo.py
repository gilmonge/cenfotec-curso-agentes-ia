"""Flujo declarativo: el grafo de LangGraph se arma desde una tabla de pasos.

Cada ``Paso`` dice su nombre, qué nodo ejecuta y a dónde sigue: a un paso fijo o, con ``Ruta``, al que
decida una función sobre el estado. Agregar un agente al flujo es agregar su ``Paso`` y cambiar a dónde
sigue el paso anterior; ``construir_flujo`` valida que todos los destinos existan antes de compilar.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, START, StateGraph

FIN = END  # destino especial: el flujo termina


class FlujoInvalidoError(ValueError):
    """La tabla del flujo tiene pasos repetidos, destinos inexistentes o pasos inalcanzables."""


@dataclass(frozen=True, slots=True)
class Ruta:
    """Siguiente paso según el estado: ``decidir`` devuelve una clave de ``destino``."""

    decidir: Callable[[Mapping[str, Any]], str]
    destino: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Paso:
    nombre: str
    nodo: Callable[..., Any]
    siguiente: str | Ruta  # nombre del paso siguiente, FIN, o una Ruta
    descripcion: str = ""


def _destino_de(siguiente: str | Ruta) -> set[str]:
    return set(siguiente.destino.values()) if isinstance(siguiente, Ruta) else {siguiente}


def validar_flujo(inicio: Ruta, lista_paso: Sequence[Paso]) -> None:
    nombre = [paso.nombre for paso in lista_paso]
    if len(nombre) != len(set(nombre)):
        raise FlujoInvalidoError("Hay pasos repetidos en el flujo.")
    existente = set(nombre) | {FIN}
    for origen, siguiente in [("inicio", inicio), *((paso.nombre, paso.siguiente) for paso in lista_paso)]:
        faltante = _destino_de(siguiente) - existente
        if faltante:
            raise FlujoInvalidoError(f"El paso «{origen}» lleva a pasos que no existen: {sorted(faltante)}.")
    alcanzable: set[str] = set()
    pendiente = list(_destino_de(inicio))
    por_nombre = {paso.nombre: paso for paso in lista_paso}
    while pendiente:
        actual = pendiente.pop()
        if actual == FIN or actual in alcanzable:
            continue
        alcanzable.add(actual)
        pendiente.extend(_destino_de(por_nombre[actual].siguiente))
    inalcanzable = set(nombre) - alcanzable
    if inalcanzable:
        raise FlujoInvalidoError(f"Hay pasos a los que nunca se llega: {sorted(inalcanzable)}.")


def construir_flujo(estado: type, inicio: Ruta, lista_paso: Sequence[Paso], *, checkpointer: Any):
    """Valida la tabla y compila el grafo con el ``checkpointer`` (los puntos de control para retomar)."""
    validar_flujo(inicio, lista_paso)
    builder = StateGraph(estado)
    for paso in lista_paso:
        builder.add_node(paso.nombre, paso.nodo)
    builder.add_conditional_edges(START, inicio.decidir, dict(inicio.destino))
    for paso in lista_paso:
        if isinstance(paso.siguiente, Ruta):
            builder.add_conditional_edges(paso.nombre, paso.siguiente.decidir, dict(paso.siguiente.destino))
        else:
            builder.add_edge(paso.nombre, paso.siguiente)
    return builder.compile(checkpointer=checkpointer)
