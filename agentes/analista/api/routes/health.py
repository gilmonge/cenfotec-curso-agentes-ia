"""Health route for the local analyst service."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Request

from agentes.analista.core.models import (
    CheckStatus,
    HealthChecks,
    HealthResponse,
    HealthStatus,
    LangfuseCheck,
    McpCheck,
    OpenCodeCheck,
    ToolName,
)
from agentes.analista.core.opencode_client import OpenCodeClient, OpenCodeClientError, OpenCodeSettings
from agentes.analista.core.opencode_compat import is_supported_opencode_version
from agentes.analista.core.prompt_loader import PromptLoadError, load_prompt
from agentes.analista.core.orchestrator import EXPECTED_TOOLS
from agentes.analista.mcp.tools import mcp as servidor_mcp


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    state = request.app.state
    prompt_status = CheckStatus.OK
    restart_required = False
    try:
        current_prompt = load_prompt()
        restart_required = current_prompt.sha256 != state.prompt_snapshot.sha256
        state.restart_required = restart_required
        if restart_required:
            prompt_status = CheckStatus.DEGRADED
    except PromptLoadError:
        current_prompt = state.prompt_snapshot
        prompt_status = CheckStatus.UNAVAILABLE

    settings = getattr(state, "settings", None) or OpenCodeSettings.from_environment()
    configured_provider_id = getattr(settings, "opencode_provider_id", "") or "opencode"
    configured_model_id = getattr(settings, "opencode_model_id", "") or None
    opencode_check = OpenCodeCheck(
        status=CheckStatus.UNAVAILABLE,
        version=None,
        agent=None,
        configured_provider_id=configured_provider_id,
        configured_model_id=configured_model_id,
    )
    server_version: str | None = None
    verified_agent: str | None = None
    try:
        async with OpenCodeClient(settings=settings, prompt=current_prompt) as client:
            info = await client.server_info()
            candidate_version = info.get("version")
            server_version = candidate_version if isinstance(candidate_version, str) else None
            if not is_supported_opencode_version(candidate_version):
                raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "La versión de OpenCode no es compatible.")
            agent = await client.verify_agent("analista")
            verified_agent = "analista"
            model = await client.select_model(agent)
            opencode_check = OpenCodeCheck(
                status=CheckStatus.OK,
                version=info["version"],
                agent="analista",
                configured_provider_id=configured_provider_id,
                configured_model_id=configured_model_id,
                selected_provider_id=model["providerID"],
                selected_model_id=model["id"],
            )
    except OpenCodeClientError as exc:
        opencode_check = OpenCodeCheck(
            status=CheckStatus.UNAVAILABLE,
            version=server_version,
            agent=verified_agent,
            configured_provider_id=configured_provider_id,
            configured_model_id=configured_model_id,
            rejection_code=exc.code,
            rejection_reason=str(exc),
        )

    # Se verifica el registro de herramientas dentro del mismo proceso: lanzar un proceso hijo en cada
    # consulta de salud consume ~90 MB y agota la memoria del plan gratuito (512 MB).
    mcp_check = McpCheck(status=CheckStatus.UNAVAILABLE, tools=[])
    try:
        registered = await servidor_mcp.list_tools()
        names = {tool.name for tool in registered}
        if names == EXPECTED_TOOLS:
            mcp_check = McpCheck(status=CheckStatus.OK, tools=[ToolName(name) for name in sorted(names)])
    except Exception:
        logger.warning("No se pudo verificar el registro de herramientas MCP", exc_info=True)

    langfuse_check = LangfuseCheck(status=CheckStatus(state.observability.health_status))
    checks = HealthChecks(opencode=opencode_check, mcp=mcp_check, langfuse=langfuse_check)
    if prompt_status == CheckStatus.UNAVAILABLE or opencode_check.status == CheckStatus.UNAVAILABLE or mcp_check.status == CheckStatus.UNAVAILABLE:
        status = HealthStatus.UNAVAILABLE
    elif restart_required or langfuse_check.status != CheckStatus.OK:
        status = HealthStatus.DEGRADED
    else:
        status = HealthStatus.READY

    return HealthResponse(
        status=status,
        checked_at=datetime.now(UTC),
        backend_version="1.0.0",
        timeout_seconds=state.settings.turn_timeout_seconds,
        message_limit=state.settings.message_limit,
        prompt_version=current_prompt.version,
        prompt_hash=current_prompt.sha256,
        restart_required=restart_required,
        checks=checks,
    )
