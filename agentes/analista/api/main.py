"""FastAPI entry point for the local, loopback-only Analyst backend."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agentes.analista.api.acceso import credenciales_desde_entorno
from agentes.analista.api.errors import install_error_handlers
from agentes.analista.api.estaticos import montar_frontend
from agentes.analista.api.routes.conversations import router as conversations_router
from agentes.analista.api.routes.health import router as health_router
from agentes.analista.api.routes.historias import router as historias_router
from agentes.analista.api.routes.repositorio import router as repositorio_router
from agentes.analista.api.routes.seguridad import router as seguridad_router
from agentes.analista.api.routes.pendientes import router as pendientes_router
from agentes.notificaciones.teams_service import TeamsService
from agentes.analista.api.routes.workflows import router as workflows_router
from agentes.analista.core.conversation_store import ConversationStore
from agentes.analista.core.logging_config import configure_logging
from agentes.analista.core.models import ErrorCode, ErrorDetail
from agentes.analista.core.opencode_client import OpenCodeSettings
from agentes.analista.core.observability import Observability
from agentes.analista.core.prompt_loader import PromptLoadError, load_prompt
from agentes.analista.core.workflow_graph import WorkflowRuntime
from agentes.analista.memory.repositorio import RepositorioHU
from agentes.conocimiento.sincronizacion import SincronizadorConocimiento
from agentes.seguridad.clave import FirmaSesion
from agentes.seguridad.repositorio_seguridad import RepositorioSeguridad


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
    app.state.repositorio = RepositorioHU()
    # Aviso por Teams al Product Owner (con TEAMS_WEBHOOK_URL; sin ella no envía nada).
    app.state.teams = TeamsService()
    # Seguridad por usuario: activa cuando el servicio tiene ACCESO_USUARIO y ACCESO_CLAVE (el administrador
    # inicial). Sin ellas (desarrollo local) se atiende como usuario local con todas las acciones.
    credenciales = credenciales_desde_entorno()
    app.state.seguridad = None
    if credenciales:
        app.state.seguridad = RepositorioSeguridad(app.state.repositorio.motor)
        app.state.seguridad.inicializar(*credenciales)
        app.state.firma_sesion = FirmaSesion(os.environ.get("SESION_SECRETO", "").strip() or credenciales[1])
    # Repositorio del Asesor y carga del conocimiento en Pinecone, en segundo plano y sin pasos manuales.
    app.state.sincronizador = SincronizadorConocimiento(repositorio=app.state.repositorio)
    app.state.repositorio.al_cambiar_conocimiento = app.state.sincronizador.programar_repositorio
    app.state.sincronizador.iniciar_en_segundo_plano()
    app.state.workflow_runtime = WorkflowRuntime(
        observability=app.state.observability,
        repository=app.state.repositorio,
        # Los flujos se guardan en la base de datos: se pueden retomar otro día o tras un reinicio.
        persistencia=app.state.repositorio,
    )
    app.state.workflow_operation_guard = asyncio.Lock()
    app.state.workflow_active_operations = set()
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
    title="Historias de Usuario — Agente Analista",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
install_error_handlers(app)
app.include_router(health_router, prefix="/api/analista", tags=["health"])
app.include_router(conversations_router, prefix="/api/analista", tags=["conversations"])
app.include_router(repositorio_router, prefix="/api/analista", tags=["repositorio"])
app.include_router(historias_router, prefix="/api/analista", tags=["historias"])
app.include_router(seguridad_router, prefix="/api/analista", tags=["seguridad"])
app.include_router(pendientes_router, prefix="/api/analista", tags=["pendientes"])
app.include_router(workflows_router, prefix="/api/workflows", tags=["workflows"])

# Publicación en un hosting: la interfaz la sirve el mismo servicio. La API pide sesión por usuario
# (ver agentes/analista/api/sesion.py); la interfaz es pública para poder mostrar el inicio de sesión.
credenciales_desde_entorno()  # con ANALISTA_PUBLICO=1 y sin credenciales, el servicio no inicia
montar_frontend(app)
