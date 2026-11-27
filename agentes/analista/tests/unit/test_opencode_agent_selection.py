import pytest
from pydantic import SecretStr

import httpx

from agentes.analista.core.agent_registry import AgentId, get_agent_spec
from agentes.analista.core.opencode_client import OpenCodeClient, OpenCodeClientError, OpenCodeSettings


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_id", list(AgentId))
async def test_client_selects_agent_and_verifies_its_own_prompt(agent_id):
    spec = get_agent_spec(agent_id)
    requests = []

    def respond(request):
        requests.append(request)
        if request.url.path == "/api/agent":
            return httpx.Response(200, json={"data": [{
                "id": agent_id.value,
                "system": spec.prompt.text,
                "permission": [{"action": "*", "resource": "*", "effect": "deny"}],
            }]})
        if request.url.path == "/api/session":
            return httpx.Response(200, json={"data": {
                "id": "session-test",
                "permissions": [{"action": "*", "resource": "*", "effect": "deny"}],
            }})
        return httpx.Response(404)

    transport = httpx.MockTransport(respond)
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(
            OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")),
            client=http,
            agent_id=agent_id,
        )
        agent = await client.verify_agent()
        session = await client.create_session(title="isolated-test", model={"providerID": "p", "id": "m"})

    assert agent["id"] == agent_id.value
    assert session["id"] == "session-test"
    create_body = next(request for request in requests if request.url.path == "/api/session").read()
    assert f'"agent":"{agent_id.value}"'.encode() in create_body
    assert b'"effect":"deny"' in create_body


def test_client_rejects_unknown_agent_instead_of_falling_back():
    with pytest.raises(OpenCodeClientError) as raised:
        OpenCodeClient(
            OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")),
            agent_id="unknown-agent",
        )
    assert raised.value.code == "OPENCODE_INCOMPATIBLE"


@pytest.mark.asyncio
async def test_client_rejects_selecting_a_different_agent_for_a_session():
    transport = httpx.MockTransport(lambda _request: httpx.Response(500))
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(
            OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")),
            client=http,
            agent_id=AgentId.TECHNICAL_ADVISOR,
        )
        with pytest.raises(OpenCodeClientError) as raised:
            await client.create_session(title="wrong-role", agent_id=AgentId.ANALYST)
    assert raised.value.code == "OPENCODE_INCOMPATIBLE"
