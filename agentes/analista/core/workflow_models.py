"""Typed contracts for the in-memory multi-agent workflow foundation."""
from __future__ import annotations

from enum import StrEnum
from typing import Literal, TypedDict
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, UUID4, field_validator, model_validator

from agentes.analista.core.agent_registry import AgentId
from agentes.analista.core.models import AgentTurnResponse, Question
from agentes.conocimiento.repositorio_codigo import es_ruta_codigo


class FlowMode(StrEnum):
    PRE_GROOMING = "pre_grooming"
    POST_GROOMING = "post_grooming"


class WorkflowStage(StrEnum):
    ANALYST = "analista"
    BUSINESS_WAIT = "espera_negocio"
    WRITER = "redactor"
    REVIEW = "revision"
    TECHNICAL_ADVISOR = "asesor_tecnico"
    IMPACT_WAIT = "espera_impacto"  # ya no se usa: las decisiones del Asesor van en la ronda de Negocio
    PO_APPROVAL = "aprobacion_po"
    REPOSITORY = "repositorio"
    CHANGE_MANAGER = "gestor_cambios"
    HUMAN_DECISION = "decision_humana"
    APPLY_DECISION = "aplicar_decision"


class WorkflowStatus(StrEnum):
    READY = "ready"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class POApprovalDecision(StrEnum):
    APPROVE = "aprobar"
    RETURN_TO_ANALYST = "devolver_analista"
    RETURN_TO_WRITER = "devolver_redactor"
    RETURN_TO_ADVISOR = "devolver_asesor"
    REJECT = "rechazar"
    STOP = "detener"


class ChangeDecision(StrEnum):
    APPLY = "aplicar"
    REJECT = "rechazar"
    RETURN = "devolver"


class LessonDecisionKind(StrEnum):
    APPROVE = "aprobar"
    REJECT = "rechazar"


class POApprovalSubmission(BaseModel):
    """An explicit Product Owner decision; agent output cannot satisfy this contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: POApprovalDecision
    reason: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def returns_require_a_reason(self) -> "POApprovalSubmission":
        if self.decision in {
            POApprovalDecision.RETURN_TO_ANALYST,
            POApprovalDecision.RETURN_TO_WRITER,
            POApprovalDecision.RETURN_TO_ADVISOR,
        } and not self.reason:
            raise ValueError("La devolución requiere un motivo del Product Owner.")
        return self


class PersistenceResult(BaseModel):
    """Safe, structured result of saving an explicitly approved story."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["saved", "failed"]
    story_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    approved_at: str | None = Field(default=None, max_length=40)
    error_code: Literal["REPOSITORY_UNAVAILABLE", "REPOSITORY_RESPONSE_INVALID"] | None = None


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    NEEDS_ATTENTION = "needs_attention"


class ChangeKind(StrEnum):
    CLARIFICATION = "aclaracion"
    SCOPE_CHANGE = "cambio_alcance"


class AcceptanceCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    dado: str = Field(min_length=1, max_length=1000)
    cuando: str = Field(min_length=1, max_length=1000)
    entonces: str = Field(min_length=1, max_length=1000)


class DraftStory(BaseModel):
    """Agent-authored HU; deliberately has no approval/decision field."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    como: str = Field(min_length=1, max_length=500)
    quiero: str = Field(min_length=1, max_length=1000)
    para: str = Field(min_length=1, max_length=1000)
    criterios: list[AcceptanceCriterion] = Field(min_length=1, max_length=30)
    review_status: ReviewStatus = ReviewStatus.DRAFT
    review_round: int = Field(default=0, ge=0, le=2)
    observations: list[str] = Field(default_factory=list, max_length=20)


class StoryDraftContent(BaseModel):
    """Only the writer-authored story content; review state stays backend-owned."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    como: str = Field(min_length=1, max_length=500)
    quiero: str = Field(min_length=1, max_length=1000)
    para: str = Field(min_length=1, max_length=1000)
    criterios: list[AcceptanceCriterion] = Field(min_length=1, max_length=30)


class NotaHu(BaseModel):
    """Algo que debe quedar registrado en la HU para quien la implementa o la refina.

    No es control de calidad de la redacción: es una acción fuera del sistema (``dependencia``) o algo que
    el análisis técnico debe confirmar antes de estimar (``pendiente_tecnico``).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tipo: Literal["dependencia", "pendiente_tecnico"]
    texto: str = Field(min_length=1, max_length=500)


class DevolucionPO(BaseModel):
    """Devolución del Product Owner: el motivo y, cuando el Redactor la revisa, cómo se atendió."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    fecha: str = Field(min_length=10, max_length=40)
    destino: Literal["analista", "redactor", "asesor"]
    motivo: str = Field(min_length=1, max_length=1000)
    atencion: str | None = Field(default=None, min_length=1, max_length=1000)


class StoryReviewOutput(BaseModel):
    """Structured quality feedback; it deliberately has no approval field.

    ``observations`` es el control de calidad de esta pasada (se muestra al revisar, no se guarda en la HU).
    ``notas_hu`` y ``atencion_devolucion`` sí pasan a la bitácora de la HU aprobada.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    requires_correction: bool
    observations: list[str] = Field(default_factory=list, max_length=20)
    notas_hu: list[NotaHu] = Field(default_factory=list, max_length=10)
    atencion_devolucion: str | None = Field(default=None, min_length=1, max_length=1000)

    @field_validator("observations")
    @classmethod
    def validate_observations(cls, items: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 1000 for item in items):
            raise ValueError("Cada observación debe tener entre 1 y 1.000 caracteres.")
        return [item.strip() for item in items]

    @model_validator(mode="after")
    def require_feedback_for_correction(self) -> "StoryReviewOutput":
        if self.requires_correction and not self.observations:
            raise ValueError("Una corrección requiere al menos una observación concreta.")
        return self


class BusinessAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question_id: str = Field(min_length=1, max_length=80)
    answer: str = Field(min_length=1, max_length=1000)


class BusinessAnswerSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[BusinessAnswer] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_submission(self) -> "BusinessAnswerSubmission":
        ids = [item.question_id for item in self.answers]
        if len(ids) != len(set(ids)):
            raise ValueError("No se puede responder dos veces la misma pregunta.")
        # Una sola ronda reúne las preguntas del Analista y las decisiones del Asesor.
        if sum(len(item.answer) + len(item.question_id) + 4 for item in self.answers) > 6000:
            raise ValueError("Las respuestas exceden el límite total permitido.")
        return self


class ImpactDecisionAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question_id: str = Field(min_length=1, max_length=80)
    pregunta: str = Field(min_length=1, max_length=500)
    respuesta: str = Field(min_length=1, max_length=1000)


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1, max_length=120)
    source_ref: str = Field(min_length=1, max_length=300)
    evidence: str = Field(min_length=1, max_length=1000)


class SourceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1, max_length=160)
    source_ref: str = Field(min_length=1, max_length=300)
    backend: Literal["pinecone", "local"] | None = None

    @field_validator("source_ref")
    @classmethod
    def only_allow_relative_source_paths(cls, value: str) -> str:
        if value.startswith(("/", "\\")) or "\\" in value or ".." in value.split("/") or ":" in value:
            raise ValueError("La fuente debe ser una ruta relativa allowlisted.")
        return value

    @model_validator(mode="after")
    def validate_allowlisted_source(self) -> "SourceCitation":
        is_demo_file = es_ruta_codigo(self.source_ref) and self.source_id == self.source_ref
        standard_prefix = "agentes/analista/fuentes/estandares.json#"
        is_standards_file = (
            self.source_ref.startswith(standard_prefix)
            and self.source_id == self.source_ref[len(standard_prefix):]
            and bool(self.source_id)
        )
        is_legacy_standards_file = (
            self.source_ref == "agentes/analista/fuentes/estandares.json"
            and self.source_id.startswith("estandares:")
        )
        if not (is_demo_file or is_standards_file or is_legacy_standards_file):
            raise ValueError("La cita no pertenece a las fuentes técnicas allowlisted.")
        return self


class ImpactoNegocio(BaseModel):
    """Qué otra parte del sistema cambia, en lenguaje de negocio: sin archivos, líneas ni código."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    area: str = Field(min_length=1, max_length=120)
    hoy: str = Field(min_length=1, max_length=500)
    debe: str = Field(min_length=1, max_length=500)


class TechnicalAssessment(BaseModel):
    """Technical observations constrained to sources consulted for this turn.

    ``impacto_negocio`` y ``decision_pendiente`` son lo único que ve la persona usuaria. La evidencia técnica
    (módulos, dependencias, riesgos, procesos y fuentes) se guarda para Desarrollo y no se muestra.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    impacto_negocio: list[ImpactoNegocio] = Field(default_factory=list, max_length=15)
    decision_pendiente: list[str] = Field(default_factory=list, max_length=10)

    affected_modules: list[EvidenceReference] = Field(default_factory=list, max_length=30)
    dependencies: list[EvidenceReference] = Field(default_factory=list, max_length=30)
    risks: list[EvidenceReference] = Field(default_factory=list, max_length=30)
    critical_processes: list[EvidenceReference] = Field(default_factory=list, max_length=30)
    consulted_sources: list[SourceCitation] = Field(default_factory=list, max_length=30)
    uncertainties: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("decision_pendiente")
    @classmethod
    def validate_decisions(cls, items: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 500 for item in items):
            raise ValueError("Cada decisión pendiente debe tener entre 1 y 500 caracteres.")
        return [item.strip() for item in items]

    @model_validator(mode="after")
    def findings_must_cite_consulted_sources(self) -> "TechnicalAssessment":
        catalog = {item.source_id: item.source_ref for item in self.consulted_sources}
        findings = [
            *self.affected_modules, *self.dependencies, *self.risks, *self.critical_processes
        ]
        if any(catalog.get(item.source_id) != item.source_ref for item in findings):
            raise ValueError("Cada conclusión técnica debe citar una fuente consultada.")
        if not catalog and not self.uncertainties:
            raise ValueError("Sin fuentes consultadas se debe indicar explícitamente la incertidumbre.")
        return self


class ChangeRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    recommendation: ChangeKind
    comparison: list["ChangeDifference"] = Field(min_length=1, max_length=20)
    impact: list[str] = Field(min_length=1, max_length=20)
    rationale: str = Field(min_length=1, max_length=2000)
    uncertainties: list[str] = Field(default_factory=list, max_length=20)
    lessons_proposed: list["ProposedLesson"] = Field(default_factory=list, max_length=20)

    @field_validator("impact", "uncertainties")
    @classmethod
    def validate_nonempty_items(cls, items: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 1000 for item in items):
            raise ValueError("Cada elemento debe tener entre 1 y 1.000 caracteres.")
        return [item.strip() for item in items]


class ChangeDifference(BaseModel):
    """Traceable excerpts supporting a comparison with the approved version."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    approved_excerpt: str = Field(min_length=1, max_length=1000)
    request_excerpt: str = Field(min_length=1, max_length=1000)
    explanation: str = Field(min_length=1, max_length=1000)


class ProposedLesson(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: Literal[
        "Reglas de negocio", "Datos requeridos", "Validaciones", "Excepciones", "Comportamiento esperado",
    ]
    suggested_question: str = Field(min_length=1, max_length=2000)
    terms: list[str] = Field(default_factory=list, max_length=30)


class LessonDecisionSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0, le=19)
    decision: LessonDecisionKind


class ChangeDecisionSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: ChangeDecision
    reason: str | None = Field(default=None, min_length=1, max_length=1000)
    lesson_decisions: list[LessonDecisionSubmission] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_human_decision(self) -> "ChangeDecisionSubmission":
        if self.decision == ChangeDecision.RETURN and not self.reason:
            raise ValueError("Devolver requiere un motivo.")
        if self.decision != ChangeDecision.APPLY and self.lesson_decisions:
            raise ValueError("Las lecciones solo se pueden decidir al aplicar el cambio.")
        indexes = [item.index for item in self.lesson_decisions]
        if len(indexes) != len(set(indexes)):
            raise ValueError("No se puede decidir dos veces la misma lección.")
        return self


class ChangePersistenceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["recorded", "rejected", "returned", "failed"]
    change_id: str | None = Field(default=None, max_length=100)
    lesson_ids: list[str] = Field(default_factory=list, max_length=20)
    error_code: Literal["REPOSITORY_UNAVAILABLE", "REPOSITORY_RESPONSE_INVALID"] | None = None


class WorkflowCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: UUID4 = Field(default_factory=uuid4)
    mode: FlowMode
    requirement: str | None = Field(default=None, min_length=1, max_length=4000)
    approved_story_id: str | None = Field(default=None, min_length=1, max_length=100)
    change_request: str | None = Field(default=None, min_length=1, max_length=2000)
    # Solo para guardar y retomar el flujo: no llegan al grafo ni a los agentes.
    titulo: str | None = Field(default=None, max_length=200)
    creado_por: str | None = Field(default=None, max_length=120)
    # Lo pone el backend con el usuario de la sesión (para no aprobar la historia propia).
    creado_por_usuario: str | None = Field(default=None, max_length=60)
    formulario: dict[str, str] | None = Field(default=None, max_length=20)

    @field_validator("formulario")
    @classmethod
    def validate_form(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return None
        if any(len(key) > 60 or len(item) > 4000 for key, item in value.items()):
            raise ValueError("El formulario guardado excede los límites permitidos.")
        return value

    @model_validator(mode="after")
    def validate_mode_contract(self) -> "WorkflowCreateRequest":
        if self.mode == FlowMode.PRE_GROOMING:
            if not self.requirement or not self.requirement.strip():
                raise ValueError("pre_grooming requiere requirement no vacío.")
            if self.approved_story_id is not None or self.change_request is not None:
                raise ValueError("pre_grooming no admite datos de solicitud post-grooming.")
        else:
            if not self.approved_story_id or not self.change_request or not self.change_request.strip():
                raise ValueError("post_grooming requiere una HU aprobada y una solicitud de cambio.")
            if self.requirement is not None:
                raise ValueError("post_grooming no admite requirement.")
        return self

    def to_graph_state(self, workflow_id: UUID | None = None) -> "WorkflowState":
        """Create the small, serializable state passed to LangGraph."""
        state = WorkflowStateContract(
            workflow_id=workflow_id or uuid4(),
            request_id=self.request_id,
            mode=self.mode,
            requirement_input=self.requirement,
            approved_story_id=self.approved_story_id,
            change_request=self.change_request,
        )
        return state.model_dump(mode="json")  # type: ignore[return-value]


class WorkflowStateContract(BaseModel):
    """Pydantic serialization boundary for the LangGraph state."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    workflow_id: UUID
    request_id: UUID4
    mode: FlowMode
    requirement_input: str | None = Field(default=None, min_length=1, max_length=4000)
    approved_story_id: str | None = Field(default=None, min_length=1, max_length=100)
    change_request: str | None = Field(default=None, min_length=1, max_length=2000)
    current_stage: WorkflowStage | None = None
    active_agent: AgentId | None = None
    status: WorkflowStatus = WorkflowStatus.READY

    @model_validator(mode="after")
    def validate_mode_contract(self) -> "WorkflowStateContract":
        if self.mode == FlowMode.PRE_GROOMING:
            if not self.requirement_input or self.approved_story_id is not None or self.change_request is not None:
                raise ValueError("El estado pre_grooming contiene un contrato de entrada inválido.")
        elif not self.approved_story_id or not self.change_request or self.requirement_input is not None:
            raise ValueError("El estado post_grooming contiene un contrato de entrada inválido.")
        return self


class WorkflowState(TypedDict, total=False):
    """LangGraph state; thread_id stays in LangGraph config, never in state."""

    workflow_id: str
    request_id: str
    mode: FlowMode
    requirement_input: str | None
    approved_story_id: str | None
    change_request: str | None
    current_stage: WorkflowStage
    active_agent: AgentId
    status: WorkflowStatus
    execute_agents: bool
    analyst_response: dict
    analyst_ready: bool
    pending_questions: list[dict]
    latest_business_answers: list[dict]
    business_clarifications: list[dict]
    draft_story: dict
    technical_assessment: dict
    impact_decisions: list[dict]
    asesor_ejecutado: bool
    decisiones_pendientes: list[dict]
    review_observations: list[str]
    ultima_revision: list[str]
    notas_hu: list[dict]
    devoluciones_po: list[dict]
    po_feedback: str
    po_decision: dict
    po_route: str
    persistence_result: dict
    change_recommendation: dict
    change_decision: dict
    change_persistence_result: dict
    change_route: str
    approved_story_context: dict
    completion_reason: str | None


class WorkflowSnapshot(BaseModel):
    """Publicly safe workflow state, without thread IDs or internal prompts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_id: UUID
    mode: FlowMode
    status: WorkflowStatus
    current_stage: WorkflowStage
    active_agent: AgentId
    pending_questions: list[Question] = Field(default_factory=list)
    analyst_response: AgentTurnResponse | None = None
    draft_story: DraftStory | None = None
    technical_assessment: TechnicalAssessment | None = None
    impact_decisions: list[ImpactDecisionAnswer] = Field(default_factory=list)
    review_observations: list[str] = Field(default_factory=list)
    ultima_revision: list[str] = Field(default_factory=list)
    notas_hu: list[NotaHu] = Field(default_factory=list)
    devoluciones_po: list[DevolucionPO] = Field(default_factory=list)
    po_decision: POApprovalSubmission | None = None
    persistence_result: PersistenceResult | None = None
    change_recommendation: ChangeRecommendation | None = None
    change_decision: ChangeDecisionSubmission | None = None
    change_persistence_result: ChangePersistenceResult | None = None
    completion_reason: str | None = None

