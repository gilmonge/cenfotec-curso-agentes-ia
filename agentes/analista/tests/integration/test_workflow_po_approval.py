from uuid import uuid4

import pytest
from pydantic import ValidationError

from agentes.analista.core.models import AgentTurnResponse, Analysis
from agentes.analista.core.workflow_graph import WorkflowNotInterruptedError, WorkflowRuntime
from agentes.analista.core.workflow_models import (
    FlowMode,
    WorkflowCreateRequest,
    WorkflowStage,
    WorkflowStatus,
)


def _analyst_response():
    return AgentTurnResponse(
        conversation_id=uuid4(), request_id=uuid4(), turn_id=uuid4(), estado="completado",
        respuesta_markdown="Análisis validado.",
        analisis=Analysis(conocida=["El sistema consulta saldos."], faltante=[], supuesta=[], ambigua=[]),
        preguntas=[], fuentes_consultadas=[], listo_para_redactor=True,
        limitaciones=[], duracion_ms=1, prompt_version="1.0.0",
    )


async def _draft(_state):
    return {
        "como": "persona usuaria", "quiero": "consultar el saldo",
        "para": "conocer el disponible",
        "criterios": [{"dado": "una cuenta activa", "cuando": "consulto el saldo",
                       "entonces": "veo el disponible"}],
    }


async def _review(_state):
    return {"requires_correction": False, "observations": []}


async def _advisor(_state):
    return {"affected_modules": [], "dependencies": [], "risks": [], "critical_processes": [],
            "consulted_sources": [], "uncertainties": ["Prueba con asesor simulado."]}


class _RepositoryDouble:
    def __init__(self):
        self.rows = {}
        self.calls = []

    def guardar_hu(self, hu):
        self.calls.append(hu)
        # Mirrors RepositorioHU's upsert-by-id contract for retry safety.
        self.rows[hu["id"]] = dict(hu)
        return {"id": hu["id"], "titulo": hu["titulo"], "aprobada_en": "2026-11-21T00:00:00+00:00"}


async def _runtime(repository):
    async def analyst(_state):
        return _analyst_response()

    runtime = WorkflowRuntime(
        analyst=analyst,
        draft=_draft,
        review=_review,
        advisor=_advisor,
        repository=repository,
    )
    # Sin preguntas de Negocio ni decisiones del Asesor, el flujo llega directo a la aprobación del PO.
    paused = await runtime.execute(WorkflowCreateRequest(
        mode=FlowMode.PRE_GROOMING, requirement="Consultar el saldo de cuentas activas",
    ))
    return runtime, paused


@pytest.mark.asyncio
async def test_po_interrupt_waits_for_explicit_human_decision_without_writing():
    repository = _RepositoryDouble()
    runtime, paused = await _runtime(repository)

    assert paused.current_stage == WorkflowStage.PO_APPROVAL
    assert paused.status == WorkflowStatus.INTERRUPTED
    assert repository.calls == []
    assert any(task.interrupts for task in runtime._graph.get_state(
        runtime._thread_config(paused.workflow_id)
    ).tasks)


@pytest.mark.asyncio
async def test_explicit_approval_persists_structured_story_once_and_reuses_thread():
    repository = _RepositoryDouble()
    runtime, paused = await _runtime(repository)
    thread_id = runtime._threads[paused.workflow_id]

    finished = await runtime.resume(paused.workflow_id, {"decision": "aprobar"})

    assert finished.status == WorkflowStatus.COMPLETED
    assert finished.current_stage == WorkflowStage.REPOSITORY
    assert finished.persistence_result.status == "saved"
    assert len(repository.calls) == 1
    saved = repository.calls[0]
    assert saved == {
        "id": str(paused.workflow_id),
        "titulo": "consultar el saldo",
        "tipo_informacion": "Historia de Usuario",
        "requerimiento": "Consultar el saldo de cuentas activas",
        "historia": {"asA": "persona usuaria", "iWant": "consultar el saldo",
                     "soThat": "conocer el disponible"},
        "criterios": [{"dado": "una cuenta activa", "cuando": "consulto el saldo",
                       "entonces": "veo el disponible"}],
        "aclaraciones": [],
        "seguimiento": {
            "beneficios": [], "decisiones_impacto": [], "supuestos_po": [],
            "notas": [], "devoluciones_po": [], "nota_aprobacion": None,
            "aprobada_el": saved["seguimiento"]["aprobada_el"],
        },
    }
    assert runtime._threads[paused.workflow_id] == thread_id
    with pytest.raises(WorkflowNotInterruptedError):
        await runtime.resume(paused.workflow_id, {"decision": "aprobar"})
    assert len(repository.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("decision", "expected_stage", "expected_counter"),
    [
        ("devolver_analista", WorkflowStage.PO_APPROVAL, "analyst"),
        ("devolver_redactor", WorkflowStage.PO_APPROVAL, "draft"),
        ("devolver_asesor", WorkflowStage.PO_APPROVAL, "advisor"),
    ],
)
async def test_po_can_return_story_to_requested_stage_with_reason(decision, expected_stage, expected_counter):
    repository = _RepositoryDouble()
    counts = {"analyst": 0, "draft": 0, "advisor": 0}

    async def analyst(_state):
        counts["analyst"] += 1
        if counts["analyst"] > 1:
            assert _state.get("po_feedback") == "Ajustar la validación"
        return _analyst_response()

    async def draft(state):
        counts["draft"] += 1
        if counts["draft"] > 1:
            assert state.get("po_feedback") == "Ajustar la validación"
        return await _draft(state)

    async def advisor(_state):
        counts["advisor"] += 1
        if counts["advisor"] > 1:
            assert _state.get("po_feedback") == "Ajustar la validación"
        return await _advisor(_state)

    runtime = WorkflowRuntime(analyst=analyst, draft=draft, review=_review, advisor=advisor,
                              repository=repository)
    paused = await runtime.execute(WorkflowCreateRequest(
        mode=FlowMode.PRE_GROOMING, requirement="Consultar el saldo de cuentas activas",
    ))
    assert paused.current_stage == WorkflowStage.PO_APPROVAL
    before = counts[expected_counter]

    returned = await runtime.resume(paused.workflow_id, {
        "decision": decision, "reason": "Ajustar la validación",
    })

    assert returned.current_stage == expected_stage
    assert returned.status == WorkflowStatus.INTERRUPTED
    assert counts[expected_counter] == before + 1
    assert repository.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("decision", ["rechazar", "detener"])
async def test_po_reject_or_stop_ends_without_persisting(decision):
    repository = _RepositoryDouble()
    runtime, paused = await _runtime(repository)

    finished = await runtime.resume(paused.workflow_id, {"decision": decision, "reason": "No procede"})

    assert finished.status == WorkflowStatus.CANCELLED
    assert finished.persistence_result is None
    assert repository.calls == []


@pytest.mark.asyncio
async def test_repository_failure_is_reported_as_structured_persistence_result():
    class UnavailableRepository:
        def guardar_hu(self, _hu):
            raise ConnectionError("sensitive connection detail")

    runtime, paused = await _runtime(UnavailableRepository())

    failed = await runtime.resume(paused.workflow_id, {"decision": "aprobar"})

    assert failed.status == WorkflowStatus.FAILED
    assert failed.persistence_result.status == "failed"
    assert failed.persistence_result.error_code == "REPOSITORY_UNAVAILABLE"
    assert "sensitive" not in failed.completion_reason


def test_po_submission_rejects_unknown_decision_missing_return_reason_and_agent_fields():
    from agentes.analista.core.workflow_models import POApprovalSubmission

    for payload in (
        {"decision": "aprobar_automaticamente"},
        {"decision": "devolver_analista"},
        {"decision": "aprobar", "approved_by_agent": True},
    ):
        with pytest.raises(ValidationError):
            POApprovalSubmission.model_validate(payload)


@pytest.mark.asyncio
async def test_invalid_human_decision_does_not_resume_or_write():
    repository = _RepositoryDouble()
    runtime, paused = await _runtime(repository)

    with pytest.raises(ValidationError):
        await runtime.resume(paused.workflow_id, {"decision": "the_llm_says_yes"})

    assert runtime.get(paused.workflow_id).status == WorkflowStatus.INTERRUPTED
    assert repository.calls == []
