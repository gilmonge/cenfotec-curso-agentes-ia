from __future__ import annotations

from types import SimpleNamespace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from agentes.analista.api import errors
from agentes.analista.api.routes import conversations, health
from agentes.analista.core.conversation_store import ConversationStore
from agentes.analista.core.models import AgentTurnResponse, ErrorCode
from agentes.analista.core.orchestrator import OrchestrationError
from agentes.analista.core.observability import Observability
from agentes.analista.core.prompt_loader import load_prompt


def make_app() -> FastAPI:
    app = FastAPI()
    errors.install_error_handlers(app)
    app.include_router(health.router, prefix="/api/analista")
    app.include_router(conversations.router, prefix="/api/analista")
    prompt = load_prompt()
    app.state.prompt_snapshot = prompt
    app.state.restart_required = False
    app.state.settings = SimpleNamespace(
        request_timeout_seconds=90, turn_timeout_seconds=75, message_limit=4000
    )
    app.state.observability = Observability()
    app.state.store = ConversationStore(prompt_version=prompt.version, prompt_hash=prompt.sha256)
    return app


@pytest_asyncio.fixture
async def api_client():
    app = make_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, app


@pytest.mark.asyncio
async def test_conversation_create_validate_reset_and_delete(api_client):
    client, _app = api_client
    created = await client.post("/api/analista/conversaciones")
    assert created.status_code == 201
    conversation_id = created.json()["conversation_id"]
    assert created.json()["timeout_seconds"] == 75

    invalid = await client.post(
        f"/api/analista/conversaciones/{conversation_id}/mensajes",
        json={"request_id": str(uuid4()), "message": "x" * 4001},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_REQUEST"

    reset = await client.post(f"/api/analista/conversaciones/{conversation_id}/reiniciar")
    assert reset.status_code == 200
    assert reset.json()["timeout_seconds"] == 75
    replacement_id = reset.json()["conversation_id"]
    assert replacement_id != conversation_id
    assert reset.json()["replaced_conversation_id"] == conversation_id

    deleted = await client.delete(f"/api/analista/conversaciones/{replacement_id}")
    assert deleted.status_code == 204
    assert (await client.delete(f"/api/analista/conversaciones/{replacement_id}")).status_code == 204


@pytest.mark.asyncio
async def test_message_route_returns_contract_response_without_live_generation(api_client, monkeypatch):
    client, _app = api_client
    conversation = (await client.post("/api/analista/conversaciones")).json()
    request_id = str(uuid4())

    async def isolated_turn(_store, conversation_id, request, *, observability=None):
        return AgentTurnResponse(
            conversation_id=conversation_id,
            request_id=request.request_id,
            turn_id=uuid4(),
            estado="completado",
            respuesta_markdown="Prueba unitaria aislada.",
            analisis={"conocida": [], "faltante": ["Plazo"], "supuesta": [], "ambigua": []},
            preguntas=[],
            fuentes_consultadas=[],
            listo_para_redactor=False,
            limitaciones=[],
            duracion_ms=1,
            prompt_version="1.0.0",
        )

    monkeypatch.setattr(conversations, "run_turn", isolated_turn)
    response = await client.post(
        f"/api/analista/conversaciones/{conversation['conversation_id']}/mensajes",
        json={"request_id": request_id, "message": "Analizar solicitud"},
    )

    assert response.status_code == 200
    assert response.json()["respuesta_markdown"] == "Prueba unitaria aislada."
    assert response.json()["request_id"] == request_id


@pytest.mark.asyncio
async def test_quota_recovery_instant_is_propagated_in_public_error_envelope(api_client, monkeypatch):
    client, _app = api_client
    conversation = (await client.post("/api/analista/conversaciones")).json()
    retry_at = datetime.now(UTC) + timedelta(minutes=8)

    async def quota_error(*_args, **_kwargs):
        raise OrchestrationError(
            ErrorCode.OPENCODE_RATE_LIMITED,
            "OpenCode agotó la cuota disponible del proveedor.",
            retryable=True,
            retry_at=retry_at,
        )

    monkeypatch.setattr(conversations, "run_turn", quota_error)
    response = await client.post(
        f"/api/analista/conversaciones/{conversation['conversation_id']}/mensajes",
        json={"request_id": str(uuid4()), "message": "Consulta aislada"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "OPENCODE_RATE_LIMITED"
    assert response.json()["error"]["retryable"] is True
    assert datetime.fromisoformat(response.json()["error"]["retry_at"]) == retry_at


@pytest.mark.asyncio
async def test_prompt_change_requires_backend_restart_before_a_turn(api_client, monkeypatch):
    client, app = api_client
    created = await client.post("/api/analista/conversaciones")
    conversation_id = created.json()["conversation_id"]
    changed_prompt = SimpleNamespace(
        text="changed prompt", version="1.0.0", sha256="b" * 64, path=app.state.prompt_snapshot.path
    )
    monkeypatch.setattr(conversations, "load_prompt", lambda: changed_prompt)

    response = await client.post(
        f"/api/analista/conversaciones/{conversation_id}/mensajes",
        json={"request_id": str(uuid4()), "message": "No generation should run"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROMPT_RESTART_REQUIRED"
    assert app.state.restart_required is True


@pytest.mark.asyncio
async def test_cancel_route_invalidates_active_turn_and_stops_its_session(api_client, monkeypatch):
    client, app = api_client
    conversation = (await client.post("/api/analista/conversaciones")).json()
    conversation_id = conversation["conversation_id"]
    request_id = uuid4()
    start = await app.state.store.begin_turn(uuid4_from(conversation_id), request_id, "cancelar")
    await app.state.store.set_opencode_session(
        uuid4_from(conversation_id), start.turn.turn_id, start.generation, "opaque-session-id"
    )
    stopped: list[str | None] = []

    async def stop_session(session_id):
        stopped.append(session_id)

    monkeypatch.setattr(conversations, "_stop_session", stop_session)
    result = await client.post(
        f"/api/analista/conversaciones/{conversation_id}/cancelar",
        json={"request_id": str(request_id)},
    )

    current = await app.state.store.get(uuid4_from(conversation_id))
    assert result.status_code == 200
    assert result.json()["canceled"] is True
    assert stopped == ["opaque-session-id"]
    assert current.active_turn_id is None
    assert current.context_turns == []


def uuid4_from(value: str):
    from uuid import UUID

    return UUID(value)


@pytest.mark.parametrize("version", ["2.0.27", "2.1.2"])
@pytest.mark.asyncio
async def test_health_reports_degraded_without_langfuse_and_checks_contracts(api_client, monkeypatch, version):
    client, _app = api_client

    class FakeOpenCode:
        def __init__(self, *, settings=None, prompt=None):
            self.prompt = prompt

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def server_info(self):
            return {"version": version}

        async def verify_agent(self, _agent):
            return {"id": "analista"}

        async def select_model(self, _agent):
            return {"providerID": "opencode-go", "id": "glm-5.3-flash"}

    class FakeAdapter:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def list_tools(self):
            return [SimpleNamespace(name=name) for name in health.EXPECTED_TOOLS]

    monkeypatch.setattr(health, "OpenCodeClient", FakeOpenCode)
    monkeypatch.setattr(health, "MCPAdapter", lambda _server: FakeAdapter())
    response = await client.get("/api/analista/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["timeout_seconds"] == 75
    assert body["checks"]["opencode"]["version"] == version
    assert body["checks"]["opencode"]["configured_provider_id"] == "opencode"
    assert body["checks"]["opencode"]["configured_model_id"] is None
    assert body["checks"]["opencode"]["selected_provider_id"] == "opencode-go"
    assert body["checks"]["opencode"]["selected_model_id"] == "glm-5.3-flash"
    assert body["checks"]["opencode"]["rejection_reason"] is None
    assert body["checks"]["mcp"]["status"] == "ok"
    assert body["checks"]["langfuse"]["status"] == "disabled"


@pytest.mark.asyncio
async def test_health_degrades_for_unsupported_opencode_version(api_client, monkeypatch):
    client, _app = api_client

    class FakeOpenCode:
        def __init__(self, *, settings=None, prompt=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def server_info(self):
            return {"version": "2.1.3"}

        async def verify_agent(self, _agent):
            pytest.fail("No debe verificar el agente en una versión incompatible")

    class FakeAdapter:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def list_tools(self):
            return [SimpleNamespace(name=name) for name in health.EXPECTED_TOOLS]

    monkeypatch.setattr(health, "OpenCodeClient", FakeOpenCode)
    monkeypatch.setattr(health, "MCPAdapter", lambda _server: FakeAdapter())
    response = await client.get("/api/analista/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"]["opencode"]["status"] == "unavailable"
    assert body["checks"]["opencode"]["version"] == "2.1.3"
    assert body["checks"]["opencode"]["agent"] is None
    assert body["checks"]["opencode"]["rejection_code"] == "OPENCODE_INCOMPATIBLE"
    assert body["checks"]["opencode"]["rejection_reason"] == "La versión de OpenCode no es compatible."
    assert body["checks"]["mcp"]["status"] == "ok"


@pytest.mark.asyncio
async def test_health_exposes_configured_model_and_exact_selection_rejection(api_client, monkeypatch):
    client, app = api_client
    app.state.settings.opencode_provider_id = "opencode-go"
    app.state.settings.opencode_model_id = "glm-5.3-flash"

    class FakeOpenCode:
        def __init__(self, *, settings=None, prompt=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def server_info(self):
            return {"version": "2.1.2"}

        async def verify_agent(self, _agent):
            return {"id": "analista"}

        async def select_model(self, _agent):
            raise health.OpenCodeClientError(
                "MODEL_UNAVAILABLE",
                "OpenCode no anuncia el modelo 'opencode-go/glm-5.3-flash'.",
            )

    class FakeAdapter:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def list_tools(self):
            return [SimpleNamespace(name=name) for name in health.EXPECTED_TOOLS]

    monkeypatch.setattr(health, "OpenCodeClient", FakeOpenCode)
    monkeypatch.setattr(health, "MCPAdapter", lambda _server: FakeAdapter())
    response = await client.get("/api/analista/health")

    assert response.status_code == 200
    check = response.json()["checks"]["opencode"]
    assert check["version"] == "2.1.2"
    assert check["agent"] == "analista"
    assert check["configured_provider_id"] == "opencode-go"
    assert check["configured_model_id"] == "glm-5.3-flash"
    assert check["selected_provider_id"] is None
    assert check["selected_model_id"] is None
    assert check["rejection_code"] == "MODEL_UNAVAILABLE"
    assert check["rejection_reason"] == "OpenCode no anuncia el modelo 'opencode-go/glm-5.3-flash'."
    assert "password" not in response.text.lower()
