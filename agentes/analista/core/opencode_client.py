"""Minimal, secret-safe asynchronous client for OpenCode Server API v2."""
from __future__ import annotations

import asyncio
import math
import re
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from agentes.analista.core.prompt_loader import PromptSnapshot, load_prompt, verify_loaded_prompt
from agentes.analista.core.opencode_compat import (
    SUPPORTED_OPENCODE_VERSIONS,
    is_supported_opencode_version,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
# Backwards-compatible name for callers that inspect the client allowlist.
SUPPORTED_VERSIONS = SUPPORTED_OPENCODE_VERSIONS
DENY_ALL = [{"action": "*", "resource": "*", "effect": "deny"}]


class OpenCodeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    server_url: str = "http://127.0.0.1:4096"
    server_username: str = "opencode"
    server_password: SecretStr = SecretStr("")
    opencode_provider_id: str = ""
    opencode_model_id: str = ""
    request_timeout_seconds: float = 90.0
    turn_timeout_seconds: float = Field(default=90.0, gt=0, le=300)
    message_limit: int = 4000
    conversation_ttl_seconds: int = Field(default=1800, gt=0)
    max_conversations: int = Field(default=32, ge=1, le=32)
    langfuse_public_key: SecretStr = SecretStr("")
    langfuse_secret_key: SecretStr = SecretStr("")
    langfuse_base_url: str = "https://us.cloud.langfuse.com"

    @model_validator(mode="after")
    def validate_lifecycle_limits(self) -> "OpenCodeSettings":
        if self.conversation_ttl_seconds <= self.turn_timeout_seconds:
            raise ValueError("El TTL de conversación debe superar el deadline total del turno.")
        return self

    @classmethod
    def from_environment(cls) -> "OpenCodeSettings":
        # Public names in .env remain explicit and scoped to this backend.
        return cls(
            server_url=_read_env_value("OPENCODE_SERVER_URL", "http://127.0.0.1:4096"),
            server_username=_read_env_value("OPENCODE_SERVER_USERNAME", "opencode"),
            server_password=SecretStr(_read_env_value("OPENCODE_SERVER_PASSWORD", "")),
            opencode_provider_id=_read_env_value("OPENCODE_PROVIDER_ID", "").strip(),
            opencode_model_id=_read_env_value("OPENCODE_MODEL_ID", "").strip(),
            request_timeout_seconds=float(_read_env_value("ANALISTA_REQUEST_TIMEOUT_SECONDS", "90")),
            turn_timeout_seconds=float(_read_env_value("ANALISTA_TURN_TIMEOUT_SECONDS", "90")),
            message_limit=int(_read_env_value("ANALISTA_MESSAGE_MAX_CHARS", "4000")),
            conversation_ttl_seconds=int(_read_env_value("ANALISTA_CONVERSATION_TTL_SECONDS", "1800")),
            max_conversations=int(_read_env_value("ANALISTA_MAX_CONVERSATIONS", "32")),
            langfuse_public_key=SecretStr(_read_env_value("LANGFUSE_PUBLIC_KEY", "")),
            langfuse_secret_key=SecretStr(_read_env_value("LANGFUSE_SECRET_KEY", "")),
            langfuse_base_url=_read_env_value("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com"),
        )


def _read_env_value(name: str, default: str) -> str:
    """Allow SettingsConfigDict aliases without ever exposing a credential."""
    import os

    value = os.environ.get(name)
    if value is not None:
        return value
    env_path = PROJECT_ROOT / ".env"
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key, separator, raw_value = line.partition("=")
            if separator and key.strip() == name:
                value = raw_value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                return value
    except (OSError, UnicodeError):
        pass
    return default


class OpenCodeClientError(RuntimeError):
    """Safe error suitable for mapping to public service error codes."""

    def __init__(
        self, code: str, message: str, *, retryable: bool = False, status: int | None = None,
        retry_at: datetime | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.status = status
        self.retry_at = retry_at


class OpenCodeClient:
    def __init__(
        self,
        settings: OpenCodeSettings | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        prompt: PromptSnapshot | None = None,
    ) -> None:
        self.settings = settings or OpenCodeSettings.from_environment()
        if not self.settings.server_password.get_secret_value():
            raise OpenCodeClientError("OPENCODE_AUTH_FAILED", "Falta configurar la autenticación local de OpenCode.")
        self.prompt = prompt or load_prompt()
        self._client = client
        self._owns_client = client is None
        self._deadline: float | None = None

    async def __aenter__(self) -> "OpenCodeClient":
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.settings.server_url.rstrip("/"),
                auth=(self.settings.server_username, self.settings.server_password.get_secret_value()),
                headers={"Accept": "application/json"},
                timeout=httpx.Timeout(self.settings.request_timeout_seconds),
            )
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def http(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Usa OpenCodeClient dentro de un contexto asíncrono.")
        return self._client

    def set_deadline(self, deadline: float) -> None:
        self._deadline = deadline

    async def _request(
        self, method: str, path: str, *, json: Any = None,
        params: Mapping[str, str] | None = None, timeout_seconds: float | None = None,
    ) -> Any:
        if timeout_seconds is None:
            timeout_seconds = self.settings.request_timeout_seconds
            if self._deadline is not None:
                remaining = self._deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise OpenCodeClientError("TURN_TIMEOUT", "Se agotó el tiempo del turno.", retryable=True)
                timeout_seconds = min(
                    timeout_seconds,
                    remaining,
                )
        try:
            response = await self.http.request(
                method, path, json=json, params=params,
                **({"timeout": timeout_seconds} if timeout_seconds is not None else {}),
            )
        except httpx.TimeoutException as exc:
            if self._deadline is not None and asyncio.get_running_loop().time() >= self._deadline:
                raise OpenCodeClientError("TURN_TIMEOUT", "Se agotó el tiempo del turno.", retryable=True) from exc
            raise OpenCodeClientError("OPENCODE_UNAVAILABLE", "OpenCode no está disponible.", retryable=True) from exc
        except (httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            raise OpenCodeClientError("OPENCODE_UNAVAILABLE", "OpenCode no está disponible.", retryable=True) from exc
        status = response.status_code
        if status in (401, 403):
            raise OpenCodeClientError("OPENCODE_AUTH_FAILED", "OpenCode rechazó la autenticación.", status=status)
        if status == 404:
            raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "OpenCode no encontró el recurso esperado.", status=status)
        if status == 409:
            raise OpenCodeClientError("OPENCODE_UNAVAILABLE", "OpenCode reportó un conflicto de sesión.", retryable=True, status=status)
        if status == 429:
            retry_at = _retry_at_from_headers(response.headers)
            raise OpenCodeClientError(
                "OPENCODE_RATE_LIMITED", "OpenCode agotó la cuota disponible del proveedor.",
                retryable=True, status=status, retry_at=retry_at,
            )
        if status == 504:
            raise OpenCodeClientError("TURN_TIMEOUT", "OpenCode agotó el tiempo de la solicitud.", retryable=True, status=status)
        if status == 503 or status >= 500:
            raise OpenCodeClientError("OPENCODE_UNAVAILABLE", "OpenCode o el proveedor no está disponible.", retryable=True, status=status)
        if status >= 400:
            raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "OpenCode rechazó una solicitud incompatible.", status=status)
        if status == 204:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "OpenCode devolvió una respuesta no JSON.") from exc

    def _location_params(self) -> dict[str, str]:
        return {"location[directory]": str(PROJECT_ROOT)}

    async def server_info(self) -> dict[str, Any]:
        value = await self._request("GET", "/api/info")
        if not isinstance(value, dict) or not is_supported_opencode_version(value.get("version")):
            raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "La versión o el esquema de OpenCode no coincide.")
        return value

    async def verify_agent(self, agent_id: str = "analista") -> dict[str, Any]:
        envelope = await self._request("GET", "/api/agent", params=self._location_params())
        agents = envelope.get("data") if isinstance(envelope, dict) else None
        agent = next((item for item in agents or [] if item.get("id") == agent_id), None)
        if not isinstance(agent, dict):
            raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "El agente Analista no está cargado en el location esperado.")
        permissions = agent.get("permission", agent.get("permissions", []))
        if not _contains_deny_all(permissions):
            raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "El agente no conserva permisos deny-all.")
        if not verify_loaded_prompt(self.prompt, agent.get("system")):
            raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "El servidor no cargó la versión local del prompt.")
        return agent

    async def select_model(self, agent: Mapping[str, Any] | None = None) -> dict[str, str]:
        configured_provider_id = self.settings.opencode_provider_id.strip()
        provider_id = configured_provider_id or "opencode"
        configured_id = self.settings.opencode_model_id
        agent_model = (agent or {}).get("model")

        if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", provider_id):
            raise OpenCodeClientError("MODEL_UNAVAILABLE", "El identificador del provider configurado no es válido.")

        if configured_id:
            requested_id = configured_id
        elif isinstance(agent_model, Mapping):
            agent_provider_id = agent_model.get("providerID")
            requested_id = agent_model.get("modelID", agent_model.get("id"))
            if agent_provider_id != provider_id:
                raise OpenCodeClientError(
                    "MODEL_UNAVAILABLE",
                    f"El agente selecciona el provider '{agent_provider_id}', pero el provider configurado es '{provider_id}'.",
                )
        else:
            default = await self._request("GET", "/api/model/default", params=self._location_params())
            model = default.get("data") if isinstance(default, dict) else None
            if not isinstance(model, Mapping) or model.get("providerID") != provider_id or not model.get("modelID"):
                raise OpenCodeClientError(
                    "MODEL_UNAVAILABLE",
                    f"OpenCode no tiene un modelo predeterminado para el provider '{provider_id}'.",
                )
            requested_id = str(model["modelID"])

        if not isinstance(requested_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,160}", requested_id):
            raise OpenCodeClientError("MODEL_UNAVAILABLE", "El identificador de modelo configurado no es válido.")
        envelope = await self._request("GET", "/api/model", params=self._location_params())
        models = envelope.get("data") if isinstance(envelope, dict) else None
        match = next(
            (
                item for item in models or []
                if item.get("providerID") == provider_id
                and item.get("modelID") == requested_id
                and item.get("enabled", True) is not False
            ),
            None,
        )
        if match is None:
            provider_models = [item for item in models or [] if item.get("providerID") == provider_id]
            listed = next((item for item in provider_models if item.get("modelID") == requested_id), None)
            if listed is not None and listed.get("enabled", True) is False:
                reason = f"El modelo '{provider_id}/{requested_id}' está deshabilitado en OpenCode."
            elif not provider_models:
                reason = f"OpenCode no anuncia el provider '{provider_id}'."
            else:
                reason = f"OpenCode no anuncia el modelo '{provider_id}/{requested_id}'."
            raise OpenCodeClientError("MODEL_UNAVAILABLE", reason)
        # Naming both provider and model is an explicit operator choice and
        # authorizes models whose OpenCode metadata is paid or unpriced.
        explicitly_authorized = bool(configured_provider_id and configured_id)
        if not explicitly_authorized and not _has_zero_cost(match.get("cost")):
            raise OpenCodeClientError(
                "MODEL_UNAVAILABLE",
                "El modelo no tiene costo cero verificado; configura OPENCODE_PROVIDER_ID y OPENCODE_MODEL_ID para autorizarlo explícitamente.",
            )
        return {"providerID": provider_id, "id": str(match["modelID"])}

    async def create_session(self, *, title: str, agent_id: str = "analista", model: Mapping[str, str] | None = None) -> dict[str, Any]:
        body = {
            "title": title,
            "agent": agent_id,
            "model": dict(model or await self.select_model()),
            "location": {"directory": str(PROJECT_ROOT)},
            "permissions": DENY_ALL,
        }
        result = await self._request("POST", "/api/session", json=body)
        session = result.get("data") if isinstance(result, dict) else None
        if not isinstance(session, dict) or not isinstance(session.get("id"), str):
            raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "OpenCode no devolvió una sesión v2 válida.")
        if not _contains_deny_all(session.get("permissions", [])):
            await self.delete_session(session["id"])
            raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "La sesión no conserva permisos deny-all.")
        return session

    async def submit_prompt(self, session_id: str, text: str) -> dict[str, Any]:
        result = await self._request("POST", f"/api/session/{quote(session_id, safe='')}/prompt", json={"text": text})
        envelope = result.get("data") if isinstance(result, dict) else None
        if not isinstance(envelope, dict):
            raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "OpenCode no confirmó la admisión del mensaje.")
        return envelope

    async def wait_for_assistant(
        self, session_id: str, *, deadline: float, after: int | float | str | None = None
    ) -> dict[str, Any]:
        endpoint = f"/api/session/{quote(session_id, safe='')}/message"
        while asyncio.get_running_loop().time() < deadline:
            envelope = await self._request(
                "GET", endpoint, params={"limit": "30", "order": "asc"},
                timeout_seconds=max(0.1, deadline - asyncio.get_running_loop().time()),
            )
            records = envelope.get("data") if isinstance(envelope, dict) else None
            if not isinstance(records, list):
                raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "OpenCode devolvió mensajes con schema incompatible.")
            for record in reversed(records):
                if record.get("type") != "assistant" or not record.get("time", {}).get("completed"):
                    continue
                created = record.get("time", {}).get("created")
                if after is not None:
                    if isinstance(created, (int, float)) and isinstance(after, (int, float)) and created <= after:
                        continue
                    if isinstance(created, str) and isinstance(after, str) and created <= after:
                        continue
                if record.get("finish") == "error" or record.get("error"):
                    error = record.get("error") or {}
                    error_type = str(error.get("type", "")).lower() if isinstance(error, Mapping) else ""
                    error_status = error.get("status") if isinstance(error, Mapping) else None
                    if error_status == 429 or error_type in {
                        "provider.quota", "provider.rate-limit", "provider.free-limit",
                    }:
                        completed_at = _message_completed_at(record)
                        retry_at = _retry_at_from_ms(
                            error.get("retryAfterMs"), now=completed_at,
                        ) if isinstance(error, Mapping) else None
                        raise OpenCodeClientError(
                            "OPENCODE_RATE_LIMITED", "OpenCode agotó la cuota disponible del proveedor.",
                            retryable=True, status=429, retry_at=retry_at,
                        )
                    if error_status in (401, 403):
                        raise OpenCodeClientError("OPENCODE_AUTH_FAILED", "OpenCode rechazó la autenticación del proveedor.", status=error_status)
                    if error_status == 504:
                        raise OpenCodeClientError("TURN_TIMEOUT", "OpenCode agotó el tiempo de generación.", retryable=True, status=504)
                    if "model_not_found" in error_type or "model unavailable" in error_type:
                        raise OpenCodeClientError("MODEL_UNAVAILABLE", "El modelo seleccionado no está disponible.", retryable=True)
                    raise OpenCodeClientError("OPENCODE_UNAVAILABLE", "El proveedor no pudo completar la generación.", retryable=True)
                content = record.get("content")
                if not isinstance(content, list):
                    raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "El mensaje assistant no tiene contenido v2 válido.")
                text = "".join(part.get("text", "") for part in content if part.get("type") == "text")
                if not text.strip():
                    raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "El mensaje assistant no contiene texto utilizable.")
                if any(part.get("type") == "tool" for part in content):
                    raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "La respuesta incluyó una parte de herramienta no permitida.")
                return {"text": text, "finish": record.get("finish"), "model": record.get("model")}
            await asyncio.sleep(min(0.25, max(0, deadline - asyncio.get_running_loop().time())))
        raise OpenCodeClientError("TURN_TIMEOUT", "Se agotó el tiempo de generación del modelo.", retryable=True)

    async def interrupt(self, session_id: str) -> bool:
        result = await self._request(
            "POST", f"/api/session/{quote(session_id, safe='')}/interrupt", timeout_seconds=2.0
        )
        if not isinstance(result, dict) or not isinstance(result.get("interrupted"), bool):
            raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "OpenCode devolvió un interrupt incompatible.")
        return result["interrupted"]

    async def delete_session(self, session_id: str) -> None:
        try:
            await self._request(
                "DELETE", f"/api/session/{quote(session_id, safe='')}", timeout_seconds=2.0
            )
        except OpenCodeClientError as exc:
            if exc.status != 404:
                raise

    @asynccontextmanager
    async def session(self, *, title: str, agent_id: str = "analista", model: Mapping[str, str] | None = None) -> AsyncIterator[dict[str, Any]]:
        value = await self.create_session(title=title, agent_id=agent_id, model=model)
        failed = False
        try:
            yield value
        except BaseException:
            failed = True
            try:
                await asyncio.shield(self.interrupt(value["id"]))
            except (OpenCodeClientError, asyncio.CancelledError):
                pass
            raise
        finally:
            try:
                await asyncio.shield(self.delete_session(value["id"]))
            except asyncio.CancelledError:
                if not failed:
                    raise
            except OpenCodeClientError:
                if not failed:
                    raise


def _contains_deny_all(value: Any) -> bool:
    if isinstance(value, list):
        return any(_contains_deny_all(item) for item in value)
    if isinstance(value, dict):
        if value.get("action") == "*" and value.get("resource") == "*" and value.get("effect") == "deny":
            return True
        return any(_contains_deny_all(item) for item in value.values())
    return False


def _retry_at_from_ms(value: Any, *, now: datetime | None = None) -> datetime | None:
    """Convert OpenCode's optional retryAfterMs duration to a UTC instant."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    current = now or datetime.now(UTC)
    if value == 0:
        return current.astimezone(UTC)
    try:
        retry_at = current + timedelta(milliseconds=value)
    except (OverflowError, ValueError):
        return None
    return retry_at.astimezone(UTC) if retry_at > current else None


def _message_completed_at(record: Mapping[str, Any]) -> datetime | None:
    """Use OpenCode's completion timestamp as the base for a provider delay."""
    message_time = record.get("time")
    value = message_time.get("completed") if isinstance(message_time, Mapping) else None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or (isinstance(value, float) and not math.isfinite(value))
        or value <= 0
    ):
        return None
    try:
        return datetime.fromtimestamp(value / 1000, UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _retry_at_from_headers(headers: Mapping[str, str], *, now: datetime | None = None) -> datetime | None:
    """Parse provider/server retry hints without exposing the raw header value."""
    current = now or datetime.now(UTC)
    retry_after_ms = headers.get("retry-after-ms")
    if retry_after_ms is not None:
        parsed_ms = _retry_at_from_ms(_parse_nonnegative_integer(retry_after_ms), now=current)
        if parsed_ms is not None:
            return parsed_ms

    retry_after = headers.get("retry-after")
    if retry_after is None:
        return None
    value = retry_after.strip()
    seconds = _parse_nonnegative_integer(value)
    if seconds is not None:
        if seconds == 0:
            return current.astimezone(UTC)
        try:
            retry_at = current + timedelta(seconds=seconds)
        except (OverflowError, ValueError):
            return None
        return retry_at.astimezone(UTC) if retry_at > current else None
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if retry_at is None:
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    retry_at = retry_at.astimezone(UTC)
    return retry_at if retry_at > current else None


def _parse_nonnegative_integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
        return int(value.strip())
    return None


def _has_zero_cost(value: Any) -> bool:
    """Require explicit zero input/output/cache pricing for every cost tier."""
    entries = value if isinstance(value, list) else [value]
    if not entries or not all(isinstance(entry, Mapping) for entry in entries):
        return False
    allowed_keys = {"input", "output", "cache", "tier"}
    for entry in entries:
        if set(entry) - allowed_keys:
            return False
        for key in ("input", "output"):
            amount = entry.get(key)
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount != 0:
                return False
        cache = entry.get("cache")
        if not isinstance(cache, Mapping) or set(cache) != {"read", "write"}:
            return False
        for amount in cache.values():
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount != 0:
                return False
        tier = entry.get("tier")
        if tier is not None and (
            not isinstance(tier, Mapping)
            or tier.get("type") != "context"
            or not isinstance(tier.get("size"), int)
            or set(tier) != {"type", "size"}
        ):
            return False
    return True
