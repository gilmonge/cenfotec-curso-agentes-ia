"""Equipo de agentes: una carpeta por agente, descubierta automáticamente.

Para agregar un agente no se edita este archivo: basta con crear ``agentes/equipo/<id>/`` con su
``definicion.py`` (un ``DEFINICION = DefinicionAgente(...)``), su ``prompt.md`` y su ``servidor_mcp.py``.
Ver la guía ``docs/arquitectura.md`` y la skill ``agregar-agente``.
"""
from __future__ import annotations

import importlib
import pkgutil
from functools import cache

from agentes.equipo.contrato import CARPETA_EQUIPO, DefinicionAgente, PropiedadAgente

__all__ = ["DefinicionAgente", "PropiedadAgente", "listar_definicion", "obtener_definicion"]


class DefinicionInvalidaError(RuntimeError):
    """Una carpeta del equipo no cumple el contrato (falta su DEFINICION o está duplicada)."""


@cache
def listar_definicion() -> tuple[DefinicionAgente, ...]:
    """Todas las definiciones del equipo, en el orden del flujo."""
    lista_definicion: list[DefinicionAgente] = []
    for modulo in pkgutil.iter_modules([str(CARPETA_EQUIPO)]):
        if not modulo.ispkg or modulo.name.startswith("_"):
            continue
        definicion = getattr(importlib.import_module(f"agentes.equipo.{modulo.name}.definicion"), "DEFINICION", None)
        if not isinstance(definicion, DefinicionAgente):
            raise DefinicionInvalidaError(f"La carpeta del agente «{modulo.name}» no declara DEFINICION.")
        if definicion.id != modulo.name:
            raise DefinicionInvalidaError(f"El id «{definicion.id}» no coincide con su carpeta «{modulo.name}».")
        lista_definicion.append(definicion)
    for campo in ("id", "constante", "orden"):
        valor = [getattr(definicion, campo) for definicion in lista_definicion]
        if len(valor) != len(set(valor)):
            raise DefinicionInvalidaError(f"Hay agentes con el mismo «{campo}».")
    return tuple(sorted(lista_definicion, key=lambda definicion: definicion.orden))


def obtener_definicion(agente_id: str) -> DefinicionAgente:
    for definicion in listar_definicion():
        if definicion.id == str(agente_id):
            return definicion
    raise KeyError(agente_id)
