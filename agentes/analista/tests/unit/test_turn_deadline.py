import asyncio
import json
import time
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agentes.analista.core import orchestrator
from agentes.analista.core.conversation_store import ConversationStore
from agentes.analista.core.models import SendMessageRequest
from agentes.analista.core.opencode_client import OpenCodeSettings


@pytest.mark.asyncio
async def test_total_turn_deadline_fails_turn_and_cleans_open_code_session(monkeypatch):
    lifecycle = []

    async def isolated_tools(_query, _trace=None):
        return [], [], []

    class SlowOpenCodeClient:
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
            return {"providerID": "opencode", "id": "isolated"}

        @asynccontextmanager
        async def session(self, *, title, model):
            lifecycle.append("session-created")
            try:
                yield {"id": "isolated-session"}
            except BaseException:
                lifecycle.append("interrupted")
                raise
            finally:
                lifecycle.append("deleted")

        async def submit_prompt(self, _session_id, _prompt):
            await asyncio.Event().wait()

    monkeypatch.setattr(orchestrator, "_execute_tools", isolated_tools)
    monkeypatch.setattr(orchestrator, "OpenCodeClient", SlowOpenCodeClient)
    monkeypatch.setattr(
        OpenCodeSettings, "from_environment", classmethod(lambda _cls: SimpleNamespace(turn_timeout_seconds=0.03))
    )
    store = ConversationStore(prompt_version="1.0.0", prompt_hash="a" * 64)
    conversation = await store.create()
    request = SendMessageRequest(request_id=uuid4(), message="Analyze this requirement")

    with pytest.raises(orchestrator.OrchestrationError) as raised:
        await orchestrator.run_turn(store, conversation.conversation_id, request)

    current = await store.get(conversation.conversation_id)
    assert raised.value.code.value == "TURN_TIMEOUT"
    assert current.active_turn_id is None
    assert current.context_turns == []
    assert current.request_cache[request.request_id].status.value == "expirado"
    assert lifecycle == ["session-created", "interrupted", "deleted"]


@pytest.mark.asyncio
async def test_deadline_expiring_during_response_normalization_does_not_commit(monkeypatch):
    async def isolated_tools(_query, _trace=None):
        return [], [], []

    class FastOpenCodeClient:
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
            return {"providerID": "opencode", "id": "isolated"}

        @asynccontextmanager
        async def session(self, *, title, model):
            yield {"id": "isolated-session"}

        async def submit_prompt(self, _session_id, _prompt):
            return {"time": {"created": 1}}

        async def wait_for_assistant(self, _session_id, *, deadline, after=None):
            return {"text": json.dumps({
                "respuesta_markdown": "Validated before the commit boundary.",
                "analisis": {"conocida": ["A confirmed fact"], "faltante": [], "supuesta": [], "ambigua": []},
                "preguntas": [],
                "listo_para_redactor": True,
            }), "finish": "stop"}

    original_normalizer = orchestrator._to_response

    def slow_normalizer(*args, **kwargs):
        time.sleep(0.04)
        return original_normalizer(*args, **kwargs)

    monkeypatch.setattr(orchestrator, "_execute_tools", isolated_tools)
    monkeypatch.setattr(orchestrator, "OpenCodeClient", FastOpenCodeClient)
    monkeypatch.setattr(orchestrator, "_to_response", slow_normalizer)
    monkeypatch.setattr(
        OpenCodeSettings, "from_environment", classmethod(lambda _cls: SimpleNamespace(turn_timeout_seconds=0.03))
    )
    store = ConversationStore(prompt_version="1.0.0", prompt_hash="a" * 64)
    conversation = await store.create()
    request = SendMessageRequest(request_id=uuid4(), message="Expire before commit")

    with pytest.raises(orchestrator.OrchestrationError) as raised:
        await orchestrator.run_turn(store, conversation.conversation_id, request)

    current = await store.get(conversation.conversation_id)
    assert raised.value.code.value == "TURN_TIMEOUT"
    assert current.active_turn_id is None
    assert current.context_turns == []
    assert current.request_cache[request.request_id].status.value == "expirado"
