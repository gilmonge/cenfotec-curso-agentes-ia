"""Registro de agentes: se arma solo a partir de las carpetas de ``agentes/equipo``.

Nada de este archivo se edita para agregar un agente. Cada agente declara en su ``definicion.py`` su prompt,
herramientas MCP, namespaces de conocimiento, rondas y si puede consultar al Asesor; aquí solo se derivan
las tablas que usa el backend y las validaciones de permisos (mínimo privilegio).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

from agentes.analista.core.prompt_loader import PromptSnapshot, load_prompt
from agentes.equipo import DefinicionAgente, listar_definicion, obtener_definicion


# Identificadores de los agentes, generados desde las definiciones (AgentId.ANALYST == "analista").
AgentId = StrEnum("AgentId", [(definicion.constante, definicion.id) for definicion in listar_definicion()])
AgentId.__doc__ = "Identificador de cada agente del equipo; se genera desde agentes/equipo/<id>/definicion.py."


class KnowledgeNamespace(StrEnum):
    GLOSSARY = "glosario"
    STANDARDS = "estandares"
    CHECKLIST = "checklist"
    APPROVED_STORIES = "hu_aprobadas"
    LESSONS = "lecciones"
    CODE = "codigo"


class AgentPermissionError(PermissionError):
    """A role tried to use an unassigned MCP tool or knowledge namespace."""


@dataclass(frozen=True, slots=True)
class AgentSpec:
    agent_id: AgentId
    prompt_path: Path
    description: str

    @property
    def prompt(self) -> PromptSnapshot:
        return load_prompt(self.prompt_path)


def definicion_de(agent_id: AgentId | str) -> DefinicionAgente:
    return obtener_definicion(str(agent_id))


_LISTA_DEFINICION: Final = listar_definicion()

AGENT_SPECS: Final[dict[AgentId, AgentSpec]] = {
    AgentId(definicion.id): AgentSpec(AgentId(definicion.id), definicion.ruta_prompt, definicion.descripcion)
    for definicion in _LISTA_DEFINICION
}

# Cada agente solo ve en su servidor MCP las herramientas de su definición (mínimo privilegio).
MCP_TOOL_ALLOWLIST: Final[dict[AgentId, frozenset[str]]] = {
    AgentId(definicion.id): definicion.herramienta for definicion in _LISTA_DEFINICION
}

AGENT_NAMESPACE_ALLOWLIST: Final[dict[AgentId, frozenset[KnowledgeNamespace]]] = {
    AgentId(definicion.id): frozenset(KnowledgeNamespace(namespace) for namespace in definicion.namespace)
    for definicion in _LISTA_DEFINICION
}

_TOOL_NAMESPACE: Final[dict[str, KnowledgeNamespace]] = {
    "consultar_glosario": KnowledgeNamespace.GLOSSARY,
    "consultar_estandares": KnowledgeNamespace.STANDARDS,
    "aplicar_checklist_vacios": KnowledgeNamespace.CHECKLIST,
    "buscar_hu_similares": KnowledgeNamespace.APPROVED_STORIES,
    "consultar_lecciones": KnowledgeNamespace.LESSONS,
    "consultar_codigo_demo": KnowledgeNamespace.CODE,
    "leer_archivo_codigo": KnowledgeNamespace.CODE,
    "buscar_referencias_codigo": KnowledgeNamespace.CODE,
}

# Roles que pueden pedir criterio técnico al Asesor durante su propio ciclo.
ASESOR_CONSULTABLE_POR: Final[frozenset[AgentId]] = frozenset(
    AgentId(definicion.id) for definicion in _LISTA_DEFINICION if definicion.puede_consultar_asesor
)

# Rondas máximas de consulta por agente (límite de pasos por solicitud).
MAXIMO_RONDA_HERRAMIENTA: Final[dict[AgentId, int]] = {
    AgentId(definicion.id): definicion.maximo_ronda for definicion in _LISTA_DEFINICION
}


def tool_namespace(tool_name: str) -> KnowledgeNamespace | None:
    return _TOOL_NAMESPACE.get(tool_name)


def puede_consultar_asesor(agent_id: AgentId | str) -> bool:
    try:
        resolved = agent_id if isinstance(agent_id, AgentId) else AgentId(agent_id)
    except (TypeError, ValueError):
        return False
    return resolved in ASESOR_CONSULTABLE_POR


def get_agent_spec(agent_id: AgentId | str) -> AgentSpec:
    """Resolve a configured role or fail; never substitute the Analyst."""
    try:
        resolved = agent_id if isinstance(agent_id, AgentId) else AgentId(agent_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Identificador de agente desconocido.") from exc
    return AGENT_SPECS[resolved]


def allowed_mcp_tools(agent_id: AgentId | str) -> frozenset[str]:
    try:
        resolved = agent_id if isinstance(agent_id, AgentId) else AgentId(agent_id)
    except (TypeError, ValueError) as exc:
        raise AgentPermissionError("El rol no está autorizado para invocar herramientas MCP.") from exc
    return MCP_TOOL_ALLOWLIST[resolved]


def authorize_mcp_tool(
    agent_id: AgentId | str,
    tool_name: str,
    namespace: KnowledgeNamespace | str | None = None,
) -> bool:
    """Validate a backend MCP invocation, including role-specific namespace."""
    try:
        resolved = agent_id if isinstance(agent_id, AgentId) else AgentId(agent_id)
        tools = MCP_TOOL_ALLOWLIST[resolved]
        namespaces = AGENT_NAMESPACE_ALLOWLIST[resolved]
    except (TypeError, ValueError) as exc:
        raise AgentPermissionError("El rol no está autorizado para invocar herramientas MCP.") from exc

    if tool_name not in tools:
        raise AgentPermissionError("La herramienta MCP no está permitida para este rol.")
    if namespace is not None:
        try:
            resolved_namespace = (
                namespace if isinstance(namespace, KnowledgeNamespace) else KnowledgeNamespace(namespace)
            )
        except (TypeError, ValueError) as exc:
            raise AgentPermissionError("El namespace solicitado no está permitido.") from exc
        if resolved_namespace not in namespaces:
            raise AgentPermissionError("El namespace solicitado no está permitido para este rol.")
        tool_namespace = _TOOL_NAMESPACE.get(tool_name)
        if tool_namespace is None or resolved_namespace != tool_namespace:
            raise AgentPermissionError("La herramienta no puede acceder al namespace solicitado.")
    return True
