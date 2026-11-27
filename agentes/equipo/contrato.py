"""Contrato declarativo de un agente del equipo.

Cada agente vive en su carpeta ``agentes/equipo/<id>/`` y se declara con un ``DEFINICION`` en su
``definicion.py``. El registro (``agentes.equipo.listar_definicion``) los descubre solo: de esa declaración
salen el identificador del agente, su prompt, sus herramientas MCP permitidas, los namespaces de
conocimiento que puede leer, su servidor MCP y su descripción para OpenCode y para la Ayuda.

Este módulo no importa nada del resto del backend para que el registro no tenga dependencias circulares.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Literal

CARPETA_EQUIPO = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class PropiedadAgente:
    """Las cuatro propiedades de agente, en lenguaje de negocio (se muestran en la Ayuda)."""

    autonomia: str
    razonamiento: str
    herramienta: str
    memoria: str


@dataclass(frozen=True, slots=True)
class DefinicionAgente:
    """Declaración completa de un agente. Agregar un agente = crear su carpeta con esta declaración."""

    id: str  # nombre en opencode.jsonc y valor de AgentId (snake_case)
    constante: str  # nombre del miembro de AgentId (MAYÚSCULAS)
    nombre: str  # nombre visible: «Redactor-Revisor»
    orden: int  # orden en el flujo y en la Ayuda
    descripcion: str  # para el registro y OpenCode
    modo_opencode: Literal["primary", "subagent"]
    propiedad: PropiedadAgente
    # Herramientas MCP de solo lectura que el agente puede usar (mínimo privilegio).
    herramienta: frozenset[str]
    # Namespace de conocimiento → tipos de fuente que el agente puede leer en él.
    fuente: Mapping[str, frozenset[str]]
    maximo_ronda: int = 1  # rondas de consulta MCP por solicitud
    puede_consultar_asesor: bool = False
    # «modulo:funcion» que agrega herramientas propias del agente a su servidor MCP (opcional).
    herramienta_extra: str | None = None
    carpeta: Path = field(default=CARPETA_EQUIPO)

    def __post_init__(self) -> None:
        object.__setattr__(self, "fuente", MappingProxyType({k: frozenset(v) for k, v in self.fuente.items()}))
        object.__setattr__(self, "herramienta", frozenset(self.herramienta))
        object.__setattr__(self, "carpeta", CARPETA_EQUIPO / self.id)

    @property
    def ruta_prompt(self) -> Path:
        return self.carpeta / "prompt.md"

    @property
    def ruta_servidor_mcp(self) -> Path:
        return self.carpeta / "servidor_mcp.py"

    @property
    def namespace(self) -> frozenset[str]:
        return frozenset(self.fuente)
