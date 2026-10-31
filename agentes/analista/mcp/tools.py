"""The only four read-only tools exposed by the Analyst MCP server."""
from __future__ import annotations

import re
import unicodedata
from enum import StrEnum
from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentes.analista.mcp.repositories import load_sources


class Category(StrEnum):
    BUSINESS_RULES = "Reglas de negocio"
    REQUIRED_DATA = "Datos requeridos"
    VALIDATIONS = "Validaciones"
    EXCEPTIONS = "Excepciones"
    EXPECTED_BEHAVIOR = "Comportamiento esperado"


class ToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


class GlossaryResult(ToolModel):
    definiciones: list[GlossaryEntry] = Field(max_length=5)
    total: int = Field(ge=0, le=5)
    origen: Literal["simulado", "anonimizado"]
    contenido_no_confiable: Literal[True]

    @field_validator("total")
    @classmethod
    def total_matches_items(cls, total: int, info):
        items = info.data.get("definiciones")
        if items is not None and total != len(items):
            raise ValueError("total debe coincidir con definiciones")
        return total


class StoriesResult(ToolModel):
    historias: list[SimilarStory] = Field(max_length=5)
    total: int = Field(ge=0, le=5)
    origen: Literal["anonimizado"]
    contenido_no_confiable: Literal[True]

    @field_validator("total")
    @classmethod
    def total_matches_items(cls, total: int, info):
        items = info.data.get("historias")
        if items is not None and total != len(items):
            raise ValueError("total debe coincidir con historias")
        return total


class StandardsResult(ToolModel):
    estandares: list[StandardEntry] = Field(max_length=5)
    total: int = Field(ge=0, le=5)
    origen: Literal["simulado", "anonimizado"]
    contenido_no_confiable: Literal[True]

    @field_validator("total")
    @classmethod
    def total_matches_items(cls, total: int, info):
        items = info.data.get("estandares")
        if items is not None and total != len(items):
            raise ValueError("total debe coincidir con estandares")
        return total


class ChecklistResult(ToolModel):
    categorias: list[ChecklistCategory] = Field(max_length=5)
    total: int = Field(ge=0, le=25)
    origen: Literal["simulado"]
    contenido_no_confiable: Literal[True]

    @field_validator("total")
    @classmethod
    def total_matches_items(cls, total: int, info):
        categories = info.data.get("categorias")
        if categories is not None and total != sum(len(category.items) for category in categories):
            raise ValueError("total debe coincidir con los elementos del checklist")
        return total


_SOURCES = load_sources()
mcp = FastMCP("analista-fuentes")
_Consulta = Annotated[str, Field(min_length=1, max_length=4000)]
_Limite = Annotated[int, Field(ge=1, le=5)]


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_folded = "".join(char for char in normalized if not unicodedata.combining(char))
    return set(re.findall(r"[^\W_]+", ascii_folded, flags=re.UNICODE))


# Palabras vacías: sin ellas, un glosario o checklist grande coincidiría con cualquier consulta por «de», «la», «con»...
_STOPWORDS = frozenset((
    "a al algo ante aun como con contra cual cuando cada de del desde donde e el ella ellas ellos en entre era es esa ese eso esta este esto "
    "estos fue ha han hasta hay la las le les lo los mas me mi muy ni no nos o para pero por que se segun ser si sin sobre son su sus te "
    "tiene tienen todo tras un una uno unos y ya "
    "debe deben puede pueden hacer hace"
).split())


def _content_tokens(value: str) -> set[str]:
    return _tokens(value) - _STOPWORDS


def _validate_query(consulta: str) -> set[str]:
    if not isinstance(consulta, str) or not 1 <= len(consulta) <= 4000 or not consulta.strip():
        raise ValueError("consulta debe contener entre 1 y 4.000 caracteres no vacíos")
    return _tokens(consulta)


def _validate_limit(limite: int) -> None:
    if not isinstance(limite, int) or isinstance(limite, bool) or not 1 <= limite <= 5:
        raise ValueError("limite debe ser un entero entre 1 y 5")


def _matches(items: list[dict], query_tokens: set[str], text_keys: tuple[str, ...], limit: int) -> list[dict]:
    ranked: list[tuple[int, int, dict]] = []
    for index, item in enumerate(items):
        terms = set(item.get("terminos", []))
        text = " ".join(str(item.get(key, "")) for key in text_keys)
        score = len((query_tokens - _STOPWORDS) & (_content_tokens(text) | _content_tokens(" ".join(terms))))
        if score:
            ranked.append((score, index, item))
    ranked.sort(key=lambda entry: (-entry[0], entry[1]))
    return [item for _, _, item in ranked[:limit]]


@mcp.tool(name="consultar_glosario", title="Consultar glosario de negocio")
def consultar_glosario(consulta: _Consulta, limite: _Limite = 5) -> GlossaryResult:
    """Busca definiciones ficticias; no registra la consulta ni los resultados."""
    tokens = _validate_query(consulta)
    _validate_limit(limite)
    found = _matches(_SOURCES["glosario"], tokens, ("termino", "definicion"), limite)
    entries = [GlossaryEntry.model_validate({key: item[key] for key in GlossaryEntry.model_fields}) for item in found]
    return GlossaryResult(definiciones=entries, total=len(entries), origen="simulado", contenido_no_confiable=True)


@mcp.tool(name="buscar_hu_similares", title="Buscar historias de usuario similares")
def buscar_hu_similares(consulta: _Consulta, limite: _Limite = 5) -> StoriesResult:
    """Busca ejemplos ficticios o anonimizados, nunca reglas para el caso actual."""
    tokens = _validate_query(consulta)
    _validate_limit(limite)
    found = _matches(_SOURCES["historias"], tokens, ("titulo", "resumen", "aclaraciones"), limite)
    entries = [SimilarStory.model_validate({key: item[key] for key in SimilarStory.model_fields}) for item in found]
    return StoriesResult(historias=entries, total=len(entries), origen="anonimizado", contenido_no_confiable=True)


@mcp.tool(name="consultar_estandares", title="Consultar estándares internos")
def consultar_estandares(consulta: _Consulta, limite: _Limite = 5) -> StandardsResult:
    """Busca estándares ficticios que deben confirmarse con Negocio."""
    tokens = _validate_query(consulta)
    _validate_limit(limite)
    found = _matches(_SOURCES["estandares"], tokens, ("titulo", "regla", "referencia"), limite)
    entries = [StandardEntry.model_validate({key: item[key] for key in StandardEntry.model_fields}) for item in found]
    return StandardsResult(estandares=entries, total=len(entries), origen="simulado", contenido_no_confiable=True)


@mcp.tool(name="aplicar_checklist_vacios", title="Aplicar checklist de vacíos")
def aplicar_checklist_vacios(consulta: _Consulta, limite: _Limite = 5) -> ChecklistResult:
    """Devuelve preguntas de revisión de forma determinista, sin decidir por Negocio."""
    tokens = _validate_query(consulta)
    _validate_limit(limite)
    matches = _matches(_SOURCES["checklist"], tokens, ("categoria", "descripcion"), 25)
    grouped: dict[str, list[ChecklistItem]] = {category.value: [] for category in Category}
    for item in matches:
        category = item["categoria"]
        if len(grouped[category]) >= limite:
            continue
        grouped[category].append(
            ChecklistItem(
                id=item["id"],
                descripcion=item["descripcion"],
                aplica=True,
                evidencia=item.get("evidencia", "Coincidencia de términos en la consulta; requiere validación humana."),
            )
        )
    categories = [ChecklistCategory(categoria=category, items=items) for category, items in grouped.items() if items]
    total = sum(len(category.items) for category in categories)
    return ChecklistResult(categorias=categories, total=total, origen="simulado", contenido_no_confiable=True)
