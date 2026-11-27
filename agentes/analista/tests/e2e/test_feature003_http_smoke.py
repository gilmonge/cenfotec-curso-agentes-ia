"""HTTP smoke for feature 003 with synthetic agents and a temporary SQLite repository."""
from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from contextlib import asynccontextmanager
from contextlib import contextmanager
from uuid import UUID

import httpx
import uvicorn
from fastapi import FastAPI

from agentes.analista.api.errors import install_error_handlers
from agentes.analista.api.routes import workflows
from agentes.analista.core.models import (
    ErrorCode,
)
from agentes.analista.core.agent_registry import AgentId
from agentes.analista.core.observability import Observability
from agentes.analista.core.workflow_graph import WorkflowRuntime
from agentes.conocimiento.retrieval import RetrievalResult
from agentes.analista.memory.repositorio import RepositorioHU


SYNTHETIC_REQUEST = "Consultar vigencia de póliza ficticia TEST-003"
SYNTHETIC_CHANGE = "Agregar la fecha de vencimiento al resumen"


class SyntheticOpenCode:
    """Return deterministic synthetic model outputs at the external OpenCode boundary."""

    def __init__(self, *, prompt=None, agent_id=AgentId.ANALYST):
        self.prompt_snapshot = prompt
        self.agent_id = AgentId(agent_id)
        self.prompt = ""
        self.settings = type("Settings", (), {"turn_timeout_seconds": 10})()
        self.calls = SyntheticOpenCode.calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def set_deadline(self, _deadline):
        return None

    async def server_info(self):
        self.calls.append(self.agent_id.value)
        if self.agent_id == AgentId.ANALYST and SyntheticOpenCode.fail_first_analyst_call:
            SyntheticOpenCode.fail_first_analyst_call = False
            from agentes.analista.core.opencode_client import OpenCodeClientError
            raise OpenCodeClientError(ErrorCode.TURN_TIMEOUT.value, "private synthetic timeout", retryable=True)
        return {"version": "2.0.27"}

    async def verify_agent(self, agent):
        assert AgentId(agent) == self.agent_id
        return {"id": self.agent_id.value}

    async def select_model(self, _agent):
        return {"providerID": "synthetic", "id": "test-only"}

    @asynccontextmanager
    async def session(self, *, title, model):
        yield {"id": f"synthetic-{self.agent_id.value}", "title": title, "model": model}

    async def submit_prompt(self, _session_id, prompt):
        self.prompt = prompt
        return {"time": {"created": 1}}

    async def wait_for_assistant(self, _session_id, *, deadline, after=None):
        assert deadline > 0
        assert after == 1
        if self.agent_id == AgentId.ANALYST:
            answered = "2030-12-31" in self.prompt
            data = {
                "respuesta_markdown": "Análisis sintético de un requerimiento enteramente ficticio.",
                "analisis": {
                    "conocida": ["Se solicita consultar una póliza ficticia."],
                    "faltante": [] if answered else ["Fecha de vigencia"],
                    "supuesta": [], "ambigua": [],
                },
                "preguntas": [{
                    "categoria": "Datos requeridos",
                    "pregunta": "¿Cuál es la fecha de vigencia de la póliza ficticia?",
                    "estado": "respondida" if answered else "pendiente",
                }],
                "listo_para_redactor": True,
            }
        elif self.agent_id == AgentId.WRITER_REVIEWER:
            if "Revisa la historia" in self.prompt:
                data = {"requires_correction": False, "observations": []}
            else:
                data = {
                    "como": "persona usuaria ficticia",
                    "quiero": "consultar la vigencia de una póliza ficticia",
                    "para": "conocer sus fechas de cobertura",
                    "criterios": [{
                        "dado": "una póliza ficticia vigente",
                        "cuando": "consulto su detalle",
                        "entonces": "veo las fechas de inicio y vencimiento",
                    }],
                }
        elif self.agent_id == AgentId.TECHNICAL_ADVISOR:
            data = {
                "affected_modules": [], "dependencies": [], "risks": [],
                "critical_processes": [], "uncertainties": ["Análisis sintético, sin afirmaciones técnicas."],
            }
        else:
            data = {
                "recommendation": "aclaracion",
                "comparison": [{
                    "approved_excerpt": "Consultar vigencia de póliza ficticia",
                    "request_excerpt": SYNTHETIC_CHANGE,
                    "explanation": "La fecha de vencimiento precisa la información mostrada.",
                }],
                "impact": ["Aclarar un dato mostrado en el resumen."],
                "rationale": "La solicitud delimita la fecha que debe presentar la consulta.",
                "uncertainties": [], "lessons_proposed": [],
            }
        return {"text": json.dumps(data, ensure_ascii=False), "time": {"created": 2}}


class SyntheticPinecone:
    """Empty retrieval result used in place of Pinecone in the isolated test."""

    def search(self, *, agent_role, query, namespace, limit):
        return RetrievalResult(
            status="degraded", backend="none", namespace=namespace,
            sources=[], error_code="PINECONE_UNAVAILABLE",
        )


def _create_app(repository: RepositorioHU, knowledge_retriever: SyntheticPinecone) -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(workflows.router, prefix="/api/workflows")
    app.state.workflow_runtime = WorkflowRuntime(
        observability=Observability(), repository=repository,
        knowledge_retriever=knowledge_retriever,
    )
    app.state.workflow_operation_guard = asyncio.Lock()
    app.state.workflow_active_operations = set()
    return app


@contextmanager
def _serve_http(app: FastAPI):
    """Serve a real loopback TCP endpoint so the test exercises HTTP serialization."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    host, port = listener.getsockname()
    server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False, lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.02)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=3)
        raise RuntimeError("Synthetic FastAPI server failed to start")
    try:
        with httpx.Client(base_url=f"http://{host}:{port}", timeout=10) as client:
            yield client
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()


def _resume(client: httpx.Client, snapshot: dict, decision: dict) -> httpx.Response:
    interrupt = snapshot["interrupt"]
    return client.post(
        f"/api/workflows/{snapshot['workflow_id']}/resume",
        json={"kind": interrupt["kind"], "interrupt_id": interrupt["interrupt_id"], "response": decision},
    )


def test_feature003_http_smoke_full_pre_post_grooming_sqlite(tmp_path, monkeypatch):
    """Exercise real workflow agents and HTTP; only OpenCode/Pinecone/TiDB boundaries are isolated."""
    import agentes.equipo.gestor_cambios.gestor_cambios_service as change_manager
    import agentes.equipo.analista.analista_service as orchestrator
    import agentes.equipo.redactor_revisor.redactor_revisor_service as redactor_revisor
    import agentes.equipo.asesor_tecnico.asesor_tecnico_service as technical_advisor

    SyntheticOpenCode.calls = []
    SyntheticOpenCode.fail_first_analyst_call = True
    for module in (change_manager, orchestrator, redactor_revisor, technical_advisor):
        monkeypatch.setattr(module, "OpenCodeClient", SyntheticOpenCode)

    repository = RepositorioHU(f"sqlite:///{(tmp_path / 'feature003-smoke.sqlite').as_posix()}")
    app = _create_app(repository, SyntheticPinecone())

    try:
        with _serve_http(app) as client:
            failed = client.post("/api/workflows", json={"mode": "pre_grooming", "requirement": SYNTHETIC_REQUEST})
            assert failed.status_code == 504
            assert "synthetic private timeout" not in failed.text
            assert repository.listar_hu() == []

            started = client.post("/api/workflows", json={"mode": "pre_grooming", "requirement": SYNTHETIC_REQUEST})
            assert started.status_code == 201, started.text
            business = started.json()
            assert business["mode"] == "pre_grooming"
            assert business["stage"] == "espera_negocio"
            assert business["interrupt"]["kind"] == "business_answers"
            assert business["interrupt"]["interrupt_id"]
            question_id = business["results"]["analyst"]["preguntas"][0]["question_id"]
            assert repository.listar_hu() == []

            stale = json.loads(json.dumps(business))
            stale["interrupt"]["interrupt_id"] = "stale-synthetic-interrupt"
            stale_response = _resume(client, stale, {"answers": [{"question_id": question_id, "answer": "2030-12-31"}]})
            assert stale_response.status_code == 409
            assert client.get(f"/api/workflows/{business['workflow_id']}").json()["stage"] == "espera_negocio"

            answered = _resume(client, business, {"answers": [{"question_id": question_id, "answer": "2030-12-31"}]})
            assert answered.status_code == 200, answered.text
            po = answered.json()
            assert po["stage"] == "aprobacion_po"
            assert po["interrupt"]["kind"] == "po_approval"
            assert po["results"]["story"]["criterios"]
            assert po["results"]["technical_assessment"]
            assert repository.listar_hu() == []  # agent output never writes before explicit PO approval

            approved_response = _resume(client, po, {"decision": "aprobar"})
            assert approved_response.status_code == 200, approved_response.text
            approved = approved_response.json()
            assert approved["status"] == "completed"
            assert approved["results"]["persistence_result"]["status"] == "saved"
            story_id = approved["results"]["persistence_result"]["story_id"]
            story = repository.obtener_hu(story_id)
            assert story["id"] == story_id
            assert repository.listar_hu()[0]["id"] == story_id

            rejected_start = client.post("/api/workflows", json={
                "mode": "post_grooming", "approved_story_id": story_id,
                "change_request": SYNTHETIC_CHANGE,
            })
            assert rejected_start.status_code == 201, rejected_start.text
            rejected_snapshot = rejected_start.json()
            assert rejected_snapshot["stage"] == "decision_humana"
            assert rejected_snapshot["interrupt"]["kind"] == "change_decision"
            assert rejected_snapshot["results"]["change_recommendation"]["recommendation"] == "aclaracion"
            assert repository.listar_cambios(story_id) == []
            rejected = _resume(client, rejected_snapshot, {"decision": "rechazar", "reason": "Decisión de rechazo sintética"})
            assert rejected.status_code == 200
            assert rejected.json()["results"]["change_persistence_result"]["status"] == "rejected"
            assert repository.listar_cambios(story_id) == []

            apply_start = client.post("/api/workflows", json={
                "mode": "post_grooming", "approved_story_id": story_id,
                "change_request": SYNTHETIC_CHANGE,
            })
            assert apply_start.status_code == 201, apply_start.text
            pending_apply = apply_start.json()
            assert repository.listar_cambios(story_id) == []
            applied_response = _resume(client, pending_apply, {"decision": "aplicar"})
            assert applied_response.status_code == 200, applied_response.text
            applied = applied_response.json()
            assert applied["results"]["change_persistence_result"]["status"] == "recorded"
            changes = repository.listar_cambios(story_id)
            assert len(changes) == 1
            assert changes[0]["solicitud"] == SYNTHETIC_CHANGE

            duplicate_resume = _resume(client, pending_apply, {"decision": "aplicar"})
            assert duplicate_resume.status_code == 409
            assert len(repository.listar_cambios(story_id)) == 1
            # The repository's idempotency key also protects a repeated authorized write.
            repository.registrar_cambio(
                hu_id=story_id, solicitud=SYNTHETIC_CHANGE, clasificacion="aclaracion",
                causa_raiz="", cambio_id=str(UUID(pending_apply["workflow_id"])),
            )
            assert len(repository.listar_cambios(story_id)) == 1
            assert {"analista", "redactor_revisor", "asesor_tecnico", "gestor_cambios"}.issubset(SyntheticOpenCode.calls)
    finally:
        repository.motor.dispose()

