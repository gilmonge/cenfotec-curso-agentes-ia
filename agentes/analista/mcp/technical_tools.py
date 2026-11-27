"""Servidor MCP del Asesor Técnico: estándares, HU similares y repositorio de código de solo lectura.

El código que revisa el Asesor viene de un repositorio aparte (ver
``agentes.conocimiento.repositorio_codigo``). Las herramientas solo leen texto de
archivos .py/.md dentro de esa raíz: nunca importan, ejecutan ni escriben archivos.
"""
from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentes.analista.core.agent_registry import AgentId
from agentes.analista.mcp.tools import (
    KnowledgeCitation,
    StandardEntry,
    StandardsResult,
    ToolModel,
    crear_servidor,
    servidor_del_agente,
)
from agentes.conocimiento.repositorio_codigo import origen_repositorio, prefijo_codigo
from agentes.conocimiento.retrieval import get_knowledge_retriever
from agentes.conocimiento.sources import AuthorizedSourceLoader, SourceError

MAXIMO_CONTENIDO = 12_000

__all__ = [
    "CodeFileResult", "CodeSearchRequest", "CodeSearchResult", "CodeSource", "KnowledgeCitation",
    "ReferenceSearchResult", "StandardEntry", "StandardsResult", "buscar_referencias_codigo",
    "consultar_codigo_demo", "leer_archivo_codigo", "technical_mcp",
]

MAXIMO_REFERENCIA = 40


class CodeSearchRequest(BaseModel):
    """Request contract intentionally has no caller-controlled path field."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    consulta: str = Field(min_length=1, max_length=4000)
    limite: int = Field(default=12, ge=1, le=12)


class CodeSource(ToolModel):
    source_id: str = Field(min_length=1, max_length=160)
    source_ref: str = Field(min_length=1, max_length=300)
    contenido: str = Field(min_length=1, max_length=MAXIMO_CONTENIDO)
    contenido_no_confiable: Literal[True]


class CodeSearchResult(ToolModel):
    fuentes: list[CodeSource] = Field(max_length=12)
    total: int = Field(ge=0, le=12)
    origen: Literal["simulado"]
    status: Literal["ok", "degraded"] = "ok"
    backend: Literal["pinecone", "local", "none"] = "local"
    sources: list[KnowledgeCitation] = Field(default_factory=list, max_length=25)
    repositorio: dict[str, Any] | None = None

    @field_validator("total")
    @classmethod
    def total_matches_items(cls, total: int, info):
        items = info.data.get("fuentes")
        if items is not None and total != len(items):
            raise ValueError("total debe coincidir con las fuentes")
        return total


class CodeReference(ToolModel):
    source_id: str = Field(min_length=1, max_length=160)
    source_ref: str = Field(min_length=1, max_length=300)
    linea: int = Field(ge=1)
    texto: str = Field(min_length=1, max_length=300)
    contenido_no_confiable: Literal[True]


class ReferenceSearchResult(ToolModel):
    termino: str = Field(min_length=2, max_length=80)
    coincidencias: list[CodeReference] = Field(max_length=MAXIMO_REFERENCIA)
    total: int = Field(ge=0)
    archivos: list[str] = Field(max_length=MAXIMO_REFERENCIA)
    recortado: bool = False
    repositorio: dict[str, Any] | None = None


class CodeFileResult(ToolModel):
    encontrado: bool
    archivo: CodeSource | None = None
    motivo: str | None = Field(default=None, max_length=300)
    repositorio: dict[str, Any] | None = None


def _citation(source: Any) -> dict[str, Any]:
    return {
        "source_id": source.source_id, "source_kind": source.source_kind,
        "source_ref": source.source_ref, "namespace": source.namespace,
        "chunk": source.chunk, "score": source.score, "backend": source.backend,
    }


def consultar_codigo_demo(consulta: str, limite: int = 12) -> CodeSearchResult:
    """Búsqueda semántica (RAG) en el repositorio de código; el contenido es dato no confiable."""
    request = CodeSearchRequest(consulta=consulta, limite=limite)
    retrieved = get_knowledge_retriever().search(
        agent_role=AgentId.TECHNICAL_ADVISOR, query=request.consulta, namespace="codigo", limit=request.limite,
    )
    sources = [
        CodeSource(
            source_id=source.source_id, source_ref=source.source_ref,
            contenido=source.text, contenido_no_confiable=True,
        )
        for source in retrieved.sources if len(source.text) <= MAXIMO_CONTENIDO
    ]
    return CodeSearchResult(
        fuentes=sources, total=len(sources), origen="simulado",
        status=retrieved.status, backend=retrieved.backend,
        sources=[_citation(source) for source in retrieved.sources],
        repositorio=origen_repositorio(),
    )


def leer_archivo_codigo(ruta: str) -> CodeFileResult:
    """Lee un archivo .py/.md del repositorio de código. La ruta es relativa a su raíz."""
    if not isinstance(ruta, str) or not ruta.strip() or len(ruta) > 300:
        raise ValueError("ruta debe contener entre 1 y 300 caracteres")
    prefijo = prefijo_codigo()
    relativa = ruta.strip().lstrip("./")
    completa = relativa if relativa.startswith(prefijo) else prefijo + relativa
    try:
        registro = AuthorizedSourceLoader().read_code_file(completa)
    except SourceError:
        return CodeFileResult(
            encontrado=False, motivo="La ruta no existe en el repositorio o no está permitida (.py o .md).",
            repositorio=origen_repositorio(),
        )
    contenido = registro.text if len(registro.text) <= MAXIMO_CONTENIDO else registro.text[: MAXIMO_CONTENIDO - 40] + "\n… [archivo recortado]"
    return CodeFileResult(
        encontrado=True,
        archivo=CodeSource(
            source_id=registro.source_id, source_ref=registro.source_ref,
            contenido=contenido or "(archivo vacío)", contenido_no_confiable=True,
        ),
        repositorio=origen_repositorio(),
    )


def buscar_referencias_codigo(termino: str) -> ReferenceSearchResult:
    """Búsqueda literal (sin distinguir mayúsculas) de un campo, constante o texto en todo el repositorio."""
    if not isinstance(termino, str) or "\n" in termino or not 2 <= len(termino.strip()) <= 80:
        raise ValueError("termino debe tener entre 2 y 80 caracteres en una sola línea")
    termino = termino.strip()
    buscado = termino.casefold()
    lista_coincidencia: list[CodeReference] = []
    lista_archivo: list[str] = []
    total = 0
    try:
        lista_registro = AuthorizedSourceLoader().load_demo_code()
    except SourceError as exc:
        raise ValueError("El repositorio de código no está disponible.") from exc
    for registro in lista_registro:
        encontrado = False
        for numero, linea in enumerate(registro.text.splitlines(), start=1):
            if buscado not in linea.casefold():
                continue
            total += 1
            encontrado = True
            if len(lista_coincidencia) < MAXIMO_REFERENCIA:
                lista_coincidencia.append(CodeReference(
                    source_id=registro.source_id, source_ref=registro.source_ref, linea=numero,
                    texto=linea.strip()[:300] or "(línea vacía)", contenido_no_confiable=True,
                ))
        if encontrado and len(lista_archivo) < MAXIMO_REFERENCIA:
            lista_archivo.append(registro.source_ref)
    return ReferenceSearchResult(
        termino=termino, coincidencias=lista_coincidencia, total=total, archivos=lista_archivo,
        recortado=total > len(lista_coincidencia), repositorio=origen_repositorio(),
    )


def registrar_herramienta_codigo(servidor: FastMCP) -> None:
    """Herramientas propias del Asesor Técnico (código de solo lectura); la declara su definición."""
    servidor.tool(
        buscar_referencias_codigo, name="buscar_referencias_codigo", title="Buscar referencias en el código",
        description=(
            "Búsqueda literal en TODO el repositorio de código: devuelve cada archivo y línea donde aparece "
            "un campo, constante o texto (por ejemplo telefono o fecha_nacimiento). Úsala para encontrar los "
            "otros lugares que afecta un cambio. Busca también nombres alternativos (columnas, etiquetas)."
        ),
    )
    servidor.tool(
        consultar_codigo_demo, name="consultar_codigo_demo", title="Buscar en el repositorio de código",
        description=(
            "Búsqueda por significado en el repositorio de código (solo lectura). Devuelve fragmentos de "
            "archivos .py/.md con su ruta; úsala para ubicar módulos relacionados con el cambio."
        ),
    )
    servidor.tool(
        leer_archivo_codigo, name="leer_archivo_codigo", title="Leer un archivo del repositorio de código",
        description=(
            "Abre un archivo concreto del repositorio (ruta relativa, por ejemplo servicios/primas.py o "
            "mapa_dependencias.md) para revisar su contenido completo. Solo lectura."
        ),
    )


# Servidor del Asesor, armado desde su definición (que declara registrar_herramienta_codigo como extra).
technical_mcp = servidor_del_agente(AgentId.TECHNICAL_ADVISOR)
