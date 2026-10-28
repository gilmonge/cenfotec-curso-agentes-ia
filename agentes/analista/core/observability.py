"""Privacy-preserving, best-effort Langfuse spans for analyst turns."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from time import monotonic
from typing import Any

from langfuse import Langfuse
from langfuse.types import MaskOtelSpansParams, MaskOtelSpansResult, OtelSpanPatch

from agentes.analista.core.opencode_client import OpenCodeSettings


logger = logging.getLogger(__name__)
_SENSITIVE_ATTRIBUTE_PARTS = (
    "gen_ai.prompt", "gen_ai.completion", "gen_ai.input", "gen_ai.output",
    "langfuse.observation.input", "langfuse.observation.output",
    "langfuse.trace.input", "langfuse.trace.output", "authorization",
)


def mask_otel_spans(*, params: MaskOtelSpansParams) -> MaskOtelSpansResult:
    """Mask content attributes while retaining operational metadata."""
    patches: dict[Any, OtelSpanPatch] = {}
    for identifier, span in params.spans.items():
        updates = {
            key: "[REDACTED]"
            for key in span.attributes
            if any(part in key.lower() for part in _SENSITIVE_ATTRIBUTE_PARTS)
        }
        if updates:
            patches[identifier] = OtelSpanPatch(set_attributes=updates)
    return MaskOtelSpansResult(span_patches=patches)


class _Operation:
    def __init__(self, span: Any = None, on_export_failure: Any = None) -> None:
        self.span = span
        self.on_export_failure = on_export_failure
        self.started = monotonic()

    def finish(self, *, status: str, error_code: str | None = None, metadata: Mapping[str, Any] | None = None) -> None:
        if self.span is None:
            return
        safe_metadata = {"status": status, "duration_ms": max(0, int((monotonic() - self.started) * 1000))}
        if error_code:
            safe_metadata["error_code"] = error_code
        if metadata:
            safe_metadata.update({key: value for key, value in metadata.items() if value is not None})
        try:
            self.span.update(metadata=safe_metadata, level="ERROR" if error_code else "DEFAULT")
            self.span.end()
        except Exception:
            if self.on_export_failure:
                self.on_export_failure()
            logger.warning("langfuse_span_failed", extra={"event": "langfuse_span_failed", "error_code": "LANGFUSE_EXPORT_FAILED"})
            self.span = None


class TurnTrace(_Operation):
    def operation(self, *, kind: str, name: str, metadata: Mapping[str, Any] | None = None) -> _Operation:
        if self.span is None:
            return _Operation()
        try:
            span = self.span.start_observation(as_type=kind, name=name, metadata=dict(metadata or {}))
            return _Operation(span, self.on_export_failure)
        except Exception:
            if self.on_export_failure:
                self.on_export_failure()
            logger.warning("langfuse_child_span_failed", extra={"event": "langfuse_child_span_failed", "error_code": "LANGFUSE_EXPORT_FAILED"})
            return _Operation()


class Observability:
    """Initialize tracing only when configured; tracing failures never block chat."""

    def __init__(self, client: Langfuse | None = None) -> None:
        self.client = client
        self.export_failed = False

    @property
    def enabled(self) -> bool:
        return self.client is not None

    @property
    def health_status(self) -> str:
        if not self.enabled:
            return "disabled"
        return "degraded" if self.export_failed else "ok"

    def _mark_export_failed(self) -> None:
        self.export_failed = True

    @classmethod
    def from_settings(cls, settings: OpenCodeSettings) -> "Observability":
        public_key = settings.langfuse_public_key.get_secret_value()
        secret_key = settings.langfuse_secret_key.get_secret_value()
        if not public_key or not secret_key:
            return cls()
        try:
            client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                base_url=settings.langfuse_base_url,
                mask_otel_spans=mask_otel_spans,
            )
            return cls(client)
        except Exception:
            logger.warning("langfuse_init_failed", extra={"event": "langfuse_init_failed", "error_code": "LANGFUSE_DISABLED"})
            instance = cls()
            instance.export_failed = True
            return instance

    def start_turn(self, *, conversation_id: Any, request_id: Any, turn_id: Any) -> TurnTrace:
        if self.client is None:
            return TurnTrace()
        try:
            span = self.client.start_observation(
                as_type="chain",
                name="analyst-turn",
                metadata={
                    "conversation_id": str(conversation_id),
                    "request_id": str(request_id),
                    "turn_id": str(turn_id),
                },
            )
            return TurnTrace(span, self._mark_export_failed)
        except Exception:
            self._mark_export_failed()
            logger.warning("langfuse_turn_span_failed", extra={"event": "langfuse_turn_span_failed", "error_code": "LANGFUSE_EXPORT_FAILED"})
            return TurnTrace()

    async def shutdown(self, timeout_seconds: float = 2.0) -> None:
        if self.client is None:
            return

        def flush_and_shutdown() -> None:
            self.client.flush()
            self.client.shutdown()

        try:
            await asyncio.wait_for(asyncio.to_thread(flush_and_shutdown), timeout=timeout_seconds)
        except Exception:
            self._mark_export_failed()
            logger.warning("langfuse_shutdown_failed", extra={"event": "langfuse_shutdown_failed", "error_code": "LANGFUSE_EXPORT_FAILED"})
