from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agentes.analista.core.agent_registry import AgentId
from agentes.equipo.asesor_tecnico.asesor_tecnico_service import AsesorTecnicoService
from agentes.analista.core.workflow_graph import WorkflowRuntime
from agentes.analista.core.workflow_models import (
    FlowMode,
    WorkflowCreateRequest,
    WorkflowStage,
    WorkflowStatus,
)
from agentes.analista.core.models import AgentTurnResponse, Analysis


@pytest.mark.asyncio
async def test_workflow_runs_advisor_before_the_story_and_surfaces_only_mocked_evidence():
    source_ref = "ejemplos/polizas_demo/servicios/primas.py"
    dependency_ref = "ejemplos/polizas_demo/mapa_dependencias.md"
    seen_calls = []
    generated = {
        "affected_modules": [{
            "source_id": source_ref,
            "source_ref": source_ref,
            "evidence": "El módulo define el cálculo ilustrativo de prima.",
        }],
        "dependencies": [{
            "source_id": dependency_ref,
            "source_ref": dependency_ref,
            "evidence": "El mapa relaciona el servicio de primas con el modelo de póliza.",
        }],
        "risks": [{
            "source_id": source_ref,
            "source_ref": source_ref,
            "evidence": "La fórmula se describe como ilustrativa, no actuarial.",
        }],
        "critical_processes": [],
        "uncertainties": ["No se consultó ningún sistema real de pólizas."],
    }

    async def source_provider(query):
        seen_calls.append(("sources", query))
        return ([{
            "source_id": source_ref,
            "source_ref": source_ref,
            "contenido": "def calcular_prima(...): fórmula ilustrativa",
            "contenido_no_confiable": True,
        }, {
            "source_id": dependency_ref,
            "source_ref": dependency_ref,
            "contenido": "servicios/primas.py depende de modelos.py",
            "contenido_no_confiable": True,
        }], [])

    class FakeOpenCode:
        def __init__(self, *, prompt, agent_id):
            assert agent_id == AgentId.TECHNICAL_ADVISOR
            assert "Asesor Técnico" in prompt.text
            self.settings = SimpleNamespace(turn_timeout_seconds=10)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def set_deadline(self, _deadline):
            pass

        async def server_info(self):
            return {"version": "2.0.27"}

        async def verify_agent(self, agent):
            seen_calls.append(("agent", agent))
            return {"id": "asesor_tecnico"}

        async def select_model(self, _agent):
            return {"id": "mock-model"}

        @asynccontextmanager
        async def session(self, *, title, model):
            assert title.startswith("Asesor Técnico")
            yield {"id": "mock-session"}

        async def submit_prompt(self, _session, prompt):
            seen_calls.append(("prompt", prompt))
            return {"time": {"created": 1}}

        async def wait_for_assistant(self, *_args, **_kwargs):
            return {"text": json.dumps(generated, ensure_ascii=False), "finish": "stop"}

    technical_advisor = AsesorTecnicoService(source_provider=source_provider, client_factory=FakeOpenCode)

    async def analyst(_state):
        return AgentTurnResponse(
            conversation_id=uuid4(), request_id=uuid4(), turn_id=uuid4(),
            estado="completado", respuesta_markdown="Requerimiento listo.",
            analisis=Analysis(conocida=["póliza demo"], faltante=[], supuesta=[], ambigua=[]),
            preguntas=[], fuentes_consultadas=[], listo_para_redactor=True,
            limitaciones=[], duracion_ms=1, prompt_version="1.0.0",
        )

    async def draft(_state):
        return {
            "como": "persona usuaria", "quiero": "calcular prima demo", "para": "ver un importe ficticio",
            "criterios": [{"dado": "una póliza demo", "cuando": "calculo", "entonces": "veo la prima"}],
        }

    async def review(_state):
        return {"requires_correction": False, "observations": []}

    async def advisor(state):
        seen_calls.append(("stage", state["current_stage"]))
        # El Asesor trabaja antes de la historia: todavía no hay borrador.
        assert "draft_story" not in state
        return await technical_advisor.assess(
            requirement=state["requirement_input"], story={"analisis_validado": state["analyst_response"]["analisis"]}
        )

    runtime = WorkflowRuntime(analyst=analyst, draft=draft, review=review, advisor=advisor)
    result = await runtime.execute(WorkflowCreateRequest(
        mode=FlowMode.PRE_GROOMING, requirement="Calcular prima ficticia para una póliza demo."
    ))

    assert result.current_stage == WorkflowStage.PO_APPROVAL
    assert result.status == WorkflowStatus.INTERRUPTED
    assert result.draft_story.review_status.value == "reviewed"
    assert result.technical_assessment.affected_modules[0].source_ref == source_ref
    assert result.technical_assessment.dependencies[0].source_ref == dependency_ref
    assert result.technical_assessment.risks[0].source_ref == source_ref
    assert [item.source_ref for item in result.technical_assessment.consulted_sources] == [source_ref, dependency_ref]
    assert [call[0] for call in seen_calls] == ["stage", "sources", "agent", "prompt"]
    assert "consulted_sources" not in seen_calls[3][1]
