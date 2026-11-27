"""Read-only, opt-in connection checks for OpenCode and Pinecone test services.

Disabled by default. This module never uses TiDB, creates Pinecone indexes,
ingests vectors, or prints credentials or service response bodies.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any


def _enabled() -> bool:
    return (
        os.environ.get("FEATURE003_REAL_SERVICES", "").strip() == "1"
        and os.environ.get("FEATURE003_TEST_ENV_AUTHORIZED", "").strip() == "1"
    )


def _has_credentials() -> tuple[bool, bool]:
    from agentes.analista.core.opencode_client import OpenCodeSettings

    opencode = bool(OpenCodeSettings.from_environment().server_password.get_secret_value().strip())
    pinecone = bool(os.environ.get("PINECONE_API_KEY", "").strip())
    return opencode, pinecone


async def _check_opencode() -> dict[str, Any]:
    from agentes.analista.core.agent_registry import AgentId
    from agentes.analista.core.opencode_client import OpenCodeClient

    async with OpenCodeClient() as client:
        server = await client.server_info()
        agents = []
        for agent_id in AgentId:
            await client.verify_agent(agent_id)
            agents.append(agent_id.value)
    return {"status": "verified", "server_version": server.get("version"), "agents_verified": len(agents)}


def _check_pinecone() -> dict[str, Any]:
    from pinecone import Pinecone

    indexes = list(Pinecone(api_key=os.environ["PINECONE_API_KEY"].strip()).list_indexes())
    return {"status": "verified", "visible_index_count": len(indexes)}


async def run() -> tuple[dict[str, Any], int]:
    if not _enabled():
        return ({
            "diagnostic": "feature003_real_services",
            "status": "disabled",
            "message": "No external connection was attempted.",
            "enable_with": [
                "FEATURE003_REAL_SERVICES=1", "FEATURE003_TEST_ENV_AUTHORIZED=1",
                "OPENCODE_SERVER_PASSWORD", "PINECONE_API_KEY",
            ],
        }, 0)

    has_opencode, has_pinecone = _has_credentials()
    result: dict[str, Any] = {"diagnostic": "feature003_real_services", "status": "completed", "services": {}}
    exit_code = 0
    if not has_opencode:
        result["services"]["opencode"] = {"status": "skipped", "reason": "credential_not_set"}
    else:
        try:
            result["services"]["opencode"] = await _check_opencode()
        except Exception as exc:  # only the exception type is safe to report
            result["services"]["opencode"] = {"status": "failed", "error_type": type(exc).__name__}
            exit_code = 1

    if not has_pinecone:
        result["services"]["pinecone"] = {"status": "skipped", "reason": "credential_not_set"}
    else:
        try:
            result["services"]["pinecone"] = _check_pinecone()
        except Exception as exc:  # never include SDK messages, endpoints, or response data
            result["services"]["pinecone"] = {"status": "failed", "error_type": type(exc).__name__}
            exit_code = 1
    return result, exit_code


def main() -> int:
    result, code = asyncio.run(run())
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
