from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentes.analista.api.errors import install_error_handlers
from agentes.analista.api.routes import workflows
from agentes.analista.core.models import (
    AgentTurnResponse,
    Analysis,
    ErrorCode,
    Question,
    QuestionCategory,
    QuestionState,
)
from agentes.analista.core.observability import Observability
from agentes.analista.core.opencode_client import OpenCodeClientError
from agentes.analista.core.workflow_graph import WorkflowRuntime
from agentes.analista.core.workflow_models import FlowMode, WorkflowCreateRequest


APPROVED_STORY_ID = "HU-API-001"


class OpenCodeDouble:
    def __init__(self):
        self.calls: list[str] = []

    async def run(self, agent: str) -> None:
        self.calls.append(agent)


class MCPDouble:
    def __init__(self):
        self.calls = 0

    async def inspect(self):
        self.calls += 1
        return {"source": "fake://technical-evidence"}


class RepositoryDouble:
    def __init__(self, *, lookup_error: Exception | None = None):
        self.saved_stories: list[dict] = []
        self.registered_changes: list[dict] = []
        self.lesson_decisions: list[tuple[str, str]] = []
        self.lookup_error = lookup_error

    def obtener_hu(self, story_id: str):
        if self.lookup_error:
            raise self.lookup_error
        if story_id != APPROVED_STORY_ID:
            raise ValueError("not found")
        return {
            "id": story_id,
            "titulo": "Consulta de pólizas",
            "tipo_informacion": "Historia de Usuario",
            "requerimiento": "Consultar pólizas vigentes",
            "historia": {"asA": "persona", "iWant": "consultar pólizas", "soThat": "ver vigencia"},
            "criterios": [{"dado": "una póliza", "cuando": "consulto", "entonces": "veo vigencia"}],
            "aclaraciones": [],
            "aprobada_en": "2026-11-21T00:00:00Z",
        }

    def guardar_hu(self, story: dict):
        self.saved_stories.append(story)
        return {"id": story["id"], "titulo": story["titulo"], "aprobada_en": "2026-11-21T00:00:00Z"}

    def registrar_cambio(self, **kwargs):
        self.registered_changes.append(kwargs)
        return {"solicitud_id": "change-1", "leccion_ids": []}

    def decidir_leccion(self, lesson_id: str, decision: str):
        self.lesson_decisions.append((lesson_id, decision))


def _analyst_response(state, *, pending: bool) -> AgentTurnResponse:
    has_answer = bool(state.get("latest_business_answers"))
    needs_question = pending and not has_answer
    return AgentTurnResponse(
        conversation_id=uuid4(),
        request_id=state["request_id"],
        turn_id=uuid4(),
        estado="completado",
        respuesta_markdown="Análisis simulado para el contrato API.",
        analisis=Analysis(
            conocida=["La solicitud se recibió."],
            faltante=["Plazo"] if needs_question else [],
            supuesta=[],
            ambigua=[],
        ),
        preguntas=[
            Question(
                question_id="q-plazo",
                categoria=QuestionCategory.REQUIRED_DATA,
                pregunta="¿Cuál es el plazo?",
                estado=QuestionState.PENDING,
            )
        ] if needs_question else [],
        fuentes_consultadas=[],
        listo_para_redactor=not needs_question,
        supuesto_validar_po=["Se supone: el plazo se cuenta en días naturales"] if has_answer else [],
        limitaciones=[],
        duracion_ms=1,
        prompt_version="1.0.0",
    )


def _runtime(
    *,
    pending_business: bool = False,
    analyst_error: Exception | None = None,
    advisor_error: Exception | None = None,
    repository_error: Exception | None = None,
):
    opencode = OpenCodeDouble()
    mcp = MCPDouble()
    repository = RepositoryDouble(lookup_error=repository_error)

    async def analyst(state):
        await opencode.run("analista")
        if analyst_error:
            raise analyst_error
        return _analyst_response(state, pending=pending_business)

    async def draft(_state):
        await opencode.run("redactor_revisor")
        return {
            "como": "persona usuaria",
            "quiero": "consultar pólizas",
            "para": "conocer su vigencia",
            "criterios": [{"dado": "una póliza vigente", "cuando": "la consulto", "entonces": "veo sus fechas"}],
        }

    async def review(_state):
        await opencode.run("redactor_revisor")
        return {"requires_correction": False, "observations": []}

    async def advisor(_state):
        if advisor_error:
            raise advisor_error
        await mcp.inspect()
        return {
            "affected_modules": [],
            "dependencies": [],
            "risks": [],
            "critical_processes": [],
            "consulted_sources": [],
            "uncertainties": ["Evidencia técnica simulada."],
        }

    async def change_manager(state, repo):
        await opencode.run("gestor_cambios")
        approved = repo.obtener_hu(state["approved_story_id"])
        return {
            "recommendation": "aclaracion",
            "comparison": [{
                "approved_excerpt": approved["requerimiento"],
                "request_excerpt": state["change_request"],
                "explanation": "Comparación simulada y verificable.",
            }],
            "impact": ["Ajuste de una aclaración."],
            "rationale": "La solicitud precisa el comportamiento esperado.",
            "uncertainties": [],
            "lessons_proposed": [],
        }

    runtime = WorkflowRuntime(
        observability=Observability(),
        analyst=analyst,
        draft=draft,
        review=review,
        advisor=advisor,
        change_manager=change_manager,
        repository=repository,
    )
    return runtime, repository, opencode, mcp


def _client(runtime: WorkflowRuntime) -> TestClient:
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(workflows.router, prefix="/api/workflows")
    app.state.workflow_runtime = runtime
    app.state.workflow_operation_guard = asyncio.Lock()
    app.state.workflow_active_operations = set()
    return TestClient(app)


def _start_pre(client: TestClient):
    return client.post(
        "/api/workflows",
        json={"mode": "pre_grooming", "requirement": "Consultar vigencia de una póliza"},
    )


def _resume(client: TestClient, workflow_id: str, interrupt: dict, response: dict):
    return client.post(
        f"/api/workflows/{workflow_id}/resume",
        json={"kind": interrupt["kind"], "interrupt_id": interrupt["interrupt_id"], "response": response},
    )


def test_api_starts_pre_and_post_and_returns_status_results_and_real_interrupt_ids():
    runtime, repository, _opencode, mcp = _runtime(pending_business=True)
    with _client(runtime) as client:
        pre = _start_pre(client)
        assert pre.status_code == 201
        pre_body = pre.json()
        assert pre_body["mode"] == "pre_grooming"
        assert pre_body["status"] == "interrupted"
        assert pre_body["stage"] == "espera_negocio"
        assert pre_body["results"]["analyst"]["preguntas"][0]["question_id"] == "q-plazo"
        assert pre_body["interrupt"]["kind"] == "business_answers"
        assert pre_body["interrupt"]["interrupt_id"]
        assert "thread_id" not in pre.text

        current = client.get(f"/api/workflows/{pre_body['workflow_id']}")
        assert current.status_code == 200
        assert current.json()["status"] == "interrupted"
        assert current.json()["interrupt"]["interrupt_id"] == pre_body["interrupt"]["interrupt_id"]

        # Una sola ronda: al responder a Negocio (sin decisiones del Asesor) se redacta y llega al PO.
        resumed = _resume(client, pre_body["workflow_id"], pre_body["interrupt"], {
            "answers": [{"question_id": "q-plazo", "answer": "30 días"}],
        })
        assert resumed.status_code == 200, resumed.text
        assert resumed.json()["stage"] == "aprobacion_po"
        # La aprobación del PO no expone el detalle técnico del Asesor.
        assert resumed.json()["interrupt"]["payload"].get("technical_assessment") is None
        assert resumed.json()["interrupt"]["kind"] == "po_approval"
        assert resumed.json()["interrupt"]["payload"]["supuesto_validar_po"] == [
            "Se supone: el plazo se cuenta en días naturales",
        ]
        assert mcp.calls == 1
        assert repository.saved_stories == []

        post = client.post("/api/workflows", json={
            "mode": "post_grooming",
            "approved_story_id": APPROVED_STORY_ID,
            "change_request": "Precisar la fecha final de vigencia",
        })
        assert post.status_code == 201, post.text
        post_body = post.json()
        assert post_body["mode"] == "post_grooming"
        assert post_body["stage"] == "decision_humana"
        assert post_body["interrupt"]["kind"] == "change_decision"
        assert post_body["results"]["change_recommendation"]["recommendation"] == "aclaracion"
        assert repository.registered_changes == []


def test_api_answers_business_questions_and_po_can_approve_or_return_without_model_approval():
    runtime, repository, _opencode, _mcp = _runtime(pending_business=True)
    with _client(runtime) as client:
        started = _start_pre(client).json()
        business = _resume(client, started["workflow_id"], started["interrupt"], {
            "answers": [{"question_id": "q-plazo", "answer": "30 días"}],
        }).json()
        approval_interrupt = business["interrupt"]
        assert "approval" not in business["results"]["story"]
        assert repository.saved_stories == []

        returned = _resume(client, business["workflow_id"], approval_interrupt, {
            "decision": "devolver_redactor", "reason": "Ajustar el criterio de aceptación",
        })
        assert returned.status_code == 200
        assert returned.json()["stage"] == "aprobacion_po"
        assert repository.saved_stories == []

        approve_interrupt = returned.json()["interrupt"]
        approved = _resume(client, business["workflow_id"], approve_interrupt, {"decision": "aprobar"})
        assert approved.status_code == 200
        assert approved.json()["status"] == "completed"
        assert approved.json()["results"]["persistence_result"]["status"] == "saved"
        assert len(repository.saved_stories) == 1


def test_api_can_apply_or_reject_change_only_after_human_decision():
    runtime, repository, _opencode, _mcp = _runtime()
    with _client(runtime) as client:
        rejected_start = client.post("/api/workflows", json={
            "mode": "post_grooming", "approved_story_id": APPROVED_STORY_ID,
            "change_request": "Precisar la fecha final de vigencia",
        }).json()
        assert repository.registered_changes == []
        rejected = _resume(client, rejected_start["workflow_id"], rejected_start["interrupt"], {
            "decision": "rechazar", "reason": "No se requiere este ajuste",
        })
        assert rejected.status_code == 200
        assert rejected.json()["results"]["change_persistence_result"]["status"] == "rejected"
        assert repository.registered_changes == []

        apply_start = client.post("/api/workflows", json={
            "mode": "post_grooming", "approved_story_id": APPROVED_STORY_ID,
            "change_request": "Precisar la fecha final de vigencia",
        }).json()
        applied = _resume(client, apply_start["workflow_id"], apply_start["interrupt"], {
            "decision": "aplicar",
        })
        assert applied.status_code == 200
        assert applied.json()["results"]["change_persistence_result"]["status"] == "recorded"
        assert len(repository.registered_changes) == 1


def test_api_rejects_invalid_bodies_unknown_fields_and_excessive_text():
    runtime, _repository, _opencode, _mcp = _runtime()
    with _client(runtime) as client:
        too_long = client.post("/api/workflows", json={
            "mode": "pre_grooming", "requirement": "x" * 4001,
        })
        assert too_long.status_code == 422
        assert too_long.json()["error"]["code"] == ErrorCode.INVALID_REQUEST

        unknown = client.post("/api/workflows", json={
            "mode": "pre_grooming", "requirement": "Solicitar una función", "prompt": "secret",
        })
        assert unknown.status_code == 422

        post_too_long = client.post("/api/workflows", json={
            "mode": "post_grooming", "approved_story_id": APPROVED_STORY_ID,
            "change_request": "x" * 2001,
        })
        assert post_too_long.status_code == 422

        started = _start_pre(client).json()
        bad_resume = _resume(client, started["workflow_id"], started["interrupt"], {
            "decision": "aprobar", "unexpected": True,
        })
        assert bad_resume.status_code == 422

    pending_runtime, _repository, _opencode, _mcp = _runtime(pending_business=True)
    with _client(pending_runtime) as client:
        pending = _start_pre(client).json()
        too_long_answer = _resume(client, pending["workflow_id"], pending["interrupt"], {
            "answers": [{"question_id": "q-plazo", "answer": "x" * 1001}],
        })
        assert too_long_answer.status_code == 422


def test_api_rejects_wrong_or_duplicate_resume_and_concurrent_operation():
    runtime, _repository, _opencode, _mcp = _runtime(pending_business=True)
    with _client(runtime) as client:
        started = _start_pre(client).json()
        wrong_id = dict(started["interrupt"], interrupt_id="stale-id")
        rejected = _resume(client, started["workflow_id"], wrong_id, {
            "answers": [{"question_id": "q-plazo", "answer": "30 días"}],
        })
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == ErrorCode.WORKFLOW_NOT_WAITING
        assert client.get(f"/api/workflows/{started['workflow_id']}").json()["stage"] == "espera_negocio"

        entered_resume = threading.Event()
        release_resume = threading.Event()
        real_resume = runtime.resume

        async def slow_resume(workflow_id, submission):
            entered_resume.set()
            await asyncio.to_thread(release_resume.wait, 5)
            return await real_resume(workflow_id, submission)

        runtime.resume = slow_resume
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(_resume, client, started["workflow_id"], started["interrupt"], {
                "answers": [{"question_id": "q-plazo", "answer": "30 días"}],
            })
            assert entered_resume.wait(5)
            concurrent = _resume(client, started["workflow_id"], started["interrupt"], {
                "answers": [{"question_id": "q-plazo", "answer": "30 días"}],
            })
            release_resume.set()
            resumed = first.result(timeout=10)

        assert concurrent.status_code == 409
        assert resumed.status_code == 200
        duplicate = _resume(client, started["workflow_id"], started["interrupt"], {
            "answers": [{"question_id": "q-plazo", "answer": "30 días"}],
        })
        assert duplicate.status_code == 409


def test_api_returns_not_found_after_checkpoint_is_lost_or_process_restarts():
    first, _repository, _opencode, _mcp = _runtime()
    with _client(first) as client:
        started = client.post("/api/workflows", json={
            "mode": "pre_grooming", "requirement": "Consulta breve",
        }).json()
    second, _repository, _opencode, _mcp = _runtime()
    with _client(second) as client:
        missing = client.get(f"/api/workflows/{started['workflow_id']}")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == ErrorCode.WORKFLOW_NOT_FOUND
        assert "traceback" not in missing.text.lower()


def test_api_sanitizes_timeout_and_dependency_failures():
    timeout_runtime, _repository, _opencode, _mcp = _runtime(analyst_error=TimeoutError("secret timeout detail"))
    with _client(timeout_runtime) as client:
        timeout = _start_pre(client)
        assert timeout.status_code == 504
        assert timeout.json()["error"]["code"] == ErrorCode.WORKFLOW_TIMEOUT
        assert "secret timeout" not in timeout.text

    dependency_runtime, _repository, _opencode, _mcp = _runtime(
        analyst_error=OpenCodeClientError("OPENCODE_UNAVAILABLE", "private credential detail", retryable=True)
    )
    with _client(dependency_runtime) as client:
        unavailable = _start_pre(client)
        assert unavailable.status_code == 503
        assert unavailable.json()["error"]["code"] == ErrorCode.DEPENDENCY_UNAVAILABLE
        assert "private credential" not in unavailable.text

    opencode_timeout_runtime, _repository, _opencode, _mcp = _runtime(
        analyst_error=OpenCodeClientError("TURN_TIMEOUT", "private timeout detail", retryable=True)
    )
    with _client(opencode_timeout_runtime) as client:
        opencode_timeout = _start_pre(client)
        assert opencode_timeout.status_code == 504
        assert opencode_timeout.json()["error"]["code"] == ErrorCode.WORKFLOW_TIMEOUT
        assert "private timeout" not in opencode_timeout.text

    mcp_runtime, repository, _opencode, _mcp = _runtime(advisor_error=ConnectionError("private MCP endpoint"))
    with _client(mcp_runtime) as client:
        mcp_failure = _start_pre(client)
        assert mcp_failure.status_code == 503
        assert mcp_failure.json()["error"]["code"] == ErrorCode.DEPENDENCY_UNAVAILABLE
        assert "private MCP endpoint" not in mcp_failure.text
        assert repository.saved_stories == []

    repository_runtime, _repository, _opencode, _mcp = _runtime(repository_error=OSError("private database host"))
    with _client(repository_runtime) as client:
        repository_failure = client.post("/api/workflows", json={
            "mode": "post_grooming", "approved_story_id": APPROVED_STORY_ID,
            "change_request": "Precisar una fecha",
        })
        assert repository_failure.status_code == 503
        assert repository_failure.json()["error"]["code"] == ErrorCode.DEPENDENCY_UNAVAILABLE
        assert "private database host" not in repository_failure.text


def test_api_uses_shared_runtime_and_does_not_expose_internal_prompt_or_thread_data():
    runtime, _repository, _opencode, _mcp = _runtime()
    with _client(runtime) as client:
        started = _start_pre(client)
        workflow_id = started.json()["workflow_id"]
        fetched = client.get(f"/api/workflows/{workflow_id}")
        assert fetched.status_code == 200
        assert runtime.active_thread_count == 1
        assert "thread_id" not in fetched.text
        assert '"prompt":' not in fetched.text.lower()
