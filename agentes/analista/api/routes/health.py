"""Health route for the local analyst service."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from langchain.mcp import MCPAdapter

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
from agentes.analista.core.opencode_client import OpenCodeClient, OpenCodeClientError
from agentes.analista.core.opencode_compat import is_supported_opencode_version
from agentes.analista.core.prompt_loader import PromptLoadError, load_prompt
from agentes.analista.core.orchestrator import MCP_SERVER, EXPECTED_TOOLS


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

    opencode_check = OpenCodeCheck(status=CheckStatus.UNAVAILABLE, version=None, agent=None)
    try:
        async with OpenCodeClient(prompt=current_prompt) as client:
            info = await client.server_info()
            if not is_supported_opencode_version(info.get("version")):
                raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "La versión de OpenCode no es compatible.")
            await client.verify_agent("analista")
            opencode_check = OpenCodeCheck(status=CheckStatus.OK, version=info["version"], agent="analista")
    except OpenCodeClientError:
        pass

    mcp_check = McpCheck(status=CheckStatus.UNAVAILABLE, tools=[])
    try:
        async with MCPAdapter(MCP_SERVER) as adapter:
            tools = await adapter.list_tools()
        names = {tool.name for tool in tools}
        if names == EXPECTED_TOOLS:
            mcp_check = McpCheck(status=CheckStatus.OK, tools=[ToolName(name) for name in sorted(names)])
    except Exception:
        pass

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
