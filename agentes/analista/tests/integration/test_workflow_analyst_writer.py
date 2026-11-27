from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agentes.equipo.analista import analista_service as orchestrator
from agentes.equipo.redactor_revisor import redactor_revisor_service as redactor_revisor
from agentes.analista.core.agent_registry import AgentId
from agentes.analista.core.models import (
    AgentTurnResponse,
    Analysis,
    Question,
    QuestionCategory,
    QuestionState,
)
from agentes.analista.core.workflow_graph import WorkflowRuntime
from agentes.analista.core.workflow_models import (
    FlowMode,
    WorkflowCreateRequest,
    WorkflowStage,
    WorkflowStatus,
)


def _analyst_response(*, ready: bool, pending: bool = False) -> AgentTurnResponse:
    questions = [Question(
        question_id="q-deadline",
        categoria=QuestionCategory.REQUIRED_DATA,
        pregunta="¿Cuál es el plazo de entrega?",
        estado=QuestionState.PENDING if pending else QuestionState.ANSWERED,
    )] if pending else []
    return AgentTurnResponse(
        conversation_id=uuid4(),
        request_id=uuid4(),
        turn_id=uuid4(),
        estado="completado",
        respuesta_markdown="Análisis actualizado.",
        analisis=Analysis(
            conocida=["El usuario solicita consultar saldos."],
            faltante=[] if ready else ["Plazo de entrega"],
            supuesta=[],
            ambigua=[],
        ),
        preguntas=questions,
        fuentes_consultadas=[],
        listo_para_redactor=ready,
        limitaciones=[],
        duracion_ms=1,
        prompt_version="1.0.0",
    )


async def _empty_technical_assessment(_state):
    return {
        "affected_modules": [], "dependencies": [], "risks": [], "critical_processes": [],
        "consulted_sources": [], "uncertainties": ["Integración aislada del Asesor Técnico."],
    }


@pytest.mark.asyncio
async def test_pending_business_question_interrupts_resumes_and_calls_existing_run_turn(monkeypatch):
    analyst_messages = []
    answered_ids = []
    responses = [_analyst_response(ready=False, pending=True), _analyst_response(ready=True)]

    async def isolated_run_turn(store, conversation_id, request, *, observability=None, respondidas=None):
        assert store is not None
        assert conversation_id
        assert observability is not None
        analyst_messages.append(request.message)
        answered_ids.append(set(respondidas or ()))
        return responses.pop(0)

    monkeypatch.setattr(orchestrator, "run_turn", isolated_run_turn)

    draft_calls = []

    async def draft(_state):
        draft_calls.append(True)
        return {
            "como": "persona usuaria", "quiero": "consultar saldo", "para": "conocer el disponible",
            "criterios": [{"dado": "una cuenta activa", "cuando": "consulto", "entonces": "veo el saldo"}],
        }

    async def review(_state):
        return {"requires_correction": False, "observations": []}

    runtime = WorkflowRuntime(draft=draft, review=review, advisor=_empty_technical_assessment)
    paused = await runtime.execute(WorkflowCreateRequest(
        mode=FlowMode.PRE_GROOMING, requirement="Consultar saldos de cuentas activas"
    ))

    assert paused.current_stage == WorkflowStage.BUSINESS_WAIT
    assert paused.status == WorkflowStatus.INTERRUPTED
    assert [item.question_id for item in paused.pending_questions] == ["q-deadline"]
    assert draft_calls == []

    # El Asesor trabajó antes de ir a Negocio (sin decisiones); al responder, el Analista termina y se redacta.
    finished = await runtime.resume(paused.workflow_id, {
        "answers": [{"question_id": "q-deadline", "answer": "14 días"}],
    })

    assert analyst_messages[0] == "Consultar saldos de cuentas activas"
    # El Analista recibe la pregunta con su respuesta, y el backend la marca como respondida.
    assert "Respuesta: 14 días" in analyst_messages[1]
    assert "Pregunta (id: q-deadline): ¿Cuál es el plazo de entrega?" in analyst_messages[1]
    assert answered_ids == [set(), {"q-deadline"}]
    assert len(draft_calls) == 1
    assert finished.current_stage == WorkflowStage.PO_APPROVAL
    assert finished.status == WorkflowStatus.INTERRUPTED
    assert finished.draft_story.review_status.value == "reviewed"
    assert "approved" not in finished.draft_story.model_dump()


@pytest.mark.asyncio
async def test_unresolved_gaps_without_questions_never_reach_writer():
    async def analyst(_state):
        return _analyst_response(ready=False)

    async def draft(_state):
        pytest.fail("El Redactor no debe ejecutarse si el Analista no marcó listo.")

    async def review(_state):
        pytest.fail("El Revisor no debe ejecutarse si no existe borrador.")

    runtime = WorkflowRuntime(analyst=analyst, draft=draft, review=review, advisor=_empty_technical_assessment)
    result = await runtime.execute(WorkflowCreateRequest(
        mode=FlowMode.PRE_GROOMING, requirement="Consultar un saldo"
    ))
    assert result.current_stage == WorkflowStage.ANALYST
    assert result.draft_story is None
    assert result.status == WorkflowStatus.FAILED
    assert "vacíos" in result.completion_reason


@pytest.mark.asyncio
async def test_writer_review_loop_allows_two_corrections_then_stops_for_po(monkeypatch):
    simulated_outputs = [
        '{"como":"persona usuaria","quiero":"consultar saldo","para":"conocer el disponible",'
        '"criterios":[{"dado":"una cuenta activa","cuando":"consulto", "entonces":"veo el saldo"}]}',
        '{"requires_correction":true,"observations":["Aclarar el comportamiento sin saldo"]}',
        '{"como":"persona usuaria","quiero":"consultar saldo","para":"conocer el disponible",'
        '"criterios":[{"dado":"una cuenta activa","cuando":"no hay saldo", "entonces":"veo cero"}]}',
        '{"requires_correction":true,"observations":["Especificar el formato de moneda"]}',
        '{"como":"persona usuaria","quiero":"consultar saldo","para":"conocer el disponible",'
        '"criterios":[{"dado":"una cuenta activa","cuando":"no hay saldo", "entonces":"veo 0.00"}]}',
        '{"requires_correction":true,"observations":["PO debe validar presentación final"]}',
    ]
    opencode_agents = []

    class SimulatedOpenCode:
        def __init__(self, *, prompt, agent_id):
            assert prompt.text
            opencode_agents.append(agent_id)
            self.settings = SimpleNamespace(turn_timeout_seconds=30)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def set_deadline(self, _deadline):
            pass

        async def server_info(self):
            return {"version": "2.0.27"}

        async def verify_agent(self, agent):
            assert agent == AgentId.WRITER_REVIEWER
            return {"id": agent.value}

        async def select_model(self, _agent):
            return {"providerID": "opencode", "id": "simulated"}

        @asynccontextmanager
        async def session(self, *, title, model):
            yield {"id": "fake-session"}

        async def submit_prompt(self, _session_id, prompt):
            self.last_prompt = prompt
            return {"time": {"created": len(opencode_agents)}}

        async def wait_for_assistant(self, _session_id, *, deadline, after=None):
            if self.last_prompt.startswith("FASE DE PLANIFICACIÓN"):
                return {"text": '{"razonamiento":"Sin consultas adicionales.","consultas":[]}', "finish": "stop"}
            return {"text": simulated_outputs.pop(0), "finish": "stop"}

    monkeypatch.setattr(redactor_revisor, "OpenCodeClient", SimulatedOpenCode)
    writer = redactor_revisor.RedactorRevisorService()

    async def analyst(_state):
        return _analyst_response(ready=True)

    async def draft(state):
        return await writer.draft(
            requirement=state["requirement_input"],
            analyst_response=state["analyst_response"],
            previous_story=state.get("draft_story"),
            observations=state.get("review_observations", []),
        )

    async def review(state):
        return await writer.review(
            requirement=state["requirement_input"],
            analyst_response=state["analyst_response"],
            story=state["draft_story"],
        )

    runtime = WorkflowRuntime(analyst=analyst, draft=draft, review=review, advisor=_empty_technical_assessment)
    result = await runtime.execute(WorkflowCreateRequest(
        mode=FlowMode.PRE_GROOMING, requirement="Consultar saldos de cuentas activas"
    ))

    assert result.current_stage == WorkflowStage.PO_APPROVAL
    assert result.status == WorkflowStatus.INTERRUPTED
    assert result.draft_story.review_round == 2
    assert result.draft_story.review_status.value == "needs_attention"
    assert len(result.review_observations) == 3
    assert result.completion_reason == "La revisión agotó dos rondas; requiere revisión del PO."
    assert len(simulated_outputs) == 0
    assert opencode_agents == [AgentId.WRITER_REVIEWER] * 6
    assert "approved" not in result.draft_story.model_dump()
