"""Un flujo se guarda en la base de datos y se retoma en otro proceso (por ejemplo, al día siguiente)."""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentes.analista.api.errors import install_error_handlers
from agentes.analista.api.routes import workflows
from agentes.analista.core.conversation_store import ConversationStore
from agentes.analista.core.models import AgentTurnResponse, Analysis, Question, QuestionCategory, QuestionState
from agentes.analista.core.workflow_graph import WorkflowNotFoundError, WorkflowRuntime
from agentes.analista.core.workflow_models import FlowMode, WorkflowCreateRequest, WorkflowStage, WorkflowStatus
from agentes.analista.memory.repositorio import RepositorioHU

DECISION = "La carga masiva acepta «8888-8888» y la pantalla lo rechaza. ¿Cuál regla aplica en ambas?"


def _analyst_response(*, pending: bool) -> AgentTurnResponse:
    preguntas = [Question(
        question_id="q-formato", categoria=QuestionCategory.REQUIRED_DATA,
        pregunta="¿Qué formato tiene el teléfono?", estado=QuestionState.PENDING,
    )] if pending else []
    return AgentTurnResponse(
        conversation_id=uuid4(), request_id=uuid4(), turn_id=uuid4(), estado="completado",
        respuesta_markdown="Análisis del teléfono opcional.",
        analisis=Analysis(conocida=["El teléfono deja de ser obligatorio."],
                          faltante=["Formato del teléfono"] if pending else [], supuesta=[], ambigua=[]),
        preguntas=preguntas, fuentes_consultadas=[], listo_para_redactor=not pending,
        limitaciones=[], duracion_ms=1, prompt_version="1.0.0",
    )


class _Agentes:
    """Agentes simulados; el Asesor puede fallar una vez para probar el reintento."""

    def __init__(self, *, asesor_falla: int = 0) -> None:
        self.asesor_falla = asesor_falla
        self.estado_redactor: list[dict] = []

    async def analyst(self, state):
        return _analyst_response(pending=not state.get("latest_business_answers"))

    async def advisor(self, _state):
        if self.asesor_falla:
            self.asesor_falla -= 1
            raise ConnectionError("Asesor no disponible")
        return {
            "impacto_negocio": [{
                "area": "Carga masiva de clientes",
                "hoy": "Rechaza las filas que vienen sin teléfono.",
                "debe": "Aceptarlas, con las mismas reglas que la pantalla.",
            }],
            "decision_pendiente": [DECISION],
            "affected_modules": [], "dependencies": [], "risks": [], "critical_processes": [],
            "consulted_sources": [], "uncertainties": ["Evidencia simulada."],
        }

    async def draft(self, state):
        self.estado_redactor.append(dict(state))
        return {
            "como": "Como persona usuaria", "quiero": "registrar clientes sin teléfono", "para": "no perder registros",
            "criterios": [{"dado": "un cliente sin teléfono", "cuando": "guardo", "entonces": "se guarda"}],
        }

    async def review(self, _state):
        return {"requires_correction": False, "observations": []}


def _runtime(repositorio: RepositorioHU, agentes: _Agentes) -> WorkflowRuntime:
    return WorkflowRuntime(
        analyst=agentes.analyst, draft=agentes.draft, review=agentes.review, advisor=agentes.advisor,
        repository=repositorio, persistencia=repositorio,
    )


def _solicitud() -> WorkflowCreateRequest:
    return WorkflowCreateRequest(
        mode=FlowMode.PRE_GROOMING, requirement="El teléfono del cliente deja de ser obligatorio.",
        titulo="Teléfono opcional en Datos del cliente", creado_por="Analista de prueba",
        formulario={"sistema": "Portal de Clientes", "codigoHu": "CLI-TEL"},
    )


@pytest.fixture()
def repositorio(tmp_path):
    return RepositorioHU(tmp_path / "flujos.db")


@pytest.mark.asyncio
async def test_un_flujo_guardado_se_retoma_en_otro_proceso_hasta_la_aprobacion(repositorio):
    primero = _runtime(repositorio, _Agentes())
    negocio = await primero.execute(_solicitud())
    assert negocio.current_stage == WorkflowStage.BUSINESS_WAIT

    [guardado] = repositorio.listar_workflow()
    assert guardado["id"] == str(negocio.workflow_id)
    assert guardado["titulo"] == "Teléfono opcional en Datos del cliente"
    assert guardado["creado_por"] == "Analista de prueba"
    assert (guardado["estado"], guardado["espera"]) == ("esperando", "business_answers")

    # El Analista y el Asesor trabajan en equipo: una sola ronda con la pregunta y la decisión del impacto.
    payload = primero.pending_interrupt(negocio.workflow_id)["payload"]
    assert payload["kind"] == "business_answers"
    assert payload["impacto_negocio"][0]["area"] == "Carga masiva de clientes"
    assert [(item["question_id"], item["origen"]) for item in payload["questions"]] == [
        ("q-formato", "analista"), ("decision-1", "asesor_tecnico"),
    ]

    # El proceso se reinicia: un runtime nuevo, sin nada en memoria, lo recupera de la base de datos.
    agentes = _Agentes()
    segundo = _runtime(repositorio, agentes)
    assert segundo.get(negocio.workflow_id).current_stage == WorkflowStage.BUSINESS_WAIT
    assert segundo.metadatos(negocio.workflow_id)["formulario"] == {"sistema": "Portal de Clientes", "codigoHu": "CLI-TEL"}
    po = await segundo.resume(negocio.workflow_id, {"answers": [
        {"question_id": "q-formato", "answer": "8 dígitos"},
        {"question_id": "decision-1", "answer": "Solo números en ambas."},
    ]})

    assert po.current_stage == WorkflowStage.PO_APPROVAL
    assert po.impact_decisions[0].respuesta == "Solo números en ambas."
    assert po.draft_story.como == "persona usuaria"  # la plantilla ya dice «Como»
    assert agentes.estado_redactor[-1]["impact_decisions"][0]["pregunta"] == DECISION
    final = await _runtime(repositorio, agentes).resume(negocio.workflow_id, {"decision": "aprobar"})
    assert final.status == WorkflowStatus.COMPLETED
    assert repositorio.listar_workflow()[0]["estado"] == "completado"


@pytest.mark.asyncio
async def test_las_respuestas_sin_enviar_se_guardan_y_se_limpian_al_enviar(repositorio):
    runtime = _runtime(repositorio, _Agentes())
    negocio = await runtime.execute(_solicitud())

    runtime.guardar_borrador(negocio.workflow_id, {"q-formato": "Todavía lo consulto con Negocio"})

    otro = _runtime(repositorio, _Agentes())
    assert otro.metadatos(negocio.workflow_id)["borrador"] == {"q-formato": "Todavía lo consulto con Negocio"}
    await otro.resume(negocio.workflow_id, {"answers": [{"question_id": "q-formato", "answer": "8 dígitos"}]})
    assert repositorio.obtener_workflow(str(negocio.workflow_id))["borrador"] == {}


@pytest.mark.asyncio
async def test_un_paso_que_falla_queda_guardado_y_se_puede_reintentar(repositorio):
    agentes = _Agentes(asesor_falla=1)
    runtime = _runtime(repositorio, agentes)
    with pytest.raises(ConnectionError):
        await runtime.execute(_solicitud())

    [guardado] = repositorio.listar_workflow()
    assert guardado["estado"] == "error"
    otro = _runtime(repositorio, agentes)
    assert otro.metadatos(guardado["id"])["reintentable"] is True
    negocio = await otro.reintentar(guardado["id"])
    assert negocio.current_stage == WorkflowStage.BUSINESS_WAIT
    assert repositorio.listar_workflow()[0]["estado"] == "esperando"


@pytest.mark.asyncio
async def test_las_decisiones_sin_responder_vuelven_a_negocio_y_no_se_aceptan_ids_ajenos(repositorio):
    runtime = _runtime(repositorio, _Agentes())
    negocio = await runtime.execute(_solicitud())

    with pytest.raises(ValueError):
        await runtime.resume(negocio.workflow_id, {"answers": [{"question_id": "decision-9", "answer": "x"}]})
    # Si solo se responde la pregunta del Analista, la decisión del Asesor sigue pendiente para Negocio.
    pendiente = await runtime.resume(negocio.workflow_id, {"answers": [{"question_id": "q-formato", "answer": "8 dígitos"}]})
    assert pendiente.current_stage == WorkflowStage.BUSINESS_WAIT
    assert [item["question_id"] for item in runtime.pending_interrupt(negocio.workflow_id)["payload"]["questions"]] == ["decision-1"]
    # Con la decisión respondida se redacta sin volver a llamar al Analista.
    po = await runtime.resume(negocio.workflow_id, {"answers": [{"question_id": "decision-1", "answer": "Solo números."}]})
    assert po.current_stage == WorkflowStage.PO_APPROVAL


@pytest.mark.asyncio
async def test_descartar_elimina_el_flujo_guardado(repositorio):
    runtime = _runtime(repositorio, _Agentes())
    negocio = await runtime.execute(_solicitud())

    runtime.descartar(negocio.workflow_id)

    assert repositorio.listar_workflow() == []
    with pytest.raises(WorkflowNotFoundError):
        _runtime(repositorio, _Agentes()).get(negocio.workflow_id)


@pytest.mark.asyncio
async def test_la_conversacion_del_analista_se_restaura_con_el_ultimo_analisis():
    store = ConversationStore(prompt_version="1.0.0", prompt_hash="a" * 64)
    conversation = await store.create()
    respuesta = _analyst_response(pending=True)

    await store.restaurar(conversation.conversation_id, "El teléfono deja de ser obligatorio.", respuesta)

    record = await store.get(conversation.conversation_id)
    assert [item.question_id for item in record.questions] == ["q-formato"]
    assert record.analysis.faltante == ["Formato del teléfono"]
    assert record.context_turns[0].message == "El teléfono deja de ser obligatorio."
    assert "Formato del teléfono" in record.previous_summary


def test_la_api_lista_retoma_guarda_borrador_y_descarta(repositorio):
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(workflows.router, prefix="/api/workflows")
    app.state.workflow_runtime = _runtime(repositorio, _Agentes())
    app.state.workflow_operation_guard = asyncio.Lock()
    app.state.workflow_active_operations = set()

    with TestClient(app) as client:
        creado = client.post("/api/workflows", json={
            "mode": "pre_grooming", "requirement": "El teléfono del cliente deja de ser obligatorio.",
            "titulo": "Teléfono opcional", "creado_por": "Analista de prueba",
            "formulario": {"sistema": "Portal de Clientes"},
        })
        assert creado.status_code == 201, creado.text
        workflow_id = creado.json()["workflow_id"]
        assert creado.json()["guardado"]["persistente"] is True

        lista = client.get("/api/workflows").json()
        assert [(item["workflow_id"], item["titulo"], item["espera"]) for item in lista] == [
            (workflow_id, "Teléfono opcional", "business_answers"),
        ]
        assert "hilo" not in client.get("/api/workflows").text

        guardar = client.put(f"/api/workflows/{workflow_id}/borrador", json={"respuestas": {"q-formato": "Pendiente"}})
        assert guardar.status_code == 204

        # Otro proceso (el servicio se reinició) retoma el flujo con el formulario y el borrador.
        app.state.workflow_runtime = _runtime(repositorio, _Agentes())
        retomado = client.get(f"/api/workflows/{workflow_id}").json()
        assert retomado["stage"] == "espera_negocio"
        assert retomado["interrupt"]["kind"] == "business_answers"
        assert retomado["guardado"]["formulario"] == {"sistema": "Portal de Clientes"}
        assert retomado["guardado"]["borrador_respuestas"] == {"q-formato": "Pendiente"}

        assert client.post(f"/api/workflows/{workflow_id}/reintentar").status_code == 409
        assert client.delete(f"/api/workflows/{workflow_id}").status_code == 204
        assert client.get("/api/workflows").json() == []
        assert client.get(f"/api/workflows/{workflow_id}").status_code == 404
