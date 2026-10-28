"""Public REST contracts and private conversation records for the Analyst."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, UUID4, field_validator, model_validator

from agentes.analista.core.opencode_compat import is_supported_opencode_version


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class HealthStatus(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class CheckStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class ConversationStatus(StrEnum):
    ACTIVE = "activa"
    PROCESSING = "procesando"
    REPLACED = "reemplazada"
    DELETED = "eliminada"
    EXPIRED = "expirada"


class TurnStatus(StrEnum):
    SENT = "enviado"
    PROCESSING = "procesando"
    COMPLETED = "completado"
    FAILED = "fallido"
    CANCELLED = "cancelado"
    EXPIRED = "expirado"
    DISCARDED = "descartado"


class QuestionCategory(StrEnum):
    BUSINESS_RULES = "Reglas de negocio"
    REQUIRED_DATA = "Datos requeridos"
    VALIDATIONS = "Validaciones"
    EXCEPTIONS = "Excepciones"
    EXPECTED_BEHAVIOR = "Comportamiento esperado"


class QuestionState(StrEnum):
    PENDING = "pendiente"
    ANSWERED = "respondida"


class ToolName(StrEnum):
    GLOSSARY = "consultar_glosario"
    SIMILAR_STORIES = "buscar_hu_similares"
    STANDARDS = "consultar_estandares"
    EMPTY_CHECKLIST = "aplicar_checklist_vacios"


class ToolStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class ErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    MESSAGE_EMPTY = "MESSAGE_EMPTY"
    MESSAGE_TOO_LONG = "MESSAGE_TOO_LONG"
    CONVERSATION_NOT_FOUND = "CONVERSATION_NOT_FOUND"
    TURN_IN_PROGRESS = "TURN_IN_PROGRESS"
    TURN_CANCELLED = "TURN_CANCELLED"
    TURN_INVALIDATED = "TURN_INVALIDATED"
    REQUEST_ID_CONFLICT = "REQUEST_ID_CONFLICT"
    AGENT_OUTPUT_INVALID = "AGENT_OUTPUT_INVALID"
    OPENCODE_UNAVAILABLE = "OPENCODE_UNAVAILABLE"
    OPENCODE_AUTH_FAILED = "OPENCODE_AUTH_FAILED"
    OPENCODE_RATE_LIMITED = "OPENCODE_RATE_LIMITED"
    OPENCODE_INCOMPATIBLE = "OPENCODE_INCOMPATIBLE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MCP_UNAVAILABLE = "MCP_UNAVAILABLE"
    PROMPT_INVALID = "PROMPT_INVALID"
    PROMPT_RESTART_REQUIRED = "PROMPT_RESTART_REQUIRED"
    TURN_TIMEOUT = "TURN_TIMEOUT"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class EvaluationMetric(StrEnum):
    M1_GAPS = "M1_vacios"
    M2_QUESTIONS = "M2_preguntas_utiles"
    M3_TIME = "M3_tiempo"
    M4_SATISFACTION = "M4_satisfaccion"
    M5_INVENTIONS = "M5_invenciones"


class EvaluationStatus(StrEnum):
    NOT_MEASURED = "NOT_MEASURED"
    MEASURED = "MEASURED"
    PARTIAL = "PARTIAL"


class Analysis(ContractModel):
    conocida: list[str] = Field(max_length=100)
    faltante: list[str] = Field(max_length=100)
    supuesta: list[str] = Field(max_length=100)
    ambigua: list[str] = Field(max_length=100)

    @field_validator("conocida", "faltante", "supuesta", "ambigua")
    @classmethod
    def validate_items(cls, items: list[str]) -> list[str]:
        for item in items:
            if not item.strip():
                raise ValueError("Los elementos del análisis no pueden estar vacíos")
            if not 1 <= len(item) <= 1000:
                raise ValueError("Cada elemento del análisis debe tener entre 1 y 1.000 caracteres")
        return items


class Question(ContractModel):
    question_id: str = Field(min_length=1, max_length=80)
    categoria: QuestionCategory
    pregunta: str = Field(min_length=1, max_length=500)
    estado: QuestionState
    created_turn_id: UUID4 | None = None
    updated_turn_id: UUID4 | None = None

    @field_validator("pregunta")
    @classmethod
    def validate_question(cls, value: str) -> str:
        if not value.strip() or len(value) > 500:
            raise ValueError("La pregunta no puede estar vacía")
        return value


class SourceConsultation(ContractModel):
    nombre: ToolName
    resultados: int = Field(ge=0)
    duracion_ms: int = Field(ge=0)


class ToolExecution(ContractModel):
    tool_name: ToolName
    status: ToolStatus
    result_count: int | None = Field(default=None, ge=0)
    duration_ms: int = Field(ge=0)
    error_code: str | None = Field(default=None, min_length=1, max_length=80)
    result_digest: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_execution(self) -> "ToolExecution":
        if self.status == ToolStatus.OK and self.result_count is None:
            raise ValueError("Una ejecución exitosa requiere result_count, incluso si es cero")
        if self.status != ToolStatus.OK and self.result_count is not None:
            raise ValueError("Una ejecución fallida no puede declarar cantidad de resultados")
        if self.status == ToolStatus.OK and self.error_code is not None:
            raise ValueError("Una ejecución exitosa no puede declarar error_code")
        return self


class AgentTurnResponse(ContractModel):
    conversation_id: UUID4
    request_id: UUID4
    turn_id: UUID4
    estado: Literal["completado"]
    respuesta_markdown: str = Field(min_length=1, max_length=50_000)
    analisis: Analysis
    preguntas: list[Question] = Field(max_length=50)
    fuentes_consultadas: list[SourceConsultation] = Field(max_length=4)
    listo_para_redactor: bool
    limitaciones: list[str] = Field(max_length=10)
    duracion_ms: int = Field(ge=0)
    prompt_version: str = Field(min_length=1, max_length=40)

    @field_validator("respuesta_markdown")
    @classmethod
    def validate_markdown(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La respuesta Markdown no puede estar vacía")
        return value

    @field_validator("limitaciones")
    @classmethod
    def validate_limitations(cls, items: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 300 for item in items):
            raise ValueError("Cada limitación debe tener entre 1 y 300 caracteres")
        return items

    @model_validator(mode="after")
    def validate_readiness(self) -> "AgentTurnResponse":
        has_open_questions = any(question.estado == QuestionState.PENDING for question in self.preguntas)
        expected = not (
            self.analisis.faltante
            or self.analisis.supuesta
            or self.analisis.ambigua
            or has_open_questions
        )
        if self.listo_para_redactor != expected:
            raise ValueError("listo_para_redactor no coincide con la compuerta conservadora")
        return self


class SendMessageRequest(ContractModel):
    request_id: UUID4
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El mensaje no puede estar vacío")
        return value


class CancelRequest(ContractModel):
    request_id: UUID4


class CreateConversationResponse(ContractModel):
    conversation_id: UUID4
    created_at: datetime
    expires_at: datetime
    message_limit: int = Field(ge=1)
    timeout_seconds: int = Field(ge=1)


class ResetResponse(CreateConversationResponse):
    replaced_conversation_id: UUID4 | None = None


class CancelResponse(ContractModel):
    canceled: bool
    turn_id: UUID4 | None = None
    reason: Literal["CANCELED", "NO_ACTIVE_TURN", "ALREADY_TERMINAL", "REQUEST_ID_MISMATCH"]


class ValidationIssue(ContractModel):
    field: str = Field(max_length=120)
    message: str = Field(max_length=300)


class ErrorDetail(ContractModel):
    code: ErrorCode
    message: str = Field(min_length=1, max_length=500)
    retryable: bool
    request_id: UUID4 | None = None
    retry_at: datetime | None = None
    field: str | None = Field(default=None, max_length=120)
    issues: list[ValidationIssue] | None = Field(default=None, max_length=20)


class ErrorResponse(ContractModel):
    error: ErrorDetail


class OpenCodeCheck(ContractModel):
    status: CheckStatus
    version: str | None = Field(default=None, max_length=40)
    agent: str | None = Field(default=None, max_length=80)


class McpCheck(ContractModel):
    status: CheckStatus
    tools: list[ToolName] = Field(max_length=4)

    @model_validator(mode="after")
    def validate_tool_set(self) -> "McpCheck":
        expected = {tool.value for tool in ToolName}
        actual = [tool.value for tool in self.tools]
        if len(actual) != len(set(actual)):
            raise ValueError("MCP no puede anunciar herramientas duplicadas")
        if self.status == CheckStatus.OK and set(actual) != expected:
            raise ValueError("MCP ok requiere exactamente las cuatro herramientas permitidas")
        return self


class LangfuseCheck(ContractModel):
    status: CheckStatus


class HealthChecks(ContractModel):
    opencode: OpenCodeCheck
    mcp: McpCheck
    langfuse: LangfuseCheck


class HealthResponse(ContractModel):
    status: HealthStatus
    checked_at: datetime
    backend_version: str = Field(max_length=40)
    timeout_seconds: int = Field(ge=1)
    message_limit: int = Field(ge=1)
    prompt_version: str | None = Field(default=None, max_length=40)
    prompt_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    restart_required: bool
    checks: HealthChecks

    @model_validator(mode="after")
    def validate_ready_state(self) -> "HealthResponse":
        if self.status == HealthStatus.READY and (
            self.checks.opencode.status != CheckStatus.OK
            or not is_supported_opencode_version(self.checks.opencode.version)
            or self.checks.opencode.agent != "analista"
        ):
            raise ValueError("Health ready requiere una versión compatible de OpenCode/API v2 y el agente analista")
        if self.status == HealthStatus.READY and self.checks.mcp.status != CheckStatus.OK:
            raise ValueError("Health ready requiere MCP verificado")
        if self.status == HealthStatus.READY and self.checks.langfuse.status != CheckStatus.OK:
            raise ValueError("Health ready requiere Langfuse verificado")
        if self.status == HealthStatus.READY and self.restart_required:
            raise ValueError("Health ready no puede requerir reinicio")
        return self


class ContextPayload(ContractModel):
    current_state: dict[str, object]
    recent_turns: list[dict[str, str]] = Field(max_length=6)
    previous_summary: str = Field(default="", max_length=2000)
    current_message: str = Field(min_length=1, max_length=4000)
    tool_results: list[dict[str, object]] = Field(max_length=4)
    limitations: list[str] = Field(max_length=10)

    @model_validator(mode="after")
    def validate_total_context(self) -> "ContextPayload":
        if len(self.model_dump_json()) > 24_000:
            raise ValueError("El contexto total no puede exceder 24.000 caracteres")
        if not self.current_message.strip():
            raise ValueError("El mensaje actual no puede estar vacío")
        if any(not item.strip() or len(item) > 300 for item in self.limitations):
            raise ValueError("Cada limitación debe tener entre 1 y 300 caracteres")
        return self


class ConversationRecord(ContractModel):
    conversation_id: UUID4
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    generation: int = Field(ge=0)
    status: ConversationStatus
    active_turn_id: UUID4 | None = None
    context_turns: list["CompletedTurn"] = Field(default_factory=list)
    previous_summary: str = Field(default="", max_length=2000)
    analysis: Analysis | None = None
    questions: list[Question] = Field(default_factory=list, max_length=50)
    request_cache: dict[UUID, "TurnRecord"] = Field(default_factory=dict)
    last_sources: list[SourceConsultation] = Field(default_factory=list, max_length=4)
    prompt_version: str = Field(min_length=1, max_length=40)
    prompt_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    turns_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_conversation(self) -> "ConversationRecord":
        if self.expires_at < self.last_activity_at:
            raise ValueError("expires_at debe ser igual o posterior a last_activity_at")
        if self.status == ConversationStatus.PROCESSING and self.active_turn_id is None:
            raise ValueError("Una conversación procesando requiere un turno activo")
        return self


class TurnRecord(ContractModel):
    turn_id: UUID4
    request_id: UUID4
    conversation_id: UUID4
    message: str = Field(min_length=1, max_length=4000)
    message_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: TurnStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    opencode_session_id: str | None = Field(default=None, repr=False)
    trace_id: str | None = Field(default=None, repr=False)
    tool_results: list[ToolExecution] = Field(default_factory=list, max_length=4)
    analysis: Analysis | None = None
    questions: list[Question] | None = None
    response: AgentTurnResponse | None = None
    error: ErrorDetail | None = None
    finish_reason: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=160)
    repair_attempts: int = Field(default=0, ge=0, le=1)
    cancel_requested_at: datetime | None = None
    invalidated_by_generation: int | None = Field(default=None, ge=0)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El mensaje no puede estar vacío")
        return value


class CompletedTurn(ContractModel):
    turn_id: UUID4
    request_id: UUID4
    message: str = Field(min_length=1, max_length=4000)
    response: AgentTurnResponse
    completed_at: datetime


class EvaluationRecord(ContractModel):
    evaluation_id: str = Field(min_length=1, max_length=120)
    corpus_id: str = Field(min_length=1, max_length=120)
    sample_size: int = Field(ge=0)
    prompt_version: str = Field(min_length=1, max_length=40)
    prompt_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    commit: str = Field(min_length=1, max_length=80)
    metric: EvaluationMetric
    target: str = Field(min_length=1, max_length=120)
    value: float | None = None
    status: EvaluationStatus
    evidence: str = Field(min_length=1, max_length=500)
    measured_at: datetime | None = None
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_measurement_state(self) -> "EvaluationRecord":
        if self.status == EvaluationStatus.NOT_MEASURED and (self.value is not None or self.measured_at is not None):
            raise ValueError("Una evaluación no medida no puede declarar valor ni fecha de medición")
        if self.status == EvaluationStatus.MEASURED and (self.value is None or self.measured_at is None):
            raise ValueError("Una evaluación medida requiere valor y fecha de medición")
        return self


ConversationRecord.model_rebuild()
