"""Strict parser and normalizer for the Analyst's JSON-only model output."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator
from langchain_core.output_parsers import PydanticOutputParser

from agentes.analista.core.models import Analysis, QuestionCategory, QuestionState


class AgentQuestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: QuestionCategory
    pregunta: str = Field(min_length=1, max_length=500)
    estado: QuestionState = QuestionState.PENDING

    @field_validator("pregunta")
    @classmethod
    def require_non_blank_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La pregunta no puede estar vacía")
        return value.strip()


class AgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    respuesta_markdown: str = Field(min_length=1, max_length=50_000)
    analisis: Analysis
    preguntas: list[AgentQuestionOutput] = Field(max_length=50)
    listo_para_redactor: bool

    @field_validator("respuesta_markdown")
    @classmethod
    def require_non_blank_answer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La respuesta no puede estar vacía")
        return value.strip()


_PARSER = PydanticOutputParser(pydantic_object=AgentOutput)


def format_instructions() -> str:
    return _PARSER.get_format_instructions()


def parse_agent_output(raw: str) -> AgentOutput:
    """Parse without returning/logging the raw model output on validation errors."""
    return _PARSER.parse(raw)
