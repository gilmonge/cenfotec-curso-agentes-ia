from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from agentes.analista.core import ejecutor_mcp
from agentes.equipo.analista import analista_service as orchestrator
from agentes.analista.core.agent_registry import AgentId, allowed_mcp_tools
from agentes.analista.core.ciclo_agente import PasoCiclo, ResultadoCiclo
from agentes.analista.core.ejecutor_mcp import ResultadoHerramienta
from agentes.analista.core.context_builder import render_user_prompt
from agentes.analista.core.conversation_store import ConversationStore
from agentes.analista.core.models import (
    ContextPayload, Question, QuestionCategory, QuestionState, SendMessageRequest,
    ToolExecution, ToolName, ToolStatus,
)
from agentes.analista.core.output_parser import AgentOutput, AgentQuestionOutput


_RESULTS = {
    "consultar_glosario": {
        "definiciones": [], "total": 0, "origen": "simulado", "contenido_no_confiable": True,
    },
    "buscar_hu_similares": {
        "historias": [], "total": 0, "origen": "anonimizado", "contenido_no_confiable": True,
    },
    "consultar_estandares": {
        "estandares": [], "total": 0, "origen": "simulado", "contenido_no_confiable": True,
    },
    "aplicar_checklist_vacios": {
        "categorias": [], "total": 0, "origen": "simulado", "contenido_no_confiable": True,
    },
}


class _Tool:
    def __init__(self, name: str) -> None:
        self.name = name
        self.description = f"herramienta {name}"
        self.args = {"consulta": {}, "limite": {}}

    async def ainvoke(self, _arguments):
        await asyncio.sleep(0)
        return _RESULTS.get(self.name, {"total": 0})


class _Adapter:
    def __init__(self, names):
        self._names = names

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def list_tools(self):
        return [_Tool(name) for name in sorted(self._names)]


@pytest.mark.asyncio
async def test_mcp_session_invokes_allowed_tools_and_normalizes_results(monkeypatch):
    monkeypatch.setattr(ejecutor_mcp, "MCPAdapter", lambda _server: _Adapter(allowed_mcp_tools(AgentId.ANALYST)))

    async with ejecutor_mcp.SesionMCP(AgentId.ANALYST, servidor="fake") as sesion:
        assert {item.nombre for item in sesion.catalogo()} == {tool.value for tool in ToolName}
        results = await asyncio.gather(*(sesion.invocar(tool.value, "requerimiento de prueba") for tool in ToolName))

    assert all(item.estado == "ok" for item in results)
    executions = orchestrator._ejecuciones(results)
    assert {item.tool_name for item in executions} == set(ToolName)
    assert all(item.status == ToolStatus.OK for item in executions)


@pytest.mark.asyncio
async def test_mcp_session_rejects_a_server_exposing_tools_outside_the_allowlist(monkeypatch):
    names = {*allowed_mcp_tools(AgentId.ANALYST), "read_file"}
    monkeypatch.setattr(ejecutor_mcp, "MCPAdapter", lambda _server: _Adapter(names))

    with pytest.raises(ejecutor_mcp.MCPNoDisponibleError):
        async with ejecutor_mcp.SesionMCP(AgentId.ANALYST, servidor="fake"):
            pass


@pytest.mark.asyncio
async def test_mcp_session_applies_the_selected_role_allowlist(monkeypatch):
    advisor_tools = allowed_mcp_tools(AgentId.TECHNICAL_ADVISOR)
    monkeypatch.setattr(ejecutor_mcp, "MCPAdapter", lambda _server: _Adapter(advisor_tools))

    async with ejecutor_mcp.SesionMCP(AgentId.TECHNICAL_ADVISOR, servidor="fake") as sesion:
        rejected = await sesion.invocar("consultar_glosario", "término")
        allowed = await sesion.invocar("consultar_estandares", "término")

    assert rejected.estado == "rechazada"
    assert allowed.estado == "ok"


def test_render_user_prompt_includes_schema_without_vendor_specific_directives():
    payload = ContextPayload(
        current_state={}, recent_turns=[], current_message="consulta", tool_results=[], limitations=[]
    )

    rendered = render_user_prompt(payload, "schema de salida")

    assert "schema de salida" in rendered
    assert "/no_think" not in rendered
    assert "máximo 3 elementos" in rendered


@pytest.mark.asyncio
async def test_run_turn_composes_context_parser_and_opencode_adapter_in_isolation(monkeypatch):
    observed_prompt = []
    assistant_texts = []

    async def isolated_tools(**_kwargs):
        return ResultadoCiclo(
            paso=[PasoCiclo(ronda=1, origen="modelo", razonamiento="Hay un término de seguros por confirmar.",
                            consulta=[{"herramienta": "consultar_glosario", "consulta": "plazo"}])],
            resultado=[ResultadoHerramienta(
                "consultar_glosario", "plazo", "ok", datos=_RESULTS["consultar_glosario"], cantidad=0,
            )],
        )

    class IsolatedOpenCodeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def set_deadline(self, _deadline):
            pass

        async def server_info(self):
            return {"version": "2.0.27"}

        async def verify_agent(self, _agent):
            return {"id": "analista"}

        async def select_model(self, _agent):
            return {"providerID": "opencode", "id": "unit-test-model"}

        @asynccontextmanager
        async def session(self, *, title, model):
            assert model["providerID"] == "opencode"
            yield {"id": "isolated-session"}

        async def submit_prompt(self, _session_id, prompt):
            observed_prompt.append(prompt)
            return {"time": {"created": 1}}

        async def wait_for_assistant(self, _session_id, *, deadline, after=None):
            return {"text": assistant_texts.pop(0), "finish": "stop"}

    monkeypatch.setattr(orchestrator, "_ejecutar_ciclo", isolated_tools)
    monkeypatch.setattr(orchestrator, "OpenCodeClient", IsolatedOpenCodeClient)
    store = ConversationStore(prompt_version="1.0.0", prompt_hash="a" * 64)
    conversation = await store.create()
    request = SendMessageRequest(request_id=uuid4(), message="Analizar requerimiento")
    valid_output = json.dumps({
        "respuesta_markdown": "Plazo por confirmar.",
        "analisis": {"conocida": ["Hay una solicitud"], "faltante": ["Plazo"], "supuesta": [], "ambigua": []},
        "preguntas": [],
        "listo_para_redactor": False,
    })
    assistant_texts.append(valid_output)

    response = await orchestrator.run_turn(store, conversation.conversation_id, request)

    assert response.respuesta_markdown == "Plazo por confirmar."
    assert response.analisis.faltante == ["Plazo"]
    assert response.listo_para_redactor is False
    assert response.plan_agente[0].razonamiento == "Hay un término de seguros por confirmar."
    assert response.plan_agente[0].consultas[0].herramienta == "consultar_glosario"
    assert [item.nombre for item in response.fuentes_consultadas] == [ToolName.GLOSSARY]
    assert len(observed_prompt) == 1
    assert "unit-test-model" not in observed_prompt[0]
    current = await store.get(conversation.conversation_id)
    assert current.active_turn_id is None
    assert len(current.context_turns) == 1
    assert "Faltante: Plazo" in current.previous_summary

    repaired_conversation = await store.create()
    assistant_texts.extend(["texto que no cumple el schema", valid_output])
    repaired = await orchestrator.run_turn(
        store,
        repaired_conversation.conversation_id,
        SendMessageRequest(request_id=uuid4(), message="Revisar salida inválida"),
    )
    assert repaired.respuesta_markdown == "Plazo por confirmar."
    assert len(observed_prompt) == 3
    assert "La salida anterior no cumpli" in observed_prompt[-1]
    assert "formato requerido" in observed_prompt[-1]


def test_public_sources_include_only_successful_tool_executions():
    from uuid import uuid4

    conversation_id, request_id, turn_id = uuid4(), uuid4(), uuid4()
    output = AgentOutput(
        respuesta_markdown="Se consultó el glosario disponible.",
        analisis={"conocida": [], "faltante": [], "supuesta": [], "ambigua": []},
        preguntas=[],
        listo_para_redactor=True,
    )
    executions = [
        ToolExecution(tool_name=ToolName.GLOSSARY, status=ToolStatus.OK, result_count=2, duration_ms=7),
        ToolExecution(tool_name=ToolName.STANDARDS, status=ToolStatus.ERROR, duration_ms=5, error_code="MCP_TOOL_FAILED"),
    ]

    response = orchestrator._to_response(
        output,
        conversation_id=conversation_id,
        request_id=request_id,
        turn_id=turn_id,
        prior_questions=[],
        tool_executions=executions,
        limitations=["No se pudieron consultar todos los estándares."],
        duration_ms=12,
    )

    assert [item.nombre for item in response.fuentes_consultadas] == [ToolName.GLOSSARY]
    assert response.limitaciones == ["No se pudieron consultar todos los estándares."]


def test_questions_answered_by_business_stay_answered_even_if_the_model_repeats_them_as_pending():
    """Caso real: tras enviar respuestas, el modelo devolvió las mismas preguntas como pendientes."""
    from uuid import uuid4

    turn_id = uuid4()
    prior = [
        Question(question_id="q-vacio", categoria=QuestionCategory.EXPECTED_BEHAVIOR,
                 pregunta="¿Qué pasa si el teléfono queda vacío?", estado=QuestionState.PENDING),
        Question(question_id="q-fecha", categoria=QuestionCategory.BUSINESS_RULES,
                 pregunta="¿Desde cuándo rige?", estado=QuestionState.PENDING),
    ]
    output = AgentOutput(
        respuesta_markdown="Análisis actualizado.",
        analisis={"conocida": ["Teléfono opcional"], "faltante": [], "supuesta": [], "ambigua": []},
        preguntas=[AgentQuestionOutput(categoria=QuestionCategory.EXPECTED_BEHAVIOR,
                                       pregunta="¿Qué pasa si el teléfono queda vacío?", estado=QuestionState.PENDING)],
        listo_para_redactor=False,
    )

    response = orchestrator._to_response(
        output, conversation_id=uuid4(), request_id=uuid4(), turn_id=turn_id, prior_questions=prior,
        tool_executions=[], limitations=[], duration_ms=1, respondidas={"q-vacio"},
    )

    by_id = {item.question_id: item.estado for item in response.preguntas}
    assert by_id["q-vacio"] == QuestionState.ANSWERED      # repetida por el modelo, igual respondida
    assert by_id["q-fecha"] == QuestionState.PENDING       # no se respondió en este turno
    assert response.listo_para_redactor is False
