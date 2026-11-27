"""Herramientas MCP de conocimiento (solo lectura) y fábrica de servidores por agente.

Todas las herramientas consultan el conocimiento a través del recuperador RAG
(Pinecone, o la copia local si Pinecone no responde). Cada agente tiene su propio
servidor MCP, y ese servidor solo expone las herramientas que el registro de
permisos le asigna: un agente no puede ver ni invocar herramientas ajenas.
"""
from __future__ import annotations

import importlib
import json
import logging
from collections.abc import Callable
from enum import StrEnum
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentes.analista.core.agent_registry import (
    AGENT_NAMESPACE_ALLOWLIST,
    MCP_TOOL_ALLOWLIST,
    AgentId,
    KnowledgeNamespace,
)
from agentes.conocimiento.retrieval import get_knowledge_retriever

logger = logging.getLogger(__name__)


class Category(StrEnum):
    BUSINESS_RULES = "Reglas de negocio"
    REQUIRED_DATA = "Datos requeridos"
    VALIDATIONS = "Validaciones"
    EXCEPTIONS = "Excepciones"
    EXPECTED_BEHAVIOR = "Comportamiento esperado"


class ToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeCitation(ToolModel):
    source_id: str = Field(min_length=1, max_length=300)
    source_kind: str = Field(min_length=1, max_length=40)
    source_ref: str = Field(min_length=1, max_length=300)
    namespace: str = Field(min_length=1, max_length=40)
    chunk: int = Field(ge=0)
    score: float
    backend: Literal["pinecone", "local"]


class GlossaryEntry(ToolModel):
    termino: str = Field(min_length=1, max_length=120)
    definicion: str = Field(min_length=1, max_length=800)
    fuente: str = Field(min_length=1, max_length=120)


class SimilarStory(ToolModel):
    id: str = Field(min_length=1, max_length=80)
    titulo: str = Field(min_length=1, max_length=200)
    resumen: str = Field(min_length=1, max_length=1000)
    aclaraciones: list[str] = Field(max_length=5)
    similitud: float = Field(ge=0, le=1)


class StandardEntry(ToolModel):
    id: str = Field(min_length=1, max_length=80)
    titulo: str = Field(min_length=1, max_length=200)
    regla: str = Field(min_length=1, max_length=1200)
    referencia: str = Field(min_length=1, max_length=200)


class ChecklistItem(ToolModel):
    id: str = Field(min_length=1, max_length=80)
    descripcion: str = Field(min_length=1, max_length=500)
    aplica: Literal[True]
    evidencia: str = Field(min_length=1, max_length=500)


class ChecklistCategory(ToolModel):
    categoria: Category
    items: list[ChecklistItem] = Field(max_length=5)


class LessonEntry(ToolModel):
    id: str = Field(min_length=1, max_length=80)
    categoria: str = Field(min_length=1, max_length=80)
    descripcion: str = Field(min_length=1, max_length=500)
    evidencia: str = Field(min_length=1, max_length=500)


class _ResultBase(ToolModel):
    origen: Literal["simulado", "anonimizado"]
    contenido_no_confiable: Literal[True]
    status: Literal["ok", "degraded"] = "ok"
    backend: Literal["pinecone", "local", "none"] = "local"
    sources: list[KnowledgeCitation] = Field(default_factory=list, max_length=25)


class GlossaryResult(_ResultBase):
    definiciones: list[GlossaryEntry] = Field(max_length=5)
    total: int = Field(ge=0, le=5)

    @field_validator("total")
    @classmethod
    def total_matches_items(cls, total: int, info):
        items = info.data.get("definiciones")
        if items is not None and total != len(items):
            raise ValueError("total debe coincidir con definiciones")
        return total


class StoriesResult(_ResultBase):
    historias: list[SimilarStory] = Field(max_length=5)
    total: int = Field(ge=0, le=5)

    @field_validator("total")
    @classmethod
    def total_matches_items(cls, total: int, info):
        items = info.data.get("historias")
        if items is not None and total != len(items):
            raise ValueError("total debe coincidir con historias")
        return total


class StandardsResult(_ResultBase):
    estandares: list[StandardEntry] = Field(max_length=5)
    total: int = Field(ge=0, le=5)

    @field_validator("total")
    @classmethod
    def total_matches_items(cls, total: int, info):
        items = info.data.get("estandares")
        if items is not None and total != len(items):
            raise ValueError("total debe coincidir con estandares")
        return total


class ChecklistResult(_ResultBase):
    categorias: list[ChecklistCategory] = Field(max_length=5)
    total: int = Field(ge=0, le=25)

    @field_validator("total")
    @classmethod
    def total_matches_items(cls, total: int, info):
        categories = info.data.get("categorias")
        if categories is not None and total != sum(len(category.items) for category in categories):
            raise ValueError("total debe coincidir con los elementos del checklist")
        return total


class LessonsResult(_ResultBase):
    lecciones: list[LessonEntry] = Field(max_length=5)
    total: int = Field(ge=0, le=5)

    @field_validator("total")
    @classmethod
    def total_matches_items(cls, total: int, info):
        items = info.data.get("lecciones")
        if items is not None and total != len(items):
            raise ValueError("total debe coincidir con lecciones")
        return total


_Consulta = Annotated[str, Field(min_length=1, max_length=4000, description="Texto a buscar en lenguaje natural.")]
_Limite = Annotated[int, Field(ge=1, le=5, description="Máximo de resultados (1 a 5).")]


def _validate_query(consulta: str) -> None:
    if not isinstance(consulta, str) or not 1 <= len(consulta) <= 4000 or not consulta.strip():
        raise ValueError("consulta debe contener entre 1 y 4.000 caracteres no vacíos")


def _validate_limit(limite: int) -> None:
    if not isinstance(limite, int) or isinstance(limite, bool) or not 1 <= limite <= 5:
        raise ValueError("limite debe ser un entero entre 1 y 5")


def _retrieved(
    agent_id: AgentId, namespace: str, consulta: str, limite: int,
) -> tuple[list[dict], str, str, list[dict]]:
    result = get_knowledge_retriever().search(
        agent_role=agent_id, query=consulta, namespace=namespace, limit=limite,
    )
    found: list[dict] = []
    for source in result.sources:
        try:
            item = json.loads(source.text)
        except (TypeError, json.JSONDecodeError) as exc:
            logger.warning("mcp_fuente_no_json", extra={"event": "mcp_fuente_no_json", "namespace": namespace, "error": type(exc).__name__})
            continue
        if isinstance(item, dict):
            found.append(item)
    citations = [
        {
            "source_id": source.source_id, "source_kind": source.source_kind,
            "source_ref": source.source_ref, "namespace": source.namespace,
            "chunk": source.chunk, "score": source.score, "backend": source.backend,
        }
        for source in result.sources
    ]
    return found, result.status, result.backend, citations


def _combine(statuses: set[str], backends: set[str]) -> tuple[str, str]:
    status = "degraded" if "degraded" in statuses else "ok"
    backend = "local" if "local" in backends else ("pinecone" if "pinecone" in backends else "none")
    return status, backend


def glosario(agent_id: AgentId, consulta: str, limite: int = 5) -> GlossaryResult:
    _validate_query(consulta)
    _validate_limit(limite)
    found, status, backend, sources = _retrieved(agent_id, "glosario", consulta, limite)
    entries = [GlossaryEntry.model_validate({key: item[key] for key in GlossaryEntry.model_fields}) for item in found]
    return GlossaryResult(definiciones=entries, total=len(entries), origen="simulado", contenido_no_confiable=True,
                          status=status, backend=backend, sources=sources)


def hu_similares(agent_id: AgentId, consulta: str, limite: int = 5) -> StoriesResult:
    _validate_query(consulta)
    _validate_limit(limite)
    found, status, backend, sources = _retrieved(agent_id, "hu_aprobadas", consulta, limite)
    entries = [SimilarStory.model_validate({key: item[key] for key in SimilarStory.model_fields}) for item in found]
    origin = "simulado" if any(item["source_kind"] == "simulated_reference" for item in sources) else "anonimizado"
    return StoriesResult(historias=entries, total=len(entries), origen=origin, contenido_no_confiable=True,
                         status=status, backend=backend, sources=sources)


def estandares(agent_id: AgentId, consulta: str, limite: int = 5) -> StandardsResult:
    _validate_query(consulta)
    _validate_limit(limite)
    found, status, backend, sources = _retrieved(agent_id, "estandares", consulta, limite)
    entries = [StandardEntry.model_validate({key: item[key] for key in StandardEntry.model_fields}) for item in found]
    return StandardsResult(estandares=entries, total=len(entries), origen="simulado", contenido_no_confiable=True,
                           status=status, backend=backend, sources=sources)


def checklist(agent_id: AgentId, consulta: str, limite: int = 5) -> ChecklistResult:
    """Checklist de vacíos; si el rol puede leer lecciones, suma las lecciones aprobadas."""
    _validate_query(consulta)
    _validate_limit(limite)
    matches, status_item, backend_item, sources = _retrieved(agent_id, "checklist", consulta, 25)
    statuses, backends = {status_item}, {backend_item}
    if KnowledgeNamespace.LESSONS in AGENT_NAMESPACE_ALLOWLIST[agent_id]:
        lesson_matches, lesson_status, lesson_backend, lesson_sources = _retrieved(agent_id, "lecciones", consulta, 25)
        matches = matches + lesson_matches
        sources = [*sources, *lesson_sources]
        statuses.add(lesson_status)
        backends.add(lesson_backend)
    matches = matches[:25]
    sources = sources[:25]
    status, backend = _combine(statuses, backends)
    grouped: dict[str, list[ChecklistItem]] = {category.value: [] for category in Category}
    for item in matches:
        category = item.get("categoria")
        if category not in grouped or len(grouped[category]) >= limite:
            continue
        grouped[category].append(ChecklistItem(
            id=item["id"],
            descripcion=item["descripcion"],
            aplica=True,
            evidencia=item.get("evidencia", "Coincidencia de términos en la consulta; requiere validación humana."),
        ))
    categories = [ChecklistCategory(categoria=category, items=items) for category, items in grouped.items() if items]
    total = sum(len(category.items) for category in categories)
    origin = "anonimizado" if any(item["source_kind"] == "approved_lesson" for item in sources) else "simulado"
    return ChecklistResult(categorias=categories, total=total, origen=origin, contenido_no_confiable=True,
                           status=status, backend=backend, sources=sources)


def lecciones(agent_id: AgentId, consulta: str, limite: int = 5) -> LessonsResult:
    _validate_query(consulta)
    _validate_limit(limite)
    found, status, backend, sources = _retrieved(agent_id, "lecciones", consulta, limite)
    entries = [LessonEntry.model_validate({key: item[key] for key in LessonEntry.model_fields}) for item in found]
    return LessonsResult(lecciones=entries, total=len(entries), origen="anonimizado", contenido_no_confiable=True,
                         status=status, backend=backend, sources=sources)


# nombre MCP → (función, título, descripción que lee el agente al planificar)
HERRAMIENTA_CONOCIMIENTO: dict[str, tuple[Callable[..., Any], str, str]] = {
    "consultar_glosario": (
        glosario, "Consultar glosario de negocio",
        "Definiciones ficticias de términos de seguros; sirve para confirmar el uso correcto de un término.",
    ),
    "buscar_hu_similares": (
        hu_similares, "Buscar historias de usuario similares",
        "Busca en el Repositorio de HU historias aprobadas o de ejemplo parecidas y lo que tuvieron que aclarar.",
    ),
    "consultar_estandares": (
        estandares, "Consultar estándares internos",
        "Reglas de desarrollo y de redacción que aplican al cambio; deben confirmarse con Negocio.",
    ),
    "aplicar_checklist_vacios": (
        checklist, "Aplicar checklist de vacíos",
        "Preguntas de revisión por categoría (estados, permisos, validaciones, excepciones, impacto en riesgo y comparativo).",
    ),
    "consultar_lecciones": (
        lecciones, "Consultar lecciones aprendidas",
        "Lecciones aprobadas de cambios anteriores (causas raíz) para no repetir el mismo vacío.",
    ),
}


def _registrar(servidor: FastMCP, agent_id: AgentId, nombre: str) -> None:
    funcion, titulo, descripcion = HERRAMIENTA_CONOCIMIENTO[nombre]

    def herramienta(consulta: _Consulta, limite: _Limite = 5):
        return funcion(agent_id, consulta, limite)

    herramienta.__name__ = nombre
    herramienta.__annotations__["return"] = funcion.__annotations__["return"]
    servidor.tool(herramienta, name=nombre, title=titulo, description=descripcion)


def crear_servidor(agent_id: AgentId, nombre: str, *, extra: Callable[[FastMCP], None] | None = None) -> FastMCP:
    """Servidor MCP de un rol: registra solo las herramientas de conocimiento que ese rol tiene permitidas."""
    servidor = FastMCP(nombre)
    permitido = MCP_TOOL_ALLOWLIST[agent_id]
    for nombre_herramienta in sorted(permitido & set(HERRAMIENTA_CONOCIMIENTO)):
        _registrar(servidor, agent_id, nombre_herramienta)
    if extra is not None:
        extra(servidor)
    return servidor


_SERVIDOR_CREADO: dict[str, FastMCP] = {}


def servidor_del_agente(agent_id: AgentId | str) -> FastMCP:
    """Servidor MCP de cualquier agente, armado desde su definición (herramientas y extras propios).

    Un agente nuevo no necesita código de servidor: basta con declarar sus herramientas en su definición.
    """
    from agentes.equipo import obtener_definicion

    definicion = obtener_definicion(str(agent_id))
    if definicion.id not in _SERVIDOR_CREADO:
        extra = None
        if definicion.herramienta_extra:
            modulo, funcion = definicion.herramienta_extra.split(":")
            extra = getattr(importlib.import_module(modulo), funcion)
        _SERVIDOR_CREADO[definicion.id] = crear_servidor(
            AgentId(definicion.id), f"{definicion.id.replace('_', '-')}-fuentes", extra=extra,
        )
    return _SERVIDOR_CREADO[definicion.id]


# Servidor del Analista (las pruebas importan ``mcp``).
mcp = servidor_del_agente(AgentId.ANALYST)


def consultar_glosario(consulta: str, limite: int = 5) -> GlossaryResult:
    """Busca definiciones ficticias; no registra la consulta ni los resultados."""
    return glosario(AgentId.ANALYST, consulta, limite)


def buscar_hu_similares(consulta: str, limite: int = 5) -> StoriesResult:
    """Busca ejemplos ficticios o anonimizados, nunca reglas para el caso actual."""
    return hu_similares(AgentId.ANALYST, consulta, limite)


def consultar_estandares(consulta: str, limite: int = 5) -> StandardsResult:
    """Busca estándares ficticios que deben confirmarse con Negocio."""
    return estandares(AgentId.ANALYST, consulta, limite)


def aplicar_checklist_vacios(consulta: str, limite: int = 5) -> ChecklistResult:
    """Devuelve preguntas de revisión de forma determinista, sin decidir por Negocio."""
    return checklist(AgentId.ANALYST, consulta, limite)
