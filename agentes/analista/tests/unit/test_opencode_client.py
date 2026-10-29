import asyncio

import httpx
import pytest
from datetime import UTC, datetime, timedelta
from pydantic import SecretStr

from agentes.analista.core.opencode_client import (
    DENY_ALL,
    OpenCodeClient,
    OpenCodeClientError,
    OpenCodeSettings,
    _retry_at_from_headers,
    _retry_at_from_ms,
)
from agentes.analista.core.prompt_loader import load_prompt

ZERO_COST = [{"input": 0, "output": 0, "cache": {"read": 0, "write": 0}}]


@pytest.mark.asyncio
async def test_expired_generation_deadline_is_reported_as_turn_timeout():
    client = OpenCodeClient(OpenCodeSettings(server_password=SecretStr("test-only")))
    deadline = asyncio.get_running_loop().time() - 0.01

    with pytest.raises(OpenCodeClientError) as raised:
        await client.wait_for_assistant("session-test", deadline=deadline)

    assert raised.value.code == "TURN_TIMEOUT"
    assert raised.value.retryable is True


def test_turn_timeout_setting_must_be_positive_and_no_more_than_five_minutes():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        OpenCodeSettings(turn_timeout_seconds=0)
    with pytest.raises(ValidationError):
        OpenCodeSettings(turn_timeout_seconds=301)
    with pytest.raises(ValidationError):
        OpenCodeSettings(turn_timeout_seconds=60, conversation_ttl_seconds=60)
    with pytest.raises(ValidationError):
        OpenCodeSettings(max_conversations=33)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "OPENCODE_AUTH_FAILED"),
        (403, "OPENCODE_AUTH_FAILED"),
        (404, "OPENCODE_INCOMPATIBLE"),
        (429, "OPENCODE_RATE_LIMITED"),
        (504, "TURN_TIMEOUT"),
        (503, "OPENCODE_UNAVAILABLE"),
    ],
)
async def test_http_failures_map_to_safe_architecture_errors(status, code):
    transport = httpx.MockTransport(lambda _request: httpx.Response(status))
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(OpenCodeSettings(server_password=SecretStr("test-only")), client=http)
        with pytest.raises(OpenCodeClientError) as raised:
            await client._request("GET", "/api/model")

    assert raised.value.code == code
    assert raised.value.status == status
    assert raised.value.retryable is (status in {429, 503, 504})


@pytest.mark.asyncio
async def test_structured_retry_after_ms_on_provider_quota_is_normalized():
    completed_at = datetime.now(UTC)
    response = httpx.Response(200, json={"data": [{
        "type": "assistant",
        "finish": "error",
        "error": {"type": "provider.quota", "status": 429, "retryAfterMs": 2500},
        "time": {"completed": int(completed_at.timestamp() * 1000)},
        "content": [],
    }]})
    transport = httpx.MockTransport(lambda _request: response)
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")), client=http)
        with pytest.raises(OpenCodeClientError) as raised:
            await client.wait_for_assistant("session-test", deadline=asyncio.get_running_loop().time() + 5)

    assert raised.value.code == "OPENCODE_RATE_LIMITED"
    assert raised.value.retry_at == completed_at.replace(microsecond=completed_at.microsecond // 1000 * 1000) + timedelta(milliseconds=2500)


@pytest.mark.asyncio
async def test_free_limit_retry_after_ms_without_status_uses_message_completion_time():
    completed_at = datetime.now(UTC)
    response = httpx.Response(200, json={"data": [{
        "type": "assistant",
        "finish": "error",
        "error": {"type": "provider.free-limit", "retryAfterMs": 60_000},
        "time": {"completed": int(completed_at.timestamp() * 1000)},
        "content": [],
    }]})
    transport = httpx.MockTransport(lambda _request: response)
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")), client=http)
        with pytest.raises(OpenCodeClientError) as raised:
            await client.wait_for_assistant("session-test", deadline=asyncio.get_running_loop().time() + 5)

    assert raised.value.code == "OPENCODE_RATE_LIMITED"
    assert raised.value.retry_at == completed_at.replace(microsecond=completed_at.microsecond // 1000 * 1000) + timedelta(minutes=1)


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["2.0.27", "2.1.2"])
async def test_server_info_accepts_only_compatibility_verified_versions(version):
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"version": version}))
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")), client=http)
        assert (await client.server_info())["version"] == version


@pytest.mark.asyncio
async def test_server_info_rejects_unverified_versions():
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"version": "2.1.3"}))
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")), client=http)
        with pytest.raises(OpenCodeClientError) as raised:
            await client.server_info()

    assert raised.value.code == "OPENCODE_INCOMPATIBLE"


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["2.0.27", "2.1.2"])
async def test_compatible_server_versions_authenticate_and_verify_analista_configuration(version, monkeypatch):
    prompt = load_prompt()
    requested_paths = []

    def respond(request):
        requested_paths.append(request.url.path)
        assert request.headers.get("authorization", "").startswith("Basic ")
        if request.url.path == "/api/info":
            return httpx.Response(200, json={"version": version})
        if request.url.path == "/api/agent":
            return httpx.Response(200, json={"data": [{
                "id": "analista",
                "system": prompt.text,
                "permission": DENY_ALL,
            }]})
        return httpx.Response(404)

    transport = httpx.MockTransport(respond)
    async_client_type = httpx.AsyncClient

    def async_client_factory(**kwargs):
        assert kwargs["auth"] == ("opencode", "test-only")
        return async_client_type(transport=transport, **kwargs)

    monkeypatch.setattr("agentes.analista.core.opencode_client.httpx.AsyncClient", async_client_factory)
    settings = OpenCodeSettings(
        _env_file=None,
        server_url="http://opencode.test",
        server_username="opencode",
        server_password=SecretStr("test-only"),
    )
    async with OpenCodeClient(settings, prompt=prompt) as client:
        info = await client.server_info()
        agent = await client.verify_agent("analista")

    assert info["version"] == version
    assert agent["id"] == "analista"
    assert requested_paths == ["/api/info", "/api/agent"]


@pytest.mark.asyncio
@pytest.mark.parametrize("retry_after_ms", [-100, "1000", None])
async def test_invalid_structured_retry_after_ms_is_omitted(retry_after_ms):
    response = httpx.Response(200, json={"data": [{
        "type": "assistant",
        "finish": "error",
        "error": {"type": "provider.quota", "retryAfterMs": retry_after_ms},
        "time": {"completed": 1},
        "content": [],
    }]})
    transport = httpx.MockTransport(lambda _request: response)
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")), client=http)
        with pytest.raises(OpenCodeClientError) as raised:
            await client.wait_for_assistant("session-test", deadline=asyncio.get_running_loop().time() + 5)

    assert raised.value.code == "OPENCODE_RATE_LIMITED"
    assert raised.value.retry_at is None


@pytest.mark.asyncio
async def test_direct_http_429_normalizes_retry_after_without_exposing_header():
    transport = httpx.MockTransport(lambda _request: httpx.Response(429, headers={"Retry-After": "2"}))
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")), client=http)
        started = datetime.now(UTC)
        with pytest.raises(OpenCodeClientError) as raised:
            await client._request("GET", "/api/model")

    assert raised.value.code == "OPENCODE_RATE_LIMITED"
    assert raised.value.retry_at is not None
    assert started + timedelta(seconds=1) < raised.value.retry_at <= datetime.now(UTC) + timedelta(seconds=2)
    assert "Retry-After" not in str(raised.value)


def test_retry_after_header_accepts_seconds_and_http_dates_and_rejects_expired_values():
    now = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)

    assert _retry_at_from_headers({"retry-after": "60"}, now=now) == now + timedelta(seconds=60)
    assert _retry_at_from_headers(
        {"retry-after": "Tue, 27 Oct 2026 12:01:00 GMT"}, now=now
    ) == now + timedelta(minutes=1)
    assert _retry_at_from_headers({"retry-after": "0"}, now=now) == now
    assert _retry_at_from_headers({"retry-after-ms": "0"}, now=now) == now
    assert _retry_at_from_headers({"retry-after": "Tue, 27 Oct 2026 11:59:59 GMT"}, now=now) is None
    assert _retry_at_from_headers({"retry-after": "not a date"}, now=now) is None
    assert _retry_at_from_headers({}, now=now) is None


@pytest.mark.parametrize("value", [None, -1, True, "1000", 10**100])
def test_retry_after_ms_rejects_missing_invalid_negative_or_overflow_values(value):
    now = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
    assert _retry_at_from_ms(value, now=now) is None


def test_retry_after_ms_converts_valid_duration_to_utc_instant():
    now = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
    assert _retry_at_from_ms(2500, now=now) == now + timedelta(milliseconds=2500)


def test_zero_retry_after_ms_means_recovery_is_available_now():
    now = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
    assert _retry_at_from_ms(0, now=now) == now


@pytest.mark.asyncio
async def test_opencode_provider_with_explicitly_free_model_is_selected():
    def respond(request):
        assert request.url.path == "/api/model"
        return httpx.Response(200, json={"data": [
            {"providerID": "other-provider", "modelID": "other-model", "enabled": True},
            {"providerID": "opencode", "modelID": "selected-model", "enabled": True, "cost": ZERO_COST},
        ]})

    transport = httpx.MockTransport(respond)
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(
            OpenCodeSettings(
                server_password=SecretStr("test-only"),
                opencode_provider_id="opencode",
                opencode_model_id="selected-model",
            ),
            client=http,
        )
        selected = await client.select_model()

    assert selected == {"providerID": "opencode", "id": "selected-model"}


@pytest.mark.asyncio
async def test_opencode_go_glm_flash_is_selected_with_explicit_paid_model_configuration():
    def respond(request):
        assert request.url.path == "/api/model"
        return httpx.Response(200, json={"data": [
            {
                "providerID": "opencode-go",
                "modelID": "glm-5.3-flash",
                "enabled": True,
                "cost": [{"input": 0.2, "output": 0.8, "cache": {"read": 0.1, "write": 0.2}}],
            },
        ]})

    transport = httpx.MockTransport(respond)
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(
            OpenCodeSettings(
                _env_file=None,
                server_password=SecretStr("test-only"),
                opencode_provider_id="opencode-go",
                opencode_model_id="glm-5.3-flash",
            ),
            client=http,
        )
        selected = await client.select_model()

    assert selected == {"providerID": "opencode-go", "id": "glm-5.3-flash"}


@pytest.mark.asyncio
async def test_missing_configured_model_fails_without_provider_fallback():
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"data": [
        {"providerID": "opencode", "modelID": "other-model", "enabled": True, "cost": ZERO_COST},
        {"providerID": "other-provider", "modelID": "other-model", "enabled": True},
    ]}))
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(
            OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only"), opencode_model_id="missing-model"),
            client=http,
        )
        with pytest.raises(OpenCodeClientError) as raised:
            await client.select_model()

    assert raised.value.code == "MODEL_UNAVAILABLE"
    assert raised.value.retryable is False
    assert str(raised.value) == "OpenCode no anuncia el modelo 'opencode/missing-model'."


@pytest.mark.asyncio
async def test_provider_not_announced_by_opencode_is_rejected_with_reason():
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"data": [
        {"providerID": "opencode", "modelID": "other-model", "enabled": True, "cost": ZERO_COST},
    ]}))
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(
            OpenCodeSettings(
                _env_file=None,
                server_password=SecretStr("test-only"),
                opencode_provider_id="unknown-provider",
                opencode_model_id="some-model",
            ),
            client=http,
        )
        with pytest.raises(OpenCodeClientError) as raised:
            await client.select_model()

    assert raised.value.code == "MODEL_UNAVAILABLE"
    assert str(raised.value) == "OpenCode no anuncia el provider 'unknown-provider'."


@pytest.mark.asyncio
async def test_default_model_is_used_only_when_open_code_owns_it():
    def respond(request):
        if request.url.path == "/api/model/default":
            return httpx.Response(200, json={"data": {"providerID": "opencode", "modelID": "default-model"}})
        return httpx.Response(200, json={"data": [
            {"providerID": "opencode", "modelID": "default-model", "enabled": True, "cost": ZERO_COST},
        ]})

    transport = httpx.MockTransport(respond)
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")), client=http)
        selected = await client.select_model()

    assert selected == {"providerID": "opencode", "id": "default-model"}


@pytest.mark.asyncio
async def test_default_model_from_another_provider_is_rejected():
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={
        "data": {"providerID": "other-provider", "modelID": "other-model"},
    }))
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")), client=http)
        with pytest.raises(OpenCodeClientError) as raised:
            await client.select_model()

    assert raised.value.code == "MODEL_UNAVAILABLE"


@pytest.mark.asyncio
async def test_disabled_model_is_rejected():
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"data": [
        {"providerID": "opencode", "modelID": "selected-model", "enabled": False, "cost": ZERO_COST},
    ]}))
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(
            OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only"), opencode_model_id="selected-model"),
            client=http,
        )
        with pytest.raises(OpenCodeClientError) as raised:
            await client.select_model()

    assert raised.value.code == "MODEL_UNAVAILABLE"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cost",
    [
        [{"input": 0.1, "output": 0, "cache": {"read": 0, "write": 0}}],
        [{"input": 0, "output": 0, "cache": {"read": 0, "write": 0}}, {"input": 0, "output": 1, "cache": {"read": 0, "write": 0}}],
        None,
    ],
)
async def test_paid_or_unpriced_model_is_rejected_without_generation(cost):
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"data": [
        {"providerID": "opencode", "modelID": "selected-model", "enabled": True, "cost": cost},
    ]}))
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(
            OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only"), opencode_model_id="selected-model"),
            client=http,
        )
        with pytest.raises(OpenCodeClientError) as raised:
            await client.select_model()

    assert raised.value.code == "MODEL_UNAVAILABLE"


@pytest.mark.asyncio
async def test_non_opencode_agent_model_is_rejected():
    client = OpenCodeClient(OpenCodeSettings(_env_file=None, server_password=SecretStr("test-only")))

    with pytest.raises(OpenCodeClientError) as raised:
        await client.select_model({"model": {"providerID": "other-provider", "modelID": "other-model"}})

    assert raised.value.code == "MODEL_UNAVAILABLE"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_error", "code"),
    [
        ({"type": "provider.quota", "status": 429}, "OPENCODE_RATE_LIMITED"),
        ({"type": "provider.auth", "status": 401}, "OPENCODE_AUTH_FAILED"),
        ({"type": "provider.timeout", "status": 504}, "TURN_TIMEOUT"),
        ({"type": "provider.model_not_found"}, "MODEL_UNAVAILABLE"),
    ],
)
async def test_completed_provider_errors_are_classified(provider_error, code):
    response = httpx.Response(200, json={"data": [{
        "type": "assistant",
        "finish": "error",
        "error": provider_error,
        "time": {"completed": 1},
        "content": [],
    }]})
    transport = httpx.MockTransport(lambda _request: response)
    async with httpx.AsyncClient(base_url="http://opencode.test", transport=transport) as http:
        client = OpenCodeClient(OpenCodeSettings(server_password=SecretStr("test-only")), client=http)
        with pytest.raises(OpenCodeClientError) as raised:
            await client.wait_for_assistant("session-test", deadline=asyncio.get_running_loop().time() + 5)

    assert raised.value.code == code
    if code == "OPENCODE_RATE_LIMITED":
        assert raised.value.retry_at is None

