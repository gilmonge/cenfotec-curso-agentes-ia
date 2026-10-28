"""Safe structured logging for the local Analyst service."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


_ALLOWED_FIELDS = (
    "event",
    "conversation_id",
    "request_id",
    "turn_id",
    "tool_name",
    "error_code",
    "duration_ms",
    "status",
)


class SafeJsonFormatter(logging.Formatter):
    """Serialize only explicitly allowlisted metadata, never message content."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        for field in _ALLOWED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(SafeJsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
