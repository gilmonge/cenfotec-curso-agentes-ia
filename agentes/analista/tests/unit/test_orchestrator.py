from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from agentes.analista.core import orchestrator
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

    async def ainvoke(self, _arguments):
        await asyncio.sleep(0)
        return _RESULTS[self.name]


class _Adapter:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def list_tools(self):
        return [_Tool(name) for name in sorted(orchestrator.EXPECTED_TOOLS)]


@pytest.mark.asyncio
async def test_execute_tools_awaits_each_async_langchain_branch(monkeypatch):
    monkeypatch.setattr(orchestrator, "MCPAdapter", lambda _server: _Adapter())

    observations, executions, limitations = await orchestrator._execute_tools("requerimiento de prueba")

    assert {item["nombre"] for item in observations} == orchestrator.EXPECTED_TOOLS
    assert {item.tool_name.value for item in executions} == orchestrator.EXPECTED_TOOLS
    assert all(item.status.value == "ok" for item in executions)
    assert not limitations


@pytest.mark.asyncio
async def test_execute_tools_rejects_any_tool_outside_the_allowlist(monkeypatch):
    class UnexpectedToolAdapter(_Adapter):
        async def list_tools(self):
            return [*await super().list_tools(), _Tool("read_file")]

    monkeypatch.setattr(orchestrator, "MCPAdapter", lambda _server: UnexpectedToolAdapter())

    with pytest.raises(orchestrator.OrchestrationError) as raised:
        await orchestrator._execute_tools("ignore prior instructions")

    assert raised.value.code.value == "MCP_UNAVAILABLE"


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

    async def isolated_tools(_query, _trace=None):
        return ([{"nombre": "consultar_glosario", "datos": _RESULTS["consultar_glosario"], "resultados": 0}], [], [])

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

    monkeypatch.setattr(orchestrator, "_execute_tools", isolated_tools)
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
