"""FastAPI entry point for the local, loopback-only Analyst backend."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from agentes.analista.api.errors import install_error_handlers
from agentes.analista.api.routes.conversations import router as conversations_router
from agentes.analista.api.routes.health import router as health_router
from agentes.analista.core.conversation_store import ConversationStore
from agentes.analista.core.logging_config import configure_logging
from agentes.analista.core.models import ErrorCode, ErrorDetail
from agentes.analista.core.opencode_client import OpenCodeSettings
from agentes.analista.core.observability import Observability
from agentes.analista.core.prompt_loader import PromptLoadError, load_prompt


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = OpenCodeSettings.from_environment()
    try:
        prompt = load_prompt()
    except PromptLoadError as exc:
        raise RuntimeError("El prompt del agente no se puede cargar; el servicio no iniciará.") from exc
    app.state.settings = settings
    app.state.observability = Observability.from_settings(settings)
    app.state.prompt_snapshot = prompt
    app.state.restart_required = False
    app.state.store = ConversationStore(
        prompt_version=prompt.version,
        prompt_hash=prompt.sha256,
        ttl_seconds=settings.conversation_ttl_seconds,
        max_conversations=settings.max_conversations,
    )
    await app.state.store.start_cleanup()
    try:
        yield
    finally:
        await app.state.store.stop_cleanup()
        await app.state.observability.shutdown()


app = FastAPI(
    title="StoryCraft AI — Agente Analista",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
install_error_handlers(app)
app.include_router(health_router, prefix="/api/analista", tags=["health"])
app.include_router(conversations_router, prefix="/api/analista", tags=["conversations"])
