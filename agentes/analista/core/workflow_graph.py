"""LangGraph workflow with Analyst business interrupts and a bounded writer loop."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command, interrupt

from agentes.analista.core.agent_registry import AgentId
from agentes.analista.core.flujo import FIN, Paso, Ruta, construir_flujo
from agentes.equipo.gestor_cambios.gestor_cambios_service import GestorCambiosService
from agentes.analista.core.conversation_store import ConversationStore, StoreError
from agentes.analista.core.models import AgentTurnResponse, SendMessageRequest, QuestionState
from agentes.analista.core.observability import Observability
from agentes.analista.core.prompt_loader import load_prompt
from agentes.equipo.redactor_revisor.redactor_revisor_service import RedactorRevisorService
from agentes.equipo.asesor_tecnico.asesor_tecnico_service import AsesorTecnicoService
from agentes.analista.core.workflow_models import (
    BusinessAnswerSubmission,
    ChangeDecision,
    ChangeDecisionSubmission,
    ChangePersistenceResult,
    ChangeRecommendation,
    DevolucionPO,
    DraftStory,
    FlowMode,
    NotaHu,
    PersistenceResult,
    POApprovalDecision,
    POApprovalSubmission,
    StoryDraftContent,
    StoryReviewOutput,
    TechnicalAssessment,
    WorkflowCreateRequest,
    WorkflowSnapshot,
    WorkflowStage,
    WorkflowState,
    WorkflowStatus,
    ReviewStatus,
)

logger = logging.getLogger(__name__)

AnalystNode = Callable[[WorkflowState], Awaitable[AgentTurnResponse | Mapping[str, Any]]]
DraftNode = Callable[[WorkflowState], Awaitable[StoryDraftContent | Mapping[str, Any]]]
ReviewNode = Callable[[WorkflowState], Awaitable[StoryReviewOutput | Mapping[str, Any]]]
TechnicalAdvisorNode = Callable[[WorkflowState], Awaitable[TechnicalAssessment | Mapping[str, Any]]]
ChangeManagerNode = Callable[[WorkflowState, Any], Awaitable[ChangeRecommendation | Mapping[str, Any]]]


class WorkflowNotFoundError(LookupError):
    """The workflow has no checkpoint in this process."""


def _siguiente_del_analista(state: Mapping[str, Any]) -> str:
    pendiente = bool(state.get("pending_questions"))
    listo = bool(state.get("analyst_ready"))
    if (pendiente or listo) and not state.get("asesor_ejecutado"):
        return "asesor"
    if pendiente or state.get("decisiones_pendientes"):
        return "negocio"
    return "redactor" if listo else "vacios"


def _siguiente_del_asesor(state: Mapping[str, Any]) -> str:
    if state.get("pending_questions") or state.get("decisiones_pendientes"):
        return "negocio"
    return "redactor" if state.get("analyst_ready") else "vacios"


def _hoy() -> str:
    return datetime.now(UTC).date().isoformat()


def _sin_que_inicial(texto: str) -> str:
    return re.sub(r"^\s*que\s+", "", texto, flags=re.IGNORECASE).strip() or texto


def _devolucion_en_curso(state: Mapping[str, Any]) -> str | None:
    """El motivo de la última devolución del PO, para que el Redactor diga cómo la atendió."""
    devoluciones = state.get("devoluciones_po") or []
    return devoluciones[-1].get("motivo") if devoluciones else None


def _seguimiento_hu(state: Mapping[str, Any], decision: POApprovalSubmission) -> dict[str, Any]:
    """Lo que queda en la HU aprobada además de la historia: lo útil para el grooming y la implementación.

    Las observaciones de control de calidad del Redactor no se guardan: sirvieron para revisar la historia.
    El impacto en otros módulos tampoco: queda cubierto por los criterios de aceptación de la historia.
    """
    analisis = state.get("analyst_response") or {}
    return {
        "beneficios": list(analisis.get("beneficios") or []),
        "decisiones_impacto": [
            {"pregunta": item["pregunta"], "respuesta": item["respuesta"]} for item in state.get("impact_decisions", [])
        ],
        "supuestos_po": list(analisis.get("supuesto_validar_po") or []),
        "notas": list(state.get("notas_hu") or []),
        "devoluciones_po": list(state.get("devoluciones_po") or []),
        "nota_aprobacion": decision.reason,
        "aprobada_el": _hoy(),
    }


class WorkflowNotInterruptedError(RuntimeError):
    """A resume was attempted while the workflow had no human interrupt."""


class WorkflowDependencyError(RuntimeError):
    """A required repository or agent dependency failed during workflow execution."""


def _public_snapshot(state: Mapping[str, Any]) -> WorkflowSnapshot:
    allowed = {
        "workflow_id", "mode", "status", "current_stage", "active_agent",
        "pending_questions", "analyst_response", "draft_story", "review_observations",
        "ultima_revision", "notas_hu", "devoluciones_po",
        "technical_assessment", "impact_decisions", "completion_reason",
        "po_decision", "persistence_result",
        "change_recommendation", "change_decision", "change_persistence_result",
    }
    return WorkflowSnapshot.model_validate({key: value for key, value in state.items() if key in allowed})


def _trace_stage(
    observability: Observability | None,
    state: WorkflowState,
    *,
    stage: WorkflowStage,
    agent: AgentId,
) -> None:
    if observability is None:
        return
    trace = observability.start_turn(
        conversation_id=state.get("workflow_id", "unknown"),
        request_id=state.get("request_id", "unknown"),
        turn_id=state.get("workflow_id", "unknown"),
    )
    operation = trace.operation(
        kind="chain", name="workflow-stage", metadata={"stage": stage.value, "agent_id": agent.value}
    )
    operation.finish(status="ready", metadata={"stage": stage.value, "agent_id": agent.value})
    trace.finish(status="ready", metadata={"stage": stage.value, "agent_id": agent.value})


def _analysis_state_from_approved_hu(state: WorkflowState) -> dict[str, Any]:
    """Build a new analysis request from the approved version and the authorized change request."""
    context = state.get("approved_story_context")
    if not isinstance(context, Mapping):
        raise ValueError("No hay contexto de HU aprobada para el nuevo análisis.")
    payload = {
        "approved_story_id": state.get("approved_story_id"),
        "approved_story": {
            "title": context.get("titulo"),
            "requirement": context.get("requerimiento"),
            "story": context.get("historia"),
            "acceptance_criteria": context.get("criterios"),
            "clarifications": context.get("aclaraciones"),
        },
        "change_request": state.get("change_request"),
        "human_return_reason": (state.get("change_decision") or {}).get("reason"),
        "instruction": (
            "Analiza la solicitud frente a la versión aprobada. Conserva los hechos provistos, "
            "separa lo conocido de lo faltante y pregunta lo necesario. La versión aprobada no "
            "se reemplaza hasta una nueva aprobación humana explícita."
        ),
    }
    return {"requirement_input": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}


def build_workflow_graph(
    *,
    checkpointer: InMemorySaver | None = None,
    observability: Observability | None = None,
    analyst: AnalystNode | None = None,
    draft: DraftNode | None = None,
    review: ReviewNode | None = None,
    advisor: TechnicalAdvisorNode | None = None,
    change_manager: ChangeManagerNode | None = None,
    repository: Any | None = None,
    knowledge_retriever: Any | None = None,
):
    """Compile pre/post-grooming orchestration with injectable agents and repository."""
    writer = RedactorRevisorService()
    technical_advisor = AsesorTecnicoService()
    manager = GestorCambiosService()
    repository_instance = repository

    if knowledge_retriever is not None:
        # Solo pruebas/diagnóstico: el conocimiento siempre llega por los servidores MCP de cada agente;
        # este recuperador se instala detrás de ellos (transporte MCP en memoria).
        from agentes.conocimiento.retrieval import establecer_recuperador

        establecer_recuperador(knowledge_retriever)

    async def call_analyst(state: WorkflowState) -> AgentTurnResponse | Mapping[str, Any]:
        if analyst is None:
            raise RuntimeError("El nodo Analista requiere el adaptador de run_turn.")
        return await analyst(state)

    def analysis_with_impact(state: WorkflowState) -> dict[str, Any]:
        """Lo que el Redactor recibe: el análisis, el impacto en otros módulos y las decisiones tomadas."""
        assessment = state.get("technical_assessment") or {}
        return {
            **dict(state["analyst_response"]),
            "impacto_en_otros_modulos": assessment.get("impacto_negocio", []),
            "decisiones_de_impacto": [
                {"pregunta": item["pregunta"], "respuesta": item["respuesta"]}
                for item in state.get("impact_decisions", [])
            ],
        }

    async def call_draft(state: WorkflowState) -> StoryDraftContent | Mapping[str, Any]:
        if draft is not None:
            return await draft(state)
        # El Redactor-Revisor decide qué consultar en su servidor MCP (RAG detrás).
        return await writer.draft(
            requirement=state["requirement_input"] or "",
            analyst_response=analysis_with_impact(state),
            previous_story=state.get("draft_story"),
            observations=state.get("review_observations", []),
        )

    async def call_review(state: WorkflowState) -> StoryReviewOutput | Mapping[str, Any]:
        if review is not None:
            return await review(state)
        return await writer.review(
            requirement=state["requirement_input"] or "",
            analyst_response=analysis_with_impact(state),
            story=state["draft_story"],
            devolucion_po=_devolucion_en_curso(state),
        )

    async def call_advisor(state: WorkflowState) -> TechnicalAssessment | Mapping[str, Any]:
        if advisor is not None:
            return await advisor(state)
        analysis = (state.get("analyst_response") or {}).get("analisis", {})
        return await technical_advisor.assess(
            requirement=state.get("requirement_input") or "",
            story={
                "analisis_validado": analysis,
                # Lo que el Analista no le pregunta a Negocio porque solo se sabe revisando el sistema.
                "temas_para_verificar": (state.get("analyst_response") or {}).get("para_asesor", []),
                "aclaraciones_de_negocio": [
                    {"pregunta": item.get("question", ""), "respuesta": item.get("answer", "")}
                    for item in state.get("business_clarifications", [])
                ],
                **({"historia_en_borrador": state["draft_story"]} if state.get("draft_story") else {}),
                **({"product_owner_feedback": state["po_feedback"]} if state.get("po_feedback") else {}),
            },
        )

    def get_repository() -> Any:
        nonlocal repository_instance
        if repository_instance is None:
            from agentes.analista.memory.repositorio import RepositorioHU

            repository_instance = RepositorioHU()
        return repository_instance

    def prepare_pre_grooming(state: WorkflowState) -> dict[str, Any]:
        if FlowMode(state["mode"]) != FlowMode.PRE_GROOMING:
            raise ValueError("El modo no corresponde al nodo pre_grooming.")
        stage, agent = WorkflowStage.ANALYST, AgentId.ANALYST
        _trace_stage(observability, state, stage=stage, agent=agent)
        return {"current_stage": stage, "active_agent": agent, "status": WorkflowStatus.READY}

    def prepare_post_grooming(state: WorkflowState) -> dict[str, Any]:
        if FlowMode(state["mode"]) != FlowMode.POST_GROOMING:
            raise ValueError("El modo no corresponde al nodo post_grooming.")
        stage, agent = WorkflowStage.CHANGE_MANAGER, AgentId.CHANGE_MANAGER
        _trace_stage(observability, state, stage=stage, agent=agent)
        return {"current_stage": stage, "active_agent": agent, "status": WorkflowStatus.READY}

    async def change_manager_node(state: WorkflowState) -> dict[str, Any]:
        approved_story_id = state.get("approved_story_id")
        change_request = state.get("change_request")
        if not approved_story_id or not change_request:
            raise ValueError("El Gestor de Cambios requiere la referencia aprobada y la solicitud.")
        repository_ref = get_repository()
        try:
            approved_story = repository_ref.obtener_hu(approved_story_id)
        except Exception as exc:
            from agentes.analista.memory.repositorio import RepositorioError

            if isinstance(exc, RepositorioError) and exc.not_found:
                raise ValueError("La HU aprobada no existe en el Repositorio.") from exc
            raise WorkflowDependencyError("No se pudo consultar la HU aprobada.") from exc
        if not isinstance(approved_story, Mapping) or approved_story.get("id") != approved_story_id:
            raise WorkflowDependencyError("El Repositorio no devolvió la HU aprobada solicitada.")
        if change_manager is None:
            # El Gestor consulta HU aprobadas, lecciones y checklist por MCP, y puede pedir criterio al Asesor.
            recommendation = await manager.evaluate(
                approved_story_id=approved_story_id,
                change_request=change_request,
                repository=repository_ref,
                approved_story=approved_story,
            )
        else:
            recommendation = await change_manager(state, repository_ref)
        recommendation = ChangeRecommendation.model_validate(recommendation)
        context = {
            key: approved_story[key] for key in (
                "id", "titulo", "tipo_informacion", "requerimiento", "historia", "criterios", "aclaraciones",
                "aprobada_en",
            ) if key in approved_story
        }
        _trace_stage(observability, state, stage=WorkflowStage.CHANGE_MANAGER, agent=AgentId.CHANGE_MANAGER)
        return {
            "approved_story_context": context,
            "change_recommendation": recommendation.model_dump(mode="json"),
            "current_stage": WorkflowStage.HUMAN_DECISION,
            "active_agent": AgentId.CHANGE_MANAGER,
            "status": WorkflowStatus.INTERRUPTED,
        }

    def human_change_decision_node(state: WorkflowState) -> dict[str, Any]:
        recommendation = ChangeRecommendation.model_validate(state.get("change_recommendation"))
        raw_decision = interrupt({
            "kind": "change_decision",
            "recommendation": recommendation.model_dump(mode="json"),
            "decisions": [item.value for item in ChangeDecision],
            "lesson_decisions": ["aprobar", "rechazar"],
        })
        decision = ChangeDecisionSubmission.model_validate(raw_decision)
        if any(item.index >= len(recommendation.lessons_proposed) for item in decision.lesson_decisions):
            raise ValueError("La decisión incluye una lección que no fue propuesta.")
        route = "apply" if decision.decision == ChangeDecision.APPLY else (
            "analyze" if decision.decision == ChangeDecision.RETURN else "end"
        )
        updates: dict[str, Any] = {
            "change_decision": decision.model_dump(mode="json"),
            "change_route": route,
            "current_stage": WorkflowStage.HUMAN_DECISION,
            "active_agent": AgentId.CHANGE_MANAGER,
            "status": WorkflowStatus.RUNNING if route != "end" else WorkflowStatus.CANCELLED,
            "completion_reason": decision.reason if route == "end" else None,
        }
        if route == "end":
            updates["change_persistence_result"] = ChangePersistenceResult(
                status="rejected",
            ).model_dump(mode="json")
        elif route == "analyze":
            updates.update(_analysis_state_from_approved_hu(state))
        _trace_stage(observability, state, stage=WorkflowStage.HUMAN_DECISION, agent=AgentId.CHANGE_MANAGER)
        return updates

    def apply_change_decision_node(state: WorkflowState) -> dict[str, Any]:
        recommendation = ChangeRecommendation.model_validate(state.get("change_recommendation"))
        decision = ChangeDecisionSubmission.model_validate(state.get("change_decision"))
        if decision.decision != ChangeDecision.APPLY:
            raise ValueError("El nodo de aplicación requiere autorización humana explícita.")
        if any(item.index >= len(recommendation.lessons_proposed) for item in decision.lesson_decisions):
            raise ValueError("La decisión incluye una lección que no fue propuesta.")
        lessons = [
            {
                "categoria": item.category,
                "pregunta_sugerida": item.suggested_question,
                "terminos": item.terms,
            }
            for item in recommendation.lessons_proposed
        ]
        repository_ref = get_repository()
        try:
            result = repository_ref.registrar_cambio(
                hu_id=state["approved_story_id"],
                solicitud=state["change_request"],
                clasificacion=recommendation.recommendation.value,
                causa_raiz=lessons[0]["categoria"] if lessons else "",
                lecciones_propuestas=lessons,
                cambio_id=state["workflow_id"],
                incluir_ids_lecciones=True,
            )
            lesson_ids = result.get("leccion_ids") or ([result["leccion_id"]] if result.get("leccion_id") else [])
            if len(lesson_ids) != len(lessons):
                raise ValueError("El Repositorio devolvió IDs de lección incompatibles.")
            for lesson_decision in decision.lesson_decisions:
                repository_ref.decidir_leccion(
                    lesson_ids[lesson_decision.index], lesson_decision.decision.value,
                )
        except Exception:
            persisted = ChangePersistenceResult(
                status="failed", error_code="REPOSITORY_UNAVAILABLE",
            )
            logger.warning("workflow_change_apply_failed", extra={
                "event": "workflow_change_apply_failed", "error_code": "REPOSITORY_UNAVAILABLE",
            })
            return {
                "change_persistence_result": persisted.model_dump(mode="json"),
                "current_stage": WorkflowStage.APPLY_DECISION,
                "active_agent": AgentId.CHANGE_MANAGER,
                "status": WorkflowStatus.FAILED,
                "completion_reason": "No fue posible registrar la decisión autorizada.",
                "change_route": "end",
            }

        try:
            persisted = ChangePersistenceResult(
                status="recorded", change_id=result["solicitud_id"], lesson_ids=lesson_ids,
            )
        except Exception:
            persisted = ChangePersistenceResult(
                status="failed", error_code="REPOSITORY_RESPONSE_INVALID",
            )
            return {
                "change_persistence_result": persisted.model_dump(mode="json"),
                "current_stage": WorkflowStage.APPLY_DECISION,
                "active_agent": AgentId.CHANGE_MANAGER,
                "status": WorkflowStatus.FAILED,
                "completion_reason": "El Repositorio devolvió un resultado inválido.",
                "change_route": "end",
            }

        updates: dict[str, Any] = {
            "change_persistence_result": persisted.model_dump(mode="json"),
            "current_stage": WorkflowStage.APPLY_DECISION,
            "active_agent": AgentId.CHANGE_MANAGER,
            "status": WorkflowStatus.COMPLETED,
            "completion_reason": "La solicitud autorizada quedó registrada.",
            "change_route": "end",
        }
        if recommendation.recommendation.value == "cambio_alcance":
            updates.update(_analysis_state_from_approved_hu(state))
            updates.update({
                "current_stage": WorkflowStage.ANALYST,
                "active_agent": AgentId.ANALYST,
                "status": WorkflowStatus.RUNNING,
                "completion_reason": None,
                "change_route": "analyze",
            })
        _trace_stage(observability, state, stage=WorkflowStage.APPLY_DECISION, agent=AgentId.CHANGE_MANAGER)
        return updates

    async def analyst_node(state: WorkflowState) -> dict[str, Any]:
        response = AgentTurnResponse.model_validate(await call_analyst(state))
        pending = [question.model_dump(mode="json") for question in response.preguntas
                   if question.estado == QuestionState.PENDING]
        ready = response.listo_para_redactor and not pending
        decision_abierta = bool(state.get("decisiones_pendientes"))
        if (pending or ready) and not state.get("asesor_ejecutado"):
            # Trabajo en equipo: el Asesor revisa el sistema después del primer análisis, antes de ir a Negocio.
            stage, agent, status = WorkflowStage.TECHNICAL_ADVISOR, AgentId.TECHNICAL_ADVISOR, WorkflowStatus.RUNNING
        elif pending or decision_abierta:
            stage, agent, status = WorkflowStage.BUSINESS_WAIT, AgentId.ANALYST, WorkflowStatus.INTERRUPTED
        elif ready:
            stage, agent, status = WorkflowStage.WRITER, AgentId.WRITER_REVIEWER, WorkflowStatus.RUNNING
        else:
            # Fail closed: without an open question there is no valid Business interrupt to resume.
            stage, agent, status = WorkflowStage.ANALYST, AgentId.ANALYST, WorkflowStatus.FAILED
        _trace_stage(observability, state, stage=WorkflowStage.ANALYST, agent=AgentId.ANALYST)
        return {
            "analyst_response": response.model_dump(mode="json"),
            "analyst_ready": ready,
            "pending_questions": pending,
            "current_stage": stage,
            "active_agent": agent,
            "status": status,
            "completion_reason": None if ready or pending else "El Analista reportó vacíos sin preguntas pendientes.",
        }

    def wait_for_business(state: WorkflowState) -> dict[str, Any]:
        """Una sola ronda para Negocio: las preguntas del Analista y las decisiones del Asesor, juntas."""
        lista_analista = [{**item, "origen": "analista"} for item in state.get("pending_questions", [])]
        lista_decision = list(state.get("decisiones_pendientes", []))
        payload = {
            "kind": "business_answers",
            "questions": [*lista_analista, *lista_decision],
            "impacto_negocio": (state.get("technical_assessment") or {}).get("impacto_negocio", []),
            "max_answer_chars": 1000,
            "max_total_chars": 6000,
        }
        raw_answers = interrupt(payload)
        answers = BusinessAnswerSubmission.model_validate(raw_answers)
        id_analista = {item["question_id"] for item in lista_analista}
        decision_por_id = {item["question_id"]: item["pregunta"] for item in lista_decision}
        supplied_ids = {item.question_id for item in answers.answers}
        if not supplied_ids or not supplied_ids <= id_analista | set(decision_por_id):
            raise ValueError("La respuesta incluye preguntas que no están pendientes en este workflow.")
        _trace_stage(observability, state, stage=WorkflowStage.BUSINESS_WAIT, agent=AgentId.ANALYST)

        respuesta_decision = [item for item in answers.answers if item.question_id in decision_por_id]
        decision_tomada = [
            *state.get("impact_decisions", []),
            *({"question_id": item.question_id, "pregunta": decision_por_id[item.question_id], "respuesta": item.answer}
              for item in respuesta_decision),
        ]
        decision_restante = [item for item in lista_decision if item["question_id"] not in supplied_ids]
        updates: dict[str, Any] = {
            "impact_decisions": decision_tomada,
            "decisiones_pendientes": decision_restante,
            "status": WorkflowStatus.RUNNING,
        }
        respuesta_analista = [item for item in answers.answers if item.question_id in id_analista]
        if respuesta_analista:
            questions_by_id = {item["question_id"]: item.get("pregunta", "") for item in lista_analista}
            enriched_answers = [
                {**item.model_dump(mode="json"), "question": questions_by_id.get(item.question_id, item.question_id)}
                for item in respuesta_analista
            ]
            clarification_by_id = {
                item["question_id"]: item for item in state.get("business_clarifications", [])
            }
            clarification_by_id.update({item["question_id"]: item for item in enriched_answers})
            updates.update({
                "latest_business_answers": enriched_answers,
                "business_clarifications": list(clarification_by_id.values()),
                "current_stage": WorkflowStage.ANALYST,
                "active_agent": AgentId.ANALYST,
            })
        else:
            # Solo se respondieron decisiones del Asesor: el Analista no tiene nada nuevo que analizar.
            updates.update({"current_stage": WorkflowStage.WRITER, "active_agent": AgentId.WRITER_REVIEWER})
        return updates

    async def writer_node(state: WorkflowState) -> dict[str, Any]:
        content = StoryDraftContent.model_validate(await call_draft(state))
        # La plantilla ya muestra «Como»: se quita si el modelo lo repitió al inicio del rol.
        rol = re.sub(r"^\s*como\s+", "", content.como, flags=re.IGNORECASE).strip() or content.como
        # Igual con «Dado que»: el criterio no debe empezar con «que» (se leería «Dado que que…»).
        criterios = [
            criterio.model_copy(update={"dado": _sin_que_inicial(criterio.dado)}) for criterio in content.criterios
        ]
        content = content.model_copy(update={"como": rol, "criterios": criterios})
        previous = DraftStory.model_validate(state["draft_story"]) if state.get("draft_story") else None
        round_number = min(previous.review_round + 1, 2) if previous else 0
        story = DraftStory(
            **content.model_dump(),
            review_status=ReviewStatus.DRAFT,
            review_round=round_number,
            observations=state.get("review_observations", []),
        )
        _trace_stage(observability, state, stage=WorkflowStage.WRITER, agent=AgentId.WRITER_REVIEWER)
        return {
            "draft_story": story.model_dump(mode="json"),
            "current_stage": WorkflowStage.REVIEW,
            "active_agent": AgentId.WRITER_REVIEWER,
            "status": WorkflowStatus.RUNNING,
        }

    async def reviewer_node(state: WorkflowState) -> dict[str, Any]:
        result = StoryReviewOutput.model_validate(await call_review(state))
        story = DraftStory.model_validate(state["draft_story"])
        observations = (story.observations + result.observations)[-20:]
        at_limit = story.review_round >= 2
        needs_attention = result.requires_correction and at_limit
        status = (
            ReviewStatus.NEEDS_ATTENTION if needs_attention else
            ReviewStatus.DRAFT if result.requires_correction else ReviewStatus.REVIEWED
        )
        revised_story = story.model_copy(update={"review_status": status, "observations": observations})
        should_correct = result.requires_correction and not at_limit
        # Cada revisión reemplaza las notas para la HU: la última versión de la historia es la que vale.
        notas: list[dict[str, Any]] = []
        for nota in result.notas_hu:
            if all(nota.texto.casefold() != previa["texto"].casefold() for previa in notas):
                notas.append(nota.model_dump(mode="json"))
        devoluciones = [dict(item) for item in state.get("devoluciones_po", [])]
        if result.atencion_devolucion and devoluciones:
            devoluciones[-1]["atencion"] = result.atencion_devolucion
        stage = WorkflowStage.WRITER if should_correct else WorkflowStage.PO_APPROVAL
        workflow_status = WorkflowStatus.RUNNING if should_correct else WorkflowStatus.INTERRUPTED
        _trace_stage(observability, state, stage=WorkflowStage.REVIEW, agent=AgentId.WRITER_REVIEWER)
        return {
            "draft_story": revised_story.model_dump(mode="json"),
            "review_observations": observations,
            "ultima_revision": list(result.observations),
            "notas_hu": notas,
            "devoluciones_po": devoluciones,
            "review_requires_correction": should_correct,
            "completion_reason": "La revisión agotó dos rondas; requiere revisión del PO." if needs_attention else None,
            "current_stage": stage,
            "active_agent": AgentId.WRITER_REVIEWER,
            "status": workflow_status,
        }

    async def technical_advisor_node(state: WorkflowState) -> dict[str, Any]:
        """El Asesor revisa el sistema; sus decisiones se suman a las preguntas de Negocio en la misma ronda."""
        assessment = TechnicalAssessment.model_validate(await call_advisor(state))
        _trace_stage(observability, state, stage=WorkflowStage.TECHNICAL_ADVISOR,
                     agent=AgentId.TECHNICAL_ADVISOR)
        decision = [
            {"question_id": f"decision-{index + 1}", "categoria": "Decisión de impacto", "pregunta": texto,
             "origen": "asesor_tecnico"}
            for index, texto in enumerate(assessment.decision_pendiente)
        ]
        hay_pregunta = bool(state.get("pending_questions")) or bool(decision)
        if hay_pregunta:
            stage, agent, status = WorkflowStage.BUSINESS_WAIT, AgentId.ANALYST, WorkflowStatus.INTERRUPTED
        elif state.get("analyst_ready"):
            stage, agent, status = WorkflowStage.WRITER, AgentId.WRITER_REVIEWER, WorkflowStatus.RUNNING
        else:
            stage, agent, status = WorkflowStage.ANALYST, AgentId.ANALYST, WorkflowStatus.FAILED
        return {
            "technical_assessment": assessment.model_dump(mode="json"),
            "asesor_ejecutado": True,
            "impact_decisions": [],
            "decisiones_pendientes": decision,
            "current_stage": stage,
            "active_agent": agent,
            "status": status,
        }

    def po_approval_node(state: WorkflowState) -> dict[str, Any]:
        """Wait for an explicit, validated human decision before taking any write path."""
        raw_decision = interrupt({
            "kind": "product_owner_approval",
            "story": state.get("draft_story"),
            "review_observations": state.get("review_observations", []),
            "ultima_revision": state.get("ultima_revision", []),
            "notas_hu": state.get("notas_hu", []),
            "devoluciones_po": state.get("devoluciones_po", []),
            "impacto_negocio": (state.get("technical_assessment") or {}).get("impacto_negocio", []),
            "decisiones_impacto": state.get("impact_decisions", []),
            "supuesto_validar_po": (state.get("analyst_response") or {}).get("supuesto_validar_po", []),
            "decisions": [item.value for item in POApprovalDecision],
            "return_requires_reason": True,
        })
        decision = POApprovalSubmission.model_validate(raw_decision)
        route_by_decision = {
            POApprovalDecision.APPROVE: "repository",
            POApprovalDecision.RETURN_TO_ANALYST: "analyst",
            POApprovalDecision.RETURN_TO_WRITER: "writer",
            POApprovalDecision.RETURN_TO_ADVISOR: "technical_advisor",
            POApprovalDecision.REJECT: "end",
            POApprovalDecision.STOP: "end",
        }
        route = route_by_decision[decision.decision]
        _trace_stage(observability, state, stage=WorkflowStage.PO_APPROVAL,
                     agent=AgentId.TECHNICAL_ADVISOR)
        updates: dict[str, Any] = {
            "po_decision": decision.model_dump(mode="json"),
            "po_route": route,
            "status": WorkflowStatus.RUNNING,
            "completion_reason": None,
        }
        if decision.decision in {POApprovalDecision.REJECT, POApprovalDecision.STOP}:
            updates.update({
                "current_stage": WorkflowStage.PO_APPROVAL,
                "status": WorkflowStatus.CANCELLED,
                "completion_reason": decision.reason or (
                    "El Product Owner rechazó la historia." if decision.decision == POApprovalDecision.REJECT
                    else "El Product Owner detuvo el flujo."
                ),
            })
        elif decision.decision == POApprovalDecision.APPROVE:
            updates["current_stage"] = WorkflowStage.REPOSITORY
        else:
            reason = decision.reason or ""
            updates["po_feedback"] = reason
            destino = {
                POApprovalDecision.RETURN_TO_ANALYST: "analista",
                POApprovalDecision.RETURN_TO_WRITER: "redactor",
                POApprovalDecision.RETURN_TO_ADVISOR: "asesor",
            }[decision.decision]
            devolucion = DevolucionPO(fecha=_hoy(), destino=destino, motivo=reason)
            updates["devoluciones_po"] = [*state.get("devoluciones_po", []), devolucion.model_dump(mode="json")][-10:]
            if decision.decision == POApprovalDecision.RETURN_TO_ANALYST:
                updates.update({"current_stage": WorkflowStage.ANALYST, "active_agent": AgentId.ANALYST})
            elif decision.decision == POApprovalDecision.RETURN_TO_WRITER:
                observations = [*state.get("review_observations", []), f"Observación del Product Owner: {reason}"][-20:]
                updates.update({
                    "current_stage": WorkflowStage.WRITER,
                    "active_agent": AgentId.WRITER_REVIEWER,
                    "review_observations": observations,
                })
            else:
                updates.update({"current_stage": WorkflowStage.TECHNICAL_ADVISOR,
                                "active_agent": AgentId.TECHNICAL_ADVISOR})
        return updates

    def repository_node(state: WorkflowState) -> dict[str, Any]:
        """Persist only after a validated human approval; use workflow UUID as idempotency key."""
        decision = POApprovalSubmission.model_validate(state.get("po_decision"))
        if decision.decision != POApprovalDecision.APPROVE:
            raise ValueError("El repositorio requiere una aprobación explícita del Product Owner.")
        story = DraftStory.model_validate(state.get("draft_story"))
        story_id = str(state.get("approved_story_id") or state["workflow_id"])
        title = story.quiero[:200]
        hu = {
            "id": story_id,
            "titulo": title,
            "tipo_informacion": "Historia de Usuario",
            "requerimiento": state.get("requirement_input") or "",
            "historia": {"asA": story.como, "iWant": story.quiero, "soThat": story.para},
            "criterios": [item.model_dump(mode="json") for item in story.criterios],
            "aclaraciones": [
                {"pregunta": item.get("question", item["question_id"]), "respuesta": item["answer"]}
                for item in state.get("business_clarifications", state.get("latest_business_answers", []))
            ],
            "seguimiento": _seguimiento_hu(state, decision),
        }
        nonlocal repository_instance
        change_persistence_result = state.get("change_persistence_result")
        try:
            if repository_instance is None:
                from agentes.analista.memory.repositorio import RepositorioHU

                repository_instance = RepositorioHU()
            if (
                FlowMode(state["mode"]) == FlowMode.POST_GROOMING
                and not state.get("change_persistence_result")
            ):
                recommendation = ChangeRecommendation.model_validate(state.get("change_recommendation"))
                lessons = [
                    {"categoria": item.category, "pregunta_sugerida": item.suggested_question, "terminos": item.terms}
                    for item in recommendation.lessons_proposed
                ]
                change_record = repository_instance.registrar_cambio(
                    hu_id=state["approved_story_id"],
                    solicitud=state["change_request"],
                    clasificacion=recommendation.recommendation.value,
                    causa_raiz=lessons[0]["categoria"] if lessons else "",
                    lecciones_propuestas=lessons,
                    cambio_id=state["workflow_id"],
                    incluir_ids_lecciones=True,
                )
                lesson_ids = change_record.get("leccion_ids") or []
                if len(lesson_ids) != len(lessons):
                    raise ValueError("El Repositorio devolvió IDs de lección incompatibles.")
                change_persistence_result = ChangePersistenceResult(
                    status="recorded", change_id=change_record["solicitud_id"], lesson_ids=lesson_ids,
                ).model_dump(mode="json")
            raw_result = repository_instance.guardar_hu(hu)
        except Exception:
            result = PersistenceResult(
                status="failed", story_id=story_id, title=title, error_code="REPOSITORY_UNAVAILABLE",
            )
            logger.warning("workflow_repository_save_failed", extra={"event": "workflow_repository_save_failed",
                                                                     "error_code": "REPOSITORY_UNAVAILABLE"})
            status = WorkflowStatus.FAILED
            completion_reason = "La aprobación humana se registró, pero no fue posible guardar la HU."
            if (
                FlowMode(state["mode"]) == FlowMode.POST_GROOMING
                and not change_persistence_result
            ):
                change_persistence_result = ChangePersistenceResult(
                    status="failed", error_code="REPOSITORY_UNAVAILABLE",
                ).model_dump(mode="json")
        else:
            try:
                result = PersistenceResult(
                    status="saved",
                    story_id=raw_result["id"],
                    title=raw_result["titulo"],
                    approved_at=raw_result["aprobada_en"],
                )
            except Exception:
                result = PersistenceResult(
                    status="failed", story_id=story_id, title=title,
                    error_code="REPOSITORY_RESPONSE_INVALID",
                )
                logger.warning("workflow_repository_response_invalid", extra={
                    "event": "workflow_repository_response_invalid",
                    "error_code": "REPOSITORY_RESPONSE_INVALID",
                })
                status = WorkflowStatus.FAILED
                completion_reason = "La aprobación humana se registró, pero el Repositorio devolvió un resultado inválido."
            else:
                status = WorkflowStatus.COMPLETED
                completion_reason = "HU aprobada por el Product Owner y guardada en el Repositorio."
        _trace_stage(observability, state, stage=WorkflowStage.REPOSITORY,
                     agent=AgentId.TECHNICAL_ADVISOR)
        return {
            "persistence_result": result.model_dump(mode="json"),
            **({"change_persistence_result": change_persistence_result} if change_persistence_result else {}),
            "current_stage": WorkflowStage.REPOSITORY,
            "active_agent": AgentId.TECHNICAL_ADVISOR,
            "status": status,
            "completion_reason": completion_reason,
        }

    def hold_for_unresolved_gaps(state: WorkflowState) -> dict[str, Any]:
        _trace_stage(observability, state, stage=WorkflowStage.ANALYST, agent=AgentId.ANALYST)
        return {"current_stage": WorkflowStage.ANALYST, "status": WorkflowStatus.FAILED}

    # El flujo como tabla: cada paso, su nodo y a dónde sigue. Para agregar un agente se agrega su Paso
    # y se cambia el «siguiente» del paso anterior (ver docs/arquitectura.md, skill «agregar-agente»).
    inicio = Ruta(lambda state: FlowMode(state["mode"]).value, {
        FlowMode.PRE_GROOMING.value: "prepare_pre_grooming",
        FlowMode.POST_GROOMING.value: "prepare_post_grooming",
    })
    lista_paso = [
        # Creación de una HU (pre-grooming)
        Paso("prepare_pre_grooming", prepare_pre_grooming,
             Ruta(lambda state: "analista" if state.get("execute_agents") else "fin",
                  {"analista": "analyst", "fin": FIN}),
             "Valida la solicitud de creación."),
        Paso("analyst", analyst_node, Ruta(_siguiente_del_analista, {
            "asesor": "technical_advisor", "negocio": "business_wait", "redactor": "writer",
            "vacios": "hold_for_unresolved_gaps",
        }), "Agente Analista: aclara los vacíos del requerimiento; lo que es del sistema lo pasa al Asesor."),
        Paso("technical_advisor", technical_advisor_node, Ruta(_siguiente_del_asesor, {
            "negocio": "business_wait", "redactor": "writer", "vacios": "hold_for_unresolved_gaps",
        }), "Asesor Técnico: revisa el sistema y agrega sus decisiones a las preguntas para Negocio."),
        Paso("business_wait", wait_for_business, Ruta(
            lambda state: "analista" if state.get("current_stage") == WorkflowStage.ANALYST else "redactor",
            {"analista": "analyst", "redactor": "writer"},
        ), "Pausa: Negocio responde en una sola ronda las preguntas del Analista y las decisiones del Asesor."),
        Paso("writer", writer_node, "reviewer",
             "Redactor-Revisor: redacta o corrige la historia."),
        Paso("reviewer", reviewer_node,
             Ruta(lambda state: "corregir" if state.get("review_requires_correction") else "aprobar",
                  {"corregir": "writer", "aprobar": "aprobacion_po"}),
             "Redactor-Revisor: revisa la historia (hasta dos rondas)."),
        Paso("aprobacion_po", po_approval_node,
             Ruta(lambda state: state["po_route"], {
                 "analyst": "analyst", "writer": "writer", "technical_advisor": "technical_advisor",
                 "repository": "repositorio", "end": FIN,
             }),
             "Pausa: el Product Owner aprueba, devuelve o rechaza."),
        Paso("repositorio", repository_node, FIN, "Guarda la HU aprobada en el Repositorio de HU."),
        Paso("hold_for_unresolved_gaps", hold_for_unresolved_gaps, FIN,
             "Se detiene si quedan vacíos sin preguntas posibles."),
        # Solicitud de cambio sobre una HU aprobada (post-grooming)
        Paso("prepare_post_grooming", prepare_post_grooming,
             Ruta(lambda state: "gestor" if state.get("execute_agents") else "fin",
                  {"gestor": "change_manager", "fin": FIN}),
             "Valida la solicitud de cambio."),
        Paso("change_manager", change_manager_node, "human_change_decision",
             "Gestor de Cambios: compara con la HU aprobada y recomienda."),
        Paso("human_change_decision", human_change_decision_node,
             Ruta(lambda state: state["change_route"],
                  {"apply": "apply_change_decision", "analyze": "analyst", "end": FIN}),
             "Pausa: el Product Owner decide sobre el cambio."),
        Paso("apply_change_decision", apply_change_decision_node,
             Ruta(lambda state: state["change_route"], {"analyze": "analyst", "end": FIN}),
             "Aplica la decisión y, si corresponde, vuelve a analizar."),
    ]
    return construir_flujo(WorkflowState, inicio, lista_paso, checkpointer=checkpointer or InMemorySaver())


_ESTADO_GUARDADO = {
    WorkflowStatus.INTERRUPTED: "esperando",
    WorkflowStatus.COMPLETED: "completado",
    WorkflowStatus.CANCELLED: "cancelado",
    WorkflowStatus.FAILED: "fallido",
    WorkflowStatus.RUNNING: "en_ejecucion",
    WorkflowStatus.READY: "en_ejecucion",
}


class WorkflowRuntime:
    """Own graph checkpoints, Analyst conversations, and private thread IDs.

    Con ``persistencia`` (el Repositorio en la aplicación real) cada flujo se guarda en la base de datos al
    detenerse para esperar a una persona o al fallar, y se recupera si el proceso se reinició. Sin ella
    (pruebas), los flujos viven solo en memoria.
    """

    def __init__(
        self,
        observability: Observability | None = None,
        *,
        analyst: AnalystNode | None = None,
        draft: DraftNode | None = None,
        review: ReviewNode | None = None,
        advisor: TechnicalAdvisorNode | None = None,
        change_manager: ChangeManagerNode | None = None,
        repository: Any | None = None,
        knowledge_retriever: Any | None = None,
        persistencia: Any | None = None,
    ) -> None:
        self.observability = observability or Observability()
        self._checkpointer = InMemorySaver(
            serde=JsonPlusSerializer(allowed_msgpack_modules=[
                ("agentes.analista.core.workflow_models", "WorkflowStage"),
                ("agentes.analista.core.workflow_models", "WorkflowStatus"),
                ("agentes.analista.core.agent_registry", "AgentId"),
            ])
        )
        self._threads: dict[UUID, str] = {}
        self._conversation_ids: dict[UUID, UUID] = {}
        self._meta: dict[UUID, dict[str, Any]] = {}
        self._persistencia = persistencia
        self._injected_analyst = analyst
        prompt = load_prompt()
        self._analyst_store = ConversationStore(
            prompt_version=prompt.version,
            prompt_hash=prompt.sha256,
            ttl_seconds=1800,
            max_conversations=32,
        )
        self._graph = build_workflow_graph(
            checkpointer=self._checkpointer,
            observability=self.observability,
            analyst=self._run_analyst if analyst is None else analyst,
            draft=draft,
            review=review,
            advisor=advisor,
            change_manager=change_manager,
            repository=repository,
            knowledge_retriever=knowledge_retriever,
        )

    @property
    def active_thread_count(self) -> int:
        return len(self._threads)

    @property
    def persiste(self) -> bool:
        return self._persistencia is not None

    def _thread_config(self, workflow_id: UUID) -> dict[str, Any]:
        return {"configurable": {"thread_id": self._threads[workflow_id]}}

    def _register(self, request: WorkflowCreateRequest | None = None) -> UUID:
        workflow_id = uuid4()
        thread_id = uuid4().hex
        self._threads[workflow_id] = thread_id
        titulo = (request.titulo if request else None) or (
            (request.requirement or request.change_request or "") if request else ""
        )
        self._meta[workflow_id] = {
            "titulo": " ".join(titulo.split())[:200] or "Sin título",
            "creado_por": request.creado_por if request else None,
            "creado_por_usuario": request.creado_por_usuario if request else None,
            "formulario": dict(request.formulario or {}) if request else {},
            "borrador": {},
            "estado": "en_ejecucion",
            "creado_en": None,
            "actualizado_en": None,
        }
        return workflow_id

    def _forget(self, workflow_id: UUID) -> None:
        thread_id = self._threads.pop(workflow_id, None)
        self._meta.pop(workflow_id, None)
        if thread_id is not None:
            self._checkpointer.delete_thread(thread_id)

    # --- Guardar y recuperar ------------------------------------------------
    def _persistir(self, workflow_id: UUID, *, error: bool = False) -> None:
        """Guarda el último punto de control y el estado del flujo. Un fallo aquí no detiene el flujo."""
        if self._persistencia is None or workflow_id not in self._threads:
            return
        from agentes.analista.core.workflow_persistencia import exportar_hilo

        try:
            thread_id = self._threads[workflow_id]
            punto = exportar_hilo(self._checkpointer, thread_id)
            if punto is None:
                return
            snapshot = self._graph.get_state(self._thread_config(workflow_id))
            values = snapshot.values
            pendiente = self._pending_interrupt_from(snapshot)
            if pendiente is not None:
                # Sigue esperando a una persona (por ejemplo, la respuesta enviada no era válida).
                estado = "esperando"
            elif error:
                estado = "error"
            else:
                estado = _ESTADO_GUARDADO.get(WorkflowStatus(values.get("status", "running")), "en_ejecucion")
            meta = self._meta.setdefault(workflow_id, {})
            meta["estado"] = estado
            self._persistencia.guardar_workflow({
                "id": str(workflow_id), "hilo": thread_id, "modo": str(values.get("mode", "pre_grooming")),
                "titulo": meta.get("titulo"), "creado_por": meta.get("creado_por"),
                "creado_por_usuario": meta.get("creado_por_usuario"),
                "estado": estado, "etapa": str(values.get("current_stage", "analista")),
                "espera": pendiente["payload"].get("kind") if pendiente else None,
                "formulario": meta.get("formulario") or {}, "punto_control": punto,
            })
        except Exception as exc:
            logger.warning("No se pudo guardar el flujo %s: %s", workflow_id, type(exc).__name__)

    def _recuperar(self, workflow_id: UUID) -> bool:
        """Carga en memoria un flujo guardado (por ejemplo, después de que el servicio se reinició)."""
        if self._persistencia is None:
            return False
        from agentes.analista.core.workflow_persistencia import importar_hilo

        try:
            registro = self._persistencia.obtener_workflow(str(workflow_id))
        except Exception as exc:
            logger.warning("No se pudo leer el flujo guardado %s: %s", workflow_id, type(exc).__name__)
            raise WorkflowDependencyError("No fue posible leer el flujo guardado.") from exc
        if not registro or not registro.get("punto_control"):
            return False
        importar_hilo(self._checkpointer, registro["hilo"], registro["punto_control"])
        self._threads[workflow_id] = registro["hilo"]
        self._meta[workflow_id] = {
            "titulo": registro.get("titulo"), "creado_por": registro.get("creado_por"),
            "creado_por_usuario": registro.get("creado_por_usuario"),
            "formulario": registro.get("formulario") or {}, "borrador": registro.get("borrador") or {},
            "estado": registro.get("estado"), "creado_en": registro.get("creado_en"),
            "actualizado_en": registro.get("actualizado_en"),
        }
        return True

    def metadatos(self, workflow_id: UUID | str) -> dict[str, Any]:
        """Datos para retomar el flujo: título, quién lo inició, formulario, respuestas sin enviar y estado."""
        identifier = self._resolve_workflow_id(workflow_id)
        meta = dict(self._meta.get(identifier, {}))
        meta["reintentable"] = meta.get("estado") == "error" and self._puede_reintentar(identifier)
        return meta

    def listar(self) -> list[dict[str, Any]]:
        if self._persistencia is None:
            return []
        return self._persistencia.listar_workflow()

    def guardar_borrador(self, workflow_id: UUID | str, respuestas: Mapping[str, str]) -> None:
        identifier = self._resolve_workflow_id(workflow_id)
        borrador = {str(key): str(value) for key, value in respuestas.items()}
        self._meta.setdefault(identifier, {})["borrador"] = borrador
        if self._persistencia is not None:
            self._persistencia.guardar_borrador_workflow(str(identifier), borrador)

    def descartar(self, workflow_id: UUID | str) -> None:
        identifier = self._resolve_workflow_id(workflow_id)
        self._forget(identifier)
        if self._persistencia is not None:
            self._persistencia.eliminar_workflow(str(identifier))

    def _puede_reintentar(self, workflow_id: UUID) -> bool:
        snapshot = self._graph.get_state(self._thread_config(workflow_id))
        return bool(snapshot.next) and self._pending_interrupt_from(snapshot) is None

    async def reintentar(self, workflow_id: UUID | str) -> WorkflowSnapshot:
        """Vuelve a ejecutar el paso que falló, desde el último punto guardado."""
        identifier = self._resolve_workflow_id(workflow_id)
        if not self._puede_reintentar(identifier):
            raise WorkflowNotInterruptedError("El flujo no tiene un paso pendiente para reintentar.")
        return await self._ejecutar(identifier, None)

    async def _ejecutar(self, workflow_id: UUID, entrada: Any) -> WorkflowSnapshot:
        """Ejecuta el grafo y guarda el resultado; si falla, lo guarda como error para poder reintentar."""
        try:
            result = await self._graph.ainvoke(entrada, config=self._thread_config(workflow_id))
        except Exception:
            await asyncio.to_thread(self._persistir, workflow_id, error=True)
            raise
        await asyncio.to_thread(self._persistir, workflow_id)
        return _public_snapshot(result)

    # --- Ciclo de vida --------------------------------------------------------
    def start(self, request: WorkflowCreateRequest) -> WorkflowSnapshot:
        """Validate and checkpoint the selected initial role without executing agents."""
        request = WorkflowCreateRequest.model_validate(request)
        workflow_id = self._register(request)
        try:
            state = request.to_graph_state(workflow_id)
            state["execute_agents"] = False
            result = self._graph.invoke(state, config=self._thread_config(workflow_id))
            return _public_snapshot(result)
        except Exception:
            self._forget(workflow_id)
            raise

    async def execute(self, request: WorkflowCreateRequest) -> WorkflowSnapshot:
        """Run pre-grooming through Analyst, Business interrupt, and writer/reviewer nodes."""
        request = WorkflowCreateRequest.model_validate(request)
        workflow_id = self._register(request)
        try:
            if self._injected_analyst is None and request.mode == FlowMode.PRE_GROOMING:
                conversation = await self._analyst_store.create()
                self._conversation_ids[workflow_id] = conversation.conversation_id
            state = request.to_graph_state(workflow_id)
            state["execute_agents"] = True
            return await self._ejecutar(workflow_id, state)
        except Exception:
            if self._persistencia is not None and self._graph.get_state(self._thread_config(workflow_id)).values:
                # Queda guardado como error: se puede reintentar desde la lista de HU en proceso.
                raise
            if self._injected_analyst is None:
                conversation_id_forget = self._conversation_ids.pop(workflow_id, None)
                if conversation_id_forget is not None:
                    await self._analyst_store.delete(conversation_id_forget)
            self._forget(workflow_id)
            raise

    async def _analyst_conversation(self, workflow_id: UUID, state: WorkflowState) -> UUID:
        """La conversación del Analista para este flujo; si expiró o el proceso se reinició, se restaura."""
        conversation_id = self._conversation_ids.get(workflow_id)
        if conversation_id is not None:
            try:
                await self._analyst_store.get(conversation_id)
                return conversation_id
            except StoreError:
                logger.info("La conversación del Analista expiró; se restaura desde el flujo guardado.")
        conversation = await self._analyst_store.create()
        conversation_id = conversation.conversation_id
        self._conversation_ids[workflow_id] = conversation_id
        previous = state.get("analyst_response")
        if previous:
            await self._analyst_store.restaurar(
                conversation_id, state.get("requirement_input") or "", AgentTurnResponse.model_validate(previous),
            )
        return conversation_id

    async def _run_analyst(self, state: WorkflowState) -> AgentTurnResponse:
        from agentes.equipo.analista.analista_service import run_turn

        workflow_id = UUID(state["workflow_id"])
        conversation_id = await self._analyst_conversation(workflow_id, state)
        answers = state.get("latest_business_answers", [])
        if answers:
            # Se envía la pregunta junto con su respuesta: el modelo no debe adivinar a qué id corresponde.
            message = "Respuestas de Negocio a las preguntas pendientes (ya quedan respondidas):\n" + "\n".join(
                f"- Pregunta (id: {item['question_id']}): {item.get('question', item['question_id'])}\n"
                f"  Respuesta: {item['answer']}"
                for item in answers
            ) + (
                "\nActualiza el análisis con estas respuestas. No vuelvas a preguntar lo que ya está respondido. "
                "Si un punto de faltante, supuesta o ambigua quedó resuelto por una respuesta, muévelo a conocida "
                "o enlázalo en `vinculos` con el id de esa pregunta."
            )
        else:
            message = state["requirement_input"] or ""
        if state.get("po_feedback"):
            message += "\nInstrucción de devolución del Product Owner:\n" + state["po_feedback"]
        request = SendMessageRequest(request_id=uuid4(), message=message[:4000])
        return await run_turn(
            self._analyst_store, conversation_id, request, observability=self.observability,
            respondidas={str(item["question_id"]) for item in answers},
        )

    async def resume(
        self,
        workflow_id: UUID | str,
        answers: BusinessAnswerSubmission | POApprovalSubmission | Mapping[str, Any],
    ) -> WorkflowSnapshot:
        """Resume a human interrupt on its existing thread checkpoint."""
        identifier = self._resolve_workflow_id(workflow_id)
        current = self._graph.get_state(self._thread_config(identifier))
        if not any(getattr(task, "interrupts", ()) for task in current.tasks):
            raise WorkflowNotInterruptedError("El workflow no está esperando una decisión humana.")
        current_stage = current.values.get("current_stage")
        if current_stage == WorkflowStage.PO_APPROVAL:
            submission = POApprovalSubmission.model_validate(answers)
        elif current_stage == WorkflowStage.HUMAN_DECISION:
            submission = ChangeDecisionSubmission.model_validate(answers)
        else:
            submission = BusinessAnswerSubmission.model_validate(answers)
            # Se valida antes de reanudar: una respuesta rechazada no debe quedar registrada en el punto de control.
            pendiente = {
                str(item.get("question_id"))
                for task in current.tasks for pausa in getattr(task, "interrupts", ())
                for item in (getattr(pausa, "value", None) or {}).get("questions", [])
            }
            if not {item.question_id for item in submission.answers} <= pendiente:
                raise ValueError("La respuesta incluye preguntas que no están pendientes en este workflow.")
        # Lo que estaba escrito sin enviar ya se envió.
        self._meta.setdefault(identifier, {})["borrador"] = {}
        if self._persistencia is not None:
            try:
                await asyncio.to_thread(self._persistencia.guardar_borrador_workflow, str(identifier), {})
            except Exception as exc:
                logger.warning("No se pudo limpiar el borrador del flujo: %s", type(exc).__name__)
        return await self._ejecutar(identifier, Command(resume=submission.model_dump(mode="json")))

    def _resolve_workflow_id(self, workflow_id: UUID | str) -> UUID:
        try:
            identifier = workflow_id if isinstance(workflow_id, UUID) else UUID(str(workflow_id))
        except ValueError as exc:
            raise WorkflowNotFoundError("El workflow no existe.") from exc
        if identifier in self._threads or self._recuperar(identifier):
            return identifier
        raise WorkflowNotFoundError("El workflow no existe o no se guardó.")

    def get(self, workflow_id: UUID | str) -> WorkflowSnapshot:
        """Read the latest safe checkpoint, from memory or from the saved workflow."""
        identifier = self._resolve_workflow_id(workflow_id)
        snapshot = self._graph.get_state(self._thread_config(identifier))
        if not snapshot.values:
            raise WorkflowNotFoundError("El workflow no existe en este proceso.")
        return _public_snapshot(snapshot.values)

    @staticmethod
    def _pending_interrupt_from(snapshot: Any) -> dict[str, Any] | None:
        for task in snapshot.tasks:
            for item in getattr(task, "interrupts", ()):
                value = getattr(item, "value", None)
                interrupt_id = getattr(item, "id", None)
                if isinstance(value, Mapping) and isinstance(value.get("kind"), str) and interrupt_id:
                    return {"interrupt_id": str(interrupt_id), "payload": dict(value)}
        return None

    def pending_interrupt(self, workflow_id: UUID | str) -> dict[str, Any] | None:
        """Return the active LangGraph interrupt identifier and its bounded public payload."""
        identifier = self._resolve_workflow_id(workflow_id)
        snapshot = self._graph.get_state(self._thread_config(identifier))
        if not snapshot.values:
            raise WorkflowNotFoundError("El workflow no existe en este proceso.")
        return self._pending_interrupt_from(snapshot)
