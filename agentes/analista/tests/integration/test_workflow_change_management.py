from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agentes.analista.core.agent_registry import AgentId
from agentes.equipo.gestor_cambios.gestor_cambios_service import GestorCambiosService, ChangeManagerError
from agentes.analista.core.workflow_graph import WorkflowNotInterruptedError, WorkflowRuntime
from agentes.analista.core.workflow_models import (
    ChangeDecision,
    ChangeRecommendation,
    FlowMode,
    WorkflowCreateRequest,
    WorkflowStage,
    WorkflowStatus,
)
from agentes.analista.memory.repositorio import RepositorioError


APPROVED_ID = "2f1b2fe5-ec30-4c67-8c46-93ae3dd75a99"
APPROVED_HU = {
    "id": APPROVED_ID,
    "codigo": "HU-42",
    "titulo": "Consultar saldo",
    "tipo_informacion": "Historia de Usuario",
    "requerimiento": "Consultar saldo de una cuenta activa",
    "historia": '{"asA":"persona usuaria","iWant":"Consultar saldo","soThat":"conocer disponible"}',
    "criterios": '[{"dado":"cuenta activa","cuando":"consulto saldo","entonces":"veo disponible"}]',
    "aclaraciones": "[]",
    "aprobada_en": "2026-11-21T00:00:00+00:00",
}
REQUEST = "Añadir consulta de movimientos del último mes"


def _recommendation(kind="aclaracion"):
    return ChangeRecommendation.model_validate({
        "recommendation": kind,
        "comparison": [{
            "approved_excerpt": "Consultar saldo",
            "request_excerpt": "consulta de movimientos",
            "explanation": "La solicitud agrega una consulta distinta de saldo.",
        }],
        "impact": ["La petición necesita aclarar si busca solo saldo o también movimientos."],
        "rationale": "La solicitud puede precisar el comportamiento aprobado sin agregar alcance confirmado.",
        "uncertainties": ["No se especificó el período de retención de movimientos."],
        "lessons_proposed": [{
            "category": "Reglas de negocio",
            "suggested_question": "¿Qué período de movimientos debe consultarse?",
            "terms": ["movimientos", "período"],
        }],
    })


class RepositoryDouble:
    def __init__(self, *, missing=False):
        self.missing = missing
        self.calls = []
        self.human_lessons = []
        self.saved = []

    def obtener_hu(self, hu_id):
        self.calls.append(("obtener_hu", hu_id))
        if self.missing or hu_id != APPROVED_ID:
            raise RepositorioError("not found", not_found=True)
        return dict(APPROVED_HU)

    def registrar_cambio(self, **kwargs):
        self.calls.append(("registrar_cambio", kwargs))
        lesson_ids = [f"lesson-{i}" for i, _ in enumerate(kwargs.get("lecciones_propuestas", []))]
        return {"solicitud_id": kwargs["cambio_id"], "leccion_ids": lesson_ids}

    def decidir_leccion(self, lesson_id, decision):
        self.human_lessons.append((lesson_id, decision))
        return {"id": lesson_id, "estado": "aprobada" if decision == "aprobar" else "rechazada"}

    def guardar_hu(self, hu):
        self.saved.append(hu)
        return {"id": hu["id"], "titulo": hu["titulo"], "aprobada_en": "2026-11-22T00:00:00+00:00"}


def _post_request():
    return WorkflowCreateRequest(
        mode=FlowMode.POST_GROOMING,
        approved_story_id=APPROVED_ID,
        change_request=REQUEST,
    )


@pytest.mark.asyncio
async def test_change_manager_reads_approved_story_and_uses_dedicated_external_prompt():
    outputs = ['{"razonamiento":"Reviso lecciones previas.","consultas":[{"herramienta":"consultar_lecciones","consulta":"movimientos"}]}',
               '''{"recommendation":"aclaracion","comparison":[{"approved_excerpt":"Consultar saldo",'''
               '''"request_excerpt":"consulta de movimientos","explanation":"La petición agrega movimientos."}],'''
               '''"impact":["Se debe aclarar el período."],"rationale":"La HU no establece el período.",'''
               '''"uncertainties":["No se indicó el período."],"lessons_proposed":[]}''']
    requests = []

    class FakeOpenCodeClient:
        def __init__(self, *, prompt, agent_id):
            assert agent_id == AgentId.CHANGE_MANAGER
            assert "Gestor de Cambios" in prompt.text
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
            assert agent == AgentId.CHANGE_MANAGER
            return {"id": "gestor_cambios"}

        async def select_model(self, _agent):
            return {"providerID": "opencode", "id": "fake-model"}

        @asynccontextmanager
        async def session(self, *, title, model):
            assert title.startswith("Gestor de Cambios")
            assert model["id"] == "fake-model"
            yield {"id": "fake-session"}

        async def submit_prompt(self, _session, prompt):
            requests.append(prompt)
            assert '"approved_story_id"' not in prompt  # only approved-story fields reach the prompt
            assert '"Consultar saldo"' in prompt
            assert REQUEST in prompt
            return {"time": {"created": 1}}

        async def wait_for_assistant(self, _session, *, deadline, after=None):
            assert deadline > 0
            return {"text": outputs.pop(0)}

    repository = RepositoryDouble()
    result = await GestorCambiosService(client_factory=FakeOpenCodeClient).evaluate(
        approved_story_id=APPROVED_ID, change_request=REQUEST, repository=repository,
    )
    assert result.recommendation.value == "aclaracion"
    assert result.comparison[0].approved_excerpt == "Consultar saldo"
    assert result.impact and result.rationale
    assert repository.calls == [("obtener_hu", APPROVED_ID)]
    assert len(requests) == 2  # plan del Gestor + comparación final
    assert requests[0].startswith("FASE DE PLANIFICACIÓN")
    assert '"nombre":"consultar_lecciones"' in requests[1]


@pytest.mark.asyncio
async def test_change_manager_refuses_missing_approved_story_before_calling_opencode():
    class NeverCall:
        def __init__(self, **_kwargs):
            pytest.fail("OpenCode must not receive an unapproved or missing HU")

    with pytest.raises(ChangeManagerError, match="HU aprobada"):
        await GestorCambiosService(client_factory=NeverCall).evaluate(
            approved_story_id=APPROVED_ID, change_request=REQUEST,
            repository=RepositoryDouble(missing=True),
        )


@pytest.mark.asyncio
async def test_change_manager_rejects_comparison_excerpts_not_present_in_source_text():
    output = '''{"recommendation":"cambio_alcance","comparison":[{"approved_excerpt":"dato inventado",'''
    output += '''"request_excerpt":"consulta de movimientos","explanation":"texto no sustentado"}],'''
    output += '''"impact":["Impacto"],"rationale":"Justificación","lessons_proposed":[]}'''

    class FakeOpenCodeClient:
        def __init__(self, *, prompt, agent_id):
            assert agent_id == AgentId.CHANGE_MANAGER
            self.settings = SimpleNamespace(turn_timeout_seconds=30)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def set_deadline(self, _deadline):
            pass

        async def server_info(self):
            return {"version": "2.0.27"}

        async def verify_agent(self, _agent):
            return {"id": "gestor_cambios"}

        async def select_model(self, _agent):
            return {"providerID": "opencode", "id": "fake-model"}

        @asynccontextmanager
        async def session(self, **_kwargs):
            yield {"id": "fake-session"}

        async def submit_prompt(self, *_args):
            return {"time": {"created": 1}}

        async def wait_for_assistant(self, *_args, **_kwargs):
            return {"text": output}

    with pytest.raises(ChangeManagerError, match="comparación válida"):
        await GestorCambiosService(client_factory=FakeOpenCodeClient).evaluate(
            approved_story_id=APPROVED_ID, change_request=REQUEST, repository=RepositoryDouble(),
        )


@pytest.mark.parametrize("kind", ["aclaracion", "cambio_alcance"])
@pytest.mark.asyncio
async def test_post_grooming_requires_human_decision_and_keeps_lessons_proposed(kind):
    repository = RepositoryDouble()

    async def manager(state, repo):
        assert state["approved_story_id"] == APPROVED_ID
        assert repo is repository
        return _recommendation(kind)

    runtime = WorkflowRuntime(repository=repository, change_manager=manager)
    paused = await runtime.execute(_post_request())

    assert paused.current_stage == WorkflowStage.HUMAN_DECISION
    assert paused.status == WorkflowStatus.INTERRUPTED
    assert paused.change_recommendation.recommendation.value == kind
    assert paused.change_recommendation.rationale
    assert paused.change_recommendation.impact
    assert "approved" not in paused.change_recommendation.model_dump()
    assert paused.change_recommendation.lessons_proposed[0].suggested_question
    assert repository.calls == [("obtener_hu", APPROVED_ID)]
    assert not any(kind == "registrar_cambio" for kind, _ in repository.calls)
    assert repository.human_lessons == []
    assert repository.saved == []


def test_change_recommendation_contract_rejects_agent_approval_fields():
    payload = _recommendation().model_dump(mode="json")
    payload["approved"] = True
    with pytest.raises(ValidationError):
        ChangeRecommendation.model_validate(payload)


@pytest.mark.asyncio
async def test_human_apply_registers_change_once_and_does_not_approve_proposed_lesson_automatically():
    repository = RepositoryDouble()

    async def manager(_state, _repo):
        return _recommendation("aclaracion")

    runtime = WorkflowRuntime(repository=repository, change_manager=manager)
    paused = await runtime.execute(_post_request())
    thread_id = runtime._threads[paused.workflow_id]

    finished = await runtime.resume(paused.workflow_id, {"decision": "aplicar"})

    assert finished.status == WorkflowStatus.COMPLETED
    assert finished.change_decision.decision == ChangeDecision.APPLY
    assert finished.change_persistence_result.status == "recorded"
    assert runtime._threads[paused.workflow_id] == thread_id
    registered = [entry for entry in repository.calls if entry[0] == "registrar_cambio"]
    assert len(registered) == 1
    assert registered[0][1]["clasificacion"] == "aclaracion"
    assert registered[0][1]["cambio_id"] == str(paused.workflow_id)
    assert repository.human_lessons == []
    with pytest.raises(WorkflowNotInterruptedError):
        await runtime.resume(paused.workflow_id, {"decision": "aplicar"})
    assert len([entry for entry in repository.calls if entry[0] == "registrar_cambio"]) == 1


@pytest.mark.asyncio
async def test_human_can_explicitly_decide_a_proposed_lesson():
    repository = RepositoryDouble()

    async def manager(_state, _repo):
        return _recommendation("aclaracion")

    runtime = WorkflowRuntime(repository=repository, change_manager=manager)
    paused = await runtime.execute(_post_request())
    await runtime.resume(paused.workflow_id, {
        "decision": "aplicar", "lesson_decisions": [{"index": 0, "decision": "aprobar"}],
    })
    assert repository.human_lessons == [("lesson-0", "aprobar")]


@pytest.mark.asyncio
async def test_return_routes_to_new_analysis_and_waits_for_po_before_recording():
    repository = RepositoryDouble()

    async def analyst(_state):
        return {
            "conversation_id": str(uuid4()), "request_id": str(uuid4()), "turn_id": str(uuid4()),
            "estado": "completado", "respuesta_markdown": "Análisis devuelto.",
            "analisis": {"conocida": ["La solicitud pide movimientos"], "faltante": [],
                         "supuesta": [], "ambigua": []},
            "preguntas": [], "fuentes_consultadas": [], "listo_para_redactor": True,
            "limitaciones": [], "duracion_ms": 1, "prompt_version": "1.0.0",
        }

    async def manager(_state, _repo):
        return _recommendation("cambio_alcance")

    async def draft(_state):
        return {
            "como": "persona usuaria", "quiero": "consultar movimientos",
            "para": "conocer operaciones recientes",
            "criterios": [{"dado": "una cuenta activa", "cuando": "consulto movimientos",
                           "entonces": "veo operaciones recientes"}],
        }

    async def review(_state):
        return {"requires_correction": False, "observations": []}

    async def advisor(_state):
        return {"affected_modules": [], "dependencies": [], "risks": [], "critical_processes": [],
                "consulted_sources": [], "uncertainties": ["Prueba simulada."]}

    runtime = WorkflowRuntime(
        analyst=analyst, draft=draft, review=review, advisor=advisor,
        repository=repository, change_manager=manager,
    )
    paused = await runtime.execute(_post_request())
    returned = await runtime.resume(paused.workflow_id, {"decision": "devolver", "reason": "Precisar datos"})

    assert returned.current_stage == WorkflowStage.PO_APPROVAL
    assert not any(entry[0] == "registrar_cambio" for entry in repository.calls)
    assert repository.saved == []
    final = await runtime.resume(paused.workflow_id, {"decision": "aprobar"})
    assert final.status == WorkflowStatus.COMPLETED
    assert len([entry for entry in repository.calls if entry[0] == "registrar_cambio"]) == 1


@pytest.mark.asyncio
async def test_invalid_human_decision_and_duplicate_resume_do_not_duplicate_writes():
    repository = RepositoryDouble()

    async def manager(_state, _repo):
        return _recommendation()

    runtime = WorkflowRuntime(repository=repository, change_manager=manager)
    paused = await runtime.execute(_post_request())
    with pytest.raises(ValidationError):
        await runtime.resume(paused.workflow_id, {"decision": "the_agent_approved"})
    assert runtime.get(paused.workflow_id).status == WorkflowStatus.INTERRUPTED
    assert not any(entry[0] == "registrar_cambio" for entry in repository.calls)

    await runtime.resume(paused.workflow_id, {"decision": "rechazar"})
    with pytest.raises(WorkflowNotInterruptedError):
        await runtime.resume(paused.workflow_id, {"decision": "rechazar"})
    assert not any(entry[0] == "registrar_cambio" for entry in repository.calls)


@pytest.mark.asyncio
async def test_out_of_range_lesson_decision_does_not_write():
    repository = RepositoryDouble()

    async def manager(_state, _repo):
        return _recommendation()

    runtime = WorkflowRuntime(repository=repository, change_manager=manager)
    paused = await runtime.execute(_post_request())
    with pytest.raises(ValueError, match="lección"):
        await runtime.resume(paused.workflow_id, {
            "decision": "aplicar", "lesson_decisions": [{"index": 3, "decision": "aprobar"}],
        })
    assert not any(entry[0] == "registrar_cambio" for entry in repository.calls)


@pytest.mark.asyncio
async def test_scope_change_leads_to_new_analysis_and_waits_for_po_approval():
    repository = RepositoryDouble()
    analysis_inputs = []

    async def analyst(state):
        analysis_inputs.append(state["requirement_input"])
        return {
            "conversation_id": str(uuid4()), "request_id": str(uuid4()), "turn_id": str(uuid4()),
            "estado": "completado", "respuesta_markdown": "Análisis del cambio.",
            "analisis": {"conocida": ["Se solicitó consultar movimientos"], "faltante": [],
                         "supuesta": [], "ambigua": []},
            "preguntas": [], "fuentes_consultadas": [], "listo_para_redactor": True,
            "limitaciones": [], "duracion_ms": 1, "prompt_version": "1.0.0",
        }

    async def draft(_state):
        return {
            "como": "persona usuaria", "quiero": "consultar saldo y movimientos",
            "para": "conocer operaciones recientes",
            "criterios": [{"dado": "cuenta activa", "cuando": "consulto movimientos",
                           "entonces": "veo operaciones recientes"}],
        }

    async def review(_state):
        return {"requires_correction": False, "observations": []}

    async def advisor(_state):
        return {"affected_modules": [], "dependencies": [], "risks": [], "critical_processes": [],
                "consulted_sources": [], "uncertainties": ["Prueba simulada."]}

    async def manager(_state, _repo):
        return _recommendation("cambio_alcance")

    runtime = WorkflowRuntime(
        analyst=analyst, draft=draft, review=review, advisor=advisor,
        repository=repository, change_manager=manager,
    )
    paused = await runtime.execute(_post_request())
    after_apply = await runtime.resume(paused.workflow_id, {"decision": "aplicar"})

    assert after_apply.status == WorkflowStatus.INTERRUPTED
    assert after_apply.current_stage == WorkflowStage.PO_APPROVAL
    assert "approved_story" in analysis_inputs[0]
    assert REQUEST in analysis_inputs[0]
    assert repository.saved == []
    assert len([entry for entry in repository.calls if entry[0] == "registrar_cambio"]) == 1

    final = await runtime.resume(paused.workflow_id, {"decision": "aprobar"})
    assert final.status == WorkflowStatus.COMPLETED
    assert final.persistence_result.story_id == APPROVED_ID
    assert repository.saved[0]["id"] == APPROVED_ID

