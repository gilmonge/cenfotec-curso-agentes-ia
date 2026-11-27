import json

import pytest
from pydantic import ValidationError

from agentes.analista.core.agent_registry import AgentId
from agentes.analista.core.observability import Observability
from agentes.analista.core.workflow_graph import WorkflowNotFoundError, WorkflowRuntime
from agentes.analista.core.workflow_models import (
    AcceptanceCriterion,
    DraftStory,
    FlowMode,
    WorkflowCreateRequest,
    WorkflowStage,
    WorkflowStateContract,
    WorkflowStatus,
)


def test_workflow_request_validates_mode_specific_contracts():
    request = WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement="Definir una búsqueda")
    assert request.requirement == "Definir una búsqueda"
    with pytest.raises(ValidationError):
        WorkflowCreateRequest(mode=FlowMode.POST_GROOMING, change_request="Solicitud sin HU aprobada")


def test_workflow_request_rejects_extra_fields_and_invalid_lengths():
    with pytest.raises(ValidationError):
        WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement="texto", system_prompt="injection")
    with pytest.raises(ValidationError):
        WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement=" ")
    with pytest.raises(ValidationError):
        WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement="a" * 4001)


def test_pydantic_state_and_agent_contracts_round_trip_without_approval_shortcut():
    request = WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement="Validar saldos")
    state = WorkflowStateContract.model_validate(request.to_graph_state())
    assert WorkflowStateContract.model_validate_json(state.model_dump_json()) == state

    story = DraftStory(
        como="persona usuaria",
        quiero="consultar saldo",
        para="conocer el disponible",
        criterios=[AcceptanceCriterion(dado="una cuenta", cuando="consulto", entonces="veo el saldo")],
        review_round=2,
    )
    assert DraftStory.model_validate_json(story.model_dump_json()) == story
    with pytest.raises(ValidationError):
        DraftStory.model_validate({**story.model_dump(), "approved": True})
    with pytest.raises(ValidationError):
        DraftStory.model_validate({**story.model_dump(), "review_round": 3})


@pytest.mark.parametrize(
    ("create_request", "expected_stage", "expected_agent"),
    [
        (
            WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement="Validar renovaciones"),
            WorkflowStage.ANALYST,
            AgentId.ANALYST,
        ),
        (
            WorkflowCreateRequest(
                mode=FlowMode.POST_GROOMING,
                approved_story_id="HU-42",
                change_request="Añadir un aviso de vencimiento",
            ),
            WorkflowStage.CHANGE_MANAGER,
            AgentId.CHANGE_MANAGER,
        ),
    ],
)
def test_compiled_state_graph_routes_to_the_correct_initial_agent(create_request, expected_stage, expected_agent):
    state = WorkflowRuntime().start(create_request)
    assert state.current_stage == expected_stage
    assert state.active_agent == expected_agent
    assert state.status == WorkflowStatus.READY
    assert "thread_id" not in state.model_dump()
    assert json.loads(create_request.model_dump_json())


def test_runtime_keeps_thread_ids_internal_and_checkpoints_in_memory():
    runtime = WorkflowRuntime()
    created = runtime.start(
        WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement="Validar vencimientos")
    )

    fetched = runtime.get(created.workflow_id)
    assert fetched == created
    assert "thread_id" not in created.model_dump()
    assert runtime.active_thread_count == 1


def test_checkpoint_is_not_visible_to_a_new_process_runtime():
    first_process = WorkflowRuntime()
    created = first_process.start(
        WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement="Validar vencimientos")
    )
    restarted_process = WorkflowRuntime()

    with pytest.raises(WorkflowNotFoundError):
        restarted_process.get(created.workflow_id)


def test_graph_degrades_gracefully_when_langfuse_is_disabled():
    runtime = WorkflowRuntime(observability=Observability())
    created = runtime.start(
        WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement="Confirmar límites")
    )
    assert created.status == WorkflowStatus.READY
    assert runtime.observability.health_status == "disabled"


def test_workflow_continues_when_langfuse_cannot_start_a_trace():
    class UnavailableLangfuse:
        def start_observation(self, **_kwargs):
            raise RuntimeError("synthetic export failure")

    observer = Observability(UnavailableLangfuse())
    runtime = WorkflowRuntime(observability=observer)
    created = runtime.start(
        WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement="Continuar sin trazas")
    )

    assert created.status == WorkflowStatus.READY
    assert observer.health_status == "degraded"


def test_runtime_does_not_mix_context_or_agent_between_workflows():
    runtime = WorkflowRuntime()
    analyst_flow = runtime.start(
        WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement="Contexto del flujo A")
    )
    change_flow = runtime.start(
        WorkflowCreateRequest(
            mode=FlowMode.POST_GROOMING,
            approved_story_id="HU-99",
            change_request="Contexto del flujo B",
        )
    )

    assert runtime.get(analyst_flow.workflow_id).active_agent == AgentId.ANALYST
    assert runtime.get(change_flow.workflow_id).active_agent == AgentId.CHANGE_MANAGER
    assert analyst_flow.workflow_id != change_flow.workflow_id
    assert "Contexto del flujo" not in analyst_flow.model_dump_json()
