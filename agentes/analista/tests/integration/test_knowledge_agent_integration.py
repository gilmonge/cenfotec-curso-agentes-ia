from __future__ import annotations

from uuid import uuid4

import pytest

from agentes.analista.core import workflow_graph
from agentes.analista.core.agent_registry import AgentId
from agentes.analista.core.models import AgentTurnResponse, Analysis
from agentes.analista.core.workflow_graph import WorkflowRuntime
from agentes.analista.core.workflow_models import (
    ChangeRecommendation,
    FlowMode,
    WorkflowCreateRequest,
    WorkflowStage,
    WorkflowStatus,
)
from agentes.conocimiento.retrieval import KnowledgeSource, RetrievalResult


APPROVED_ID = "2f1b2fe5-ec30-4c67-8c46-93ae3dd75a99"


def _ready_analysis():
    return AgentTurnResponse(
        conversation_id=uuid4(), request_id=uuid4(), turn_id=uuid4(), estado="completado",
        respuesta_markdown="Análisis listo", analisis=Analysis(conocida=["consulta póliza"], faltante=[], supuesta=[], ambigua=[]),
        preguntas=[], fuentes_consultadas=[], listo_para_redactor=True, limitaciones=[], duracion_ms=1,
        prompt_version="1.0.0",
    )


async def _assessment(_state):
    return {
        "affected_modules": [], "dependencies": [], "risks": [], "critical_processes": [],
        "consulted_sources": [], "uncertainties": ["prueba aislada"],
    }


_TEXT_BY_NAMESPACE = {
    "estandares": {"id": "STD-PRUEBA", "titulo": "Criterios observables", "regla": "Cada criterio es verificable.", "referencia": "Estándar ficticio"},
    "checklist": {"id": "CHK-PRUEBA", "categoria": "Validaciones", "descripcion": "¿Qué validación aplica?"},
    "hu_aprobadas": {"id": "HU-PRUEBA", "titulo": "HU parecida", "resumen": "Consulta de vigencia", "aclaraciones": [], "similitud": 0.5},
    "lecciones": {"id": "LEC-PRUEBA", "categoria": "Datos requeridos", "descripcion": "Confirmar formato", "evidencia": "Lección aprobada"},
}


def _result(namespace):
    import json

    return RetrievalResult(
        status="degraded", backend="local", namespace=namespace,
        sources=[KnowledgeSource(
            source_id=f"src-{namespace}", source_kind="simulated_fixture",
            source_ref=f"agentes/analista/fuentes/{namespace}.json#src-{namespace}",
            namespace=namespace, chunk=0, score=0.5, backend="local",
            citation=f"agentes/analista/fuentes/{namespace}.json#src-{namespace}",
            text=json.dumps(_TEXT_BY_NAMESPACE[namespace], ensure_ascii=False),
        )],
    )


class RetrieverSpy:
    def __init__(self):
        self.calls = []

    def search(self, *, agent_role, query, namespace, limit):
        self.calls.append((agent_role, namespace, query, limit))
        return _result(namespace)


def _fake_opencode(expected_agent, queue, prompts):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    class FakeOpenCode:
        def __init__(self, *, prompt, agent_id):
            assert agent_id == expected_agent
            self.settings = SimpleNamespace(turn_timeout_seconds=20)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def set_deadline(self, _deadline):
            pass

        async def server_info(self):
            return {"version": "2.0.27"}

        async def verify_agent(self, agent):
            return {"id": str(agent)}

        async def select_model(self, _agent):
            return {"providerID": "mock", "id": "mock"}

        @asynccontextmanager
        async def session(self, *, title, model):
            yield {"id": "mock-session"}

        async def submit_prompt(self, _session_id, prompt):
            prompts.append(prompt)
            return {"time": {"created": len(prompts)}}

        async def wait_for_assistant(self, *_args, **_kwargs):
            return {"text": queue.pop(0), "finish": "stop"}

    return FakeOpenCode


@pytest.mark.asyncio
async def test_redactor_plans_and_gets_its_evidence_only_through_its_mcp_server(monkeypatch):
    import json

    from agentes.equipo.redactor_revisor import redactor_revisor_service as redactor_revisor

    prompts, queue = [], [
        json.dumps({"razonamiento": "Estándares y HU parecidas.", "consultas": [
            {"herramienta": "consultar_estandares", "consulta": "criterios observables"},
            {"herramienta": "aplicar_checklist_vacios", "consulta": "vigencia de póliza"},
            {"herramienta": "buscar_hu_similares", "consulta": "vigencia de póliza"},
        ]}),
        json.dumps({"como": "persona usuaria", "quiero": "consultar póliza", "para": "ver vigencia",
                    "criterios": [{"dado": "póliza activa", "cuando": "consulto", "entonces": "veo vigencia"}]}),
        json.dumps({"consultas": [{"herramienta": "consultar_estandares", "consulta": "criterios observables"}]}),
        json.dumps({"requires_correction": False, "observations": []}),
    ]
    monkeypatch.setattr(redactor_revisor, "OpenCodeClient", _fake_opencode(AgentId.WRITER_REVIEWER, queue, prompts))
    retriever = RetrieverSpy()

    async def analyst(_state):
        return _ready_analysis()

    runtime = WorkflowRuntime(analyst=analyst, advisor=_assessment, knowledge_retriever=retriever)
    result = await runtime.execute(WorkflowCreateRequest(
        mode=FlowMode.PRE_GROOMING, requirement="Consultar vigencia de póliza",
    ))

    assert result.current_stage == WorkflowStage.PO_APPROVAL
    assert result.status == WorkflowStatus.INTERRUPTED
    assert not queue
    assert {namespace for _role, namespace, _query, _limit in retriever.calls} == {"estandares", "checklist", "hu_aprobadas"}
    assert all(role == AgentId.WRITER_REVIEWER for role, _namespace, _query, _limit in retriever.calls)
    # La evidencia que el agente eligió llega a su prompt final de redacción y de revisión.
    assert "STD-PRUEBA" in prompts[1] and "HU-PRUEBA" in prompts[1] and "CHK-PRUEBA" in prompts[1]
    assert "STD-PRUEBA" in prompts[3] and "HU-PRUEBA" not in prompts[3]


def _approved_repository():
    class Repository:
        def obtener_hu(self, hu_id):
            assert hu_id == APPROVED_ID
            return {
                "id": APPROVED_ID, "titulo": "HU aprobada", "tipo_informacion": "HU",
                "requerimiento": "Consultar saldo", "historia": '{"asA":"persona","iWant":"saldo","soThat":"ver"}',
                "criterios": "[]", "aclaraciones": "[]", "aprobada_en": "2026-11-20T00:00:00+00:00",
            }

    return Repository()


_RECOMMENDATION = {
    "recommendation": "aclaracion", "comparison": [{
        "approved_excerpt": "Consultar saldo", "request_excerpt": "Consultar movimientos",
        "explanation": "La solicitud requiere confirmar la diferencia.",
    }], "impact": ["requiere decisión humana"],
    "rationale": "Se requiere confirmar alcance.", "uncertainties": ["dato pendiente"],
    "lessons_proposed": [],
}


@pytest.mark.asyncio
async def test_change_manager_reads_only_approved_namespaces_through_its_mcp_server(monkeypatch):
    import json

    from agentes.equipo.gestor_cambios import gestor_cambios_service as change_manager

    prompts, queue = [], [
        json.dumps({"razonamiento": "Busco cambios parecidos y lecciones.", "consultas": [
            {"herramienta": "buscar_hu_similares", "consulta": "saldo y movimientos"},
            {"herramienta": "consultar_lecciones", "consulta": "movimientos del mes"},
            {"herramienta": "consultar_glosario", "consulta": "saldo"},
        ], "consultar_asesor": False}),
        json.dumps(_RECOMMENDATION),
    ]
    monkeypatch.setattr(change_manager, "OpenCodeClient", _fake_opencode(AgentId.CHANGE_MANAGER, queue, prompts))
    retriever = RetrieverSpy()
    runtime = WorkflowRuntime(repository=_approved_repository(), knowledge_retriever=retriever)
    result = await runtime.execute(WorkflowCreateRequest(
        mode=FlowMode.POST_GROOMING, approved_story_id=APPROVED_ID,
        change_request="Consultar movimientos del mes",
    ))

    assert result.current_stage == WorkflowStage.HUMAN_DECISION
    assert result.status == WorkflowStatus.INTERRUPTED
    assert {namespace for _role, namespace, _query, _limit in retriever.calls} == {"hu_aprobadas", "lecciones"}
    assert all(role == AgentId.CHANGE_MANAGER for role, _namespace, _query, _limit in retriever.calls)
    assert "consultar_asesor_tecnico" in prompts[0]  # el Gestor puede pedir criterio técnico
    assert "HU-PRUEBA" in prompts[1] and "LEC-PRUEBA" in prompts[1]
    assert "herramientas no permitidas" in prompts[1]  # el glosario no es del Gestor


@pytest.mark.asyncio
async def test_change_manager_decides_to_consult_the_technical_advisor(monkeypatch):
    import json

    from agentes.equipo.gestor_cambios import gestor_cambios_service as change_manager

    consulted = []

    async def advisor(pregunta, contexto):
        consulted.append((pregunta, contexto))
        return {"affected_modules": [], "uncertainties": ["El cálculo de prima podría verse afectado."]}

    prompts, queue = [], [
        json.dumps({"consultas": [{"herramienta": "buscar_hu_similares", "consulta": "saldo"}],
                    "consultar_asesor": True, "pregunta_asesor": "¿Qué módulos toca mostrar movimientos?"}),
        json.dumps(_RECOMMENDATION),
    ]
    monkeypatch.setattr(change_manager, "OpenCodeClient", _fake_opencode(AgentId.CHANGE_MANAGER, queue, prompts))
    manager = change_manager.GestorCambiosService(consultor_asesor=advisor)

    recommendation = await manager.evaluate(
        approved_story_id=APPROVED_ID, change_request="Consultar movimientos del mes",
        repository=_approved_repository(),
    )

    assert recommendation.recommendation == "aclaracion"
    assert consulted and consulted[0][0] == "¿Qué módulos toca mostrar movimientos?"
    assert "consultar_asesor_tecnico" in prompts[1]
    assert "El cálculo de prima podría verse afectado." in prompts[1]
