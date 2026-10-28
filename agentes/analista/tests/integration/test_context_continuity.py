import json
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from agentes.analista.core import orchestrator
from agentes.analista.core.conversation_store import ConversationStore
from agentes.analista.core.models import SendMessageRequest


def _output(*, known, missing, questions):
    return json.dumps({
        "respuesta_markdown": "The requirement analysis was updated.",
        "analisis": {"conocida": known, "faltante": missing, "supuesta": [], "ambigua": []},
        "preguntas": questions,
        "listo_para_redactor": not missing and not any(q["estado"] == "pendiente" for q in questions),
    })


@pytest.mark.asyncio
async def test_multi_turn_state_and_questions_continue_without_crossing_conversations(monkeypatch):
    outputs = [
        _output(
            known=["The portal accepts policy requests."],
            missing=["Delivery deadline"],
            questions=[
                {"categoria": "Datos requeridos", "pregunta": "What is the delivery deadline?", "estado": "pendiente"},
                {"categoria": "Reglas de negocio", "pregunta": "Which support channel is used?", "estado": "pendiente"},
            ],
        ),
        _output(
            known=["The portal accepts policy requests.", "Delivery deadline is 14 days."],
            missing=[],
            questions=[
                {"categoria": "Datos requeridos", "pregunta": "What is the delivery deadline?", "estado": "respondida"},
            ],
        ),
        _output(
            known=["The portal accepts policy requests.", "Delivery deadline is 14 days."],
            missing=[],
            questions=[
                {"categoria": "Datos requeridos", "pregunta": "What is the delivery deadline?", "estado": "pendiente"},
            ],
        ),
    ]
    prompts = []

    async def isolated_tools(_query, _trace=None):
        return [], [], []

    class IsolatedOpenCodeClient:
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
            return {"providerID": "opencode", "id": "isolated-test-double"}

        @asynccontextmanager
        async def session(self, *, title, model):
            assert model["providerID"] == "opencode"
            yield {"id": "isolated-session"}

        async def submit_prompt(self, _session_id, prompt):
            prompts.append(prompt)
            return {"time": {"created": len(prompts)}}

        async def wait_for_assistant(self, _session_id, *, deadline, after=None):
            return {"text": outputs.pop(0), "finish": "stop"}

    monkeypatch.setattr(orchestrator, "_execute_tools", isolated_tools)
    monkeypatch.setattr(orchestrator, "OpenCodeClient", IsolatedOpenCodeClient)
    store = ConversationStore(prompt_version="1.0.0", prompt_hash="a" * 64)
    conversation = await store.create()

    first = await orchestrator.run_turn(
        store, conversation.conversation_id,
        SendMessageRequest(request_id=uuid4(), message="Analyze the policy portal request"),
    )
    second = await orchestrator.run_turn(
        store, conversation.conversation_id,
        SendMessageRequest(request_id=uuid4(), message="The deadline is 14 days"),
    )
    third = await orchestrator.run_turn(
        store, conversation.conversation_id,
        SendMessageRequest(request_id=uuid4(), message="Continue the analysis"),
    )

    assert first.analisis.faltante == ["Delivery deadline"]
    assert second.analisis.faltante == []
    assert "Delivery deadline is 14 days." in second.analisis.conocida
    first_question = first.preguntas[0]
    assert second.preguntas[0].question_id == first_question.question_id
    assert second.preguntas[0].estado.value == "respondida"
    assert third.preguntas[0].estado.value == "respondida"
    assert third.preguntas[0].question_id == first_question.question_id
    assert third.preguntas[0].updated_turn_id == third.turn_id
    assert any(q.pregunta == "Which support channel is used?" and q.estado.value == "pendiente" for q in third.preguntas)
    assert "Analyze the policy portal request" in prompts[1]
    assert "The deadline is 14 days" in prompts[2]
    assert len((await store.get(conversation.conversation_id)).context_turns) == 3

    fresh = await store.create()
    fresh_record = await store.get(fresh.conversation_id)
    assert fresh_record.context_turns == []
    assert fresh_record.previous_summary == ""
    assert fresh_record.questions == []
