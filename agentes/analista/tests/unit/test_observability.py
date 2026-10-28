from types import SimpleNamespace

from pydantic import SecretStr

from agentes.analista.core.observability import Observability, mask_otel_spans
from agentes.analista.core.opencode_client import OpenCodeSettings


def test_otel_mask_replaces_content_attributes_and_keeps_diagnostics():
    result = mask_otel_spans(params=SimpleNamespace(spans={
        "span-1": SimpleNamespace(attributes={
            "gen_ai.prompt.0.content": "synthetic prompt",
            "langfuse.trace.output": "synthetic response",
            "langfuse.observation.metadata.status": "ok",
        }),
    }))

    assert result.span_patches["span-1"].set_attributes == {
        "gen_ai.prompt.0.content": "[REDACTED]",
        "langfuse.trace.output": "[REDACTED]",
    }


def test_observability_is_disabled_without_credentials():
    observer = Observability.from_settings(OpenCodeSettings(_env_file=None))

    assert observer.enabled is False
    assert observer.health_status == "disabled"
    assert observer.start_turn(conversation_id="c", request_id="r", turn_id="t").span is None


class FakeSpan:
    def __init__(self, *, fail_update=False):
        self.fail_update = fail_update
        self.children = []
        self.updates = []
        self.ended = False

    def start_observation(self, **kwargs):
        self.children.append(kwargs)
        return FakeSpan()

    def update(self, **kwargs):
        if self.fail_update:
            raise RuntimeError("synthetic export failure")
        self.updates.append(kwargs)

    def end(self):
        self.ended = True


class FakeLangfuse:
    def __init__(self, *, fail_update=False, **kwargs):
        self.options = kwargs
        self.span = FakeSpan(fail_update=fail_update)

    def start_observation(self, **kwargs):
        self.root_options = kwargs
        return self.span

    def flush(self):
        pass

    def shutdown(self):
        pass


def test_turn_and_child_spans_include_only_allowlisted_metadata(monkeypatch):
    import agentes.analista.core.observability as module

    client = FakeLangfuse()
    monkeypatch.setattr(module, "Langfuse", lambda **kwargs: client.options.update(kwargs) or client)
    settings = OpenCodeSettings(
        _env_file=None,
        langfuse_public_key=SecretStr("test-public"),
        langfuse_secret_key=SecretStr("test-secret"),
        langfuse_base_url="https://langfuse.invalid",
    )

    observer = Observability.from_settings(settings)
    trace = observer.start_turn(conversation_id="conversation", request_id="request", turn_id="turn")
    operation = trace.operation(kind="tool", name="mcp-consult", metadata={"tool_name": "consultar_glosario"})
    operation.finish(status="ok", metadata={"result_count": 2})
    trace.finish(status="ok", metadata={"duration_ms": 12})

    assert observer.health_status == "ok"
    assert client.options["mask_otel_spans"] is module.mask_otel_spans
    assert "input" not in client.root_options
    assert "output" not in client.root_options
    assert client.span.children[0]["metadata"] == {"tool_name": "consultar_glosario"}
    assert all("input" not in update and "output" not in update for update in client.span.updates)
    assert client.span.ended is True


def test_observability_export_failure_degrades_without_raising(monkeypatch):
    import agentes.analista.core.observability as module

    client = FakeLangfuse(fail_update=True)
    monkeypatch.setattr(module, "Langfuse", lambda **kwargs: client.options.update(kwargs) or client)
    settings = OpenCodeSettings(
        _env_file=None,
        langfuse_public_key=SecretStr("test-public"),
        langfuse_secret_key=SecretStr("test-secret"),
    )
    observer = Observability.from_settings(settings)

    trace = observer.start_turn(conversation_id="c", request_id="r", turn_id="t")
    trace.finish(status="error", error_code="OPENCODE_RATE_LIMITED")

    assert observer.health_status == "degraded"
