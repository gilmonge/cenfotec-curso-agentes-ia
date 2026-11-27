"""Bitácora de la HU aprobada: qué se guarda además de la historia y qué no."""
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text

from agentes.analista.core.models import AgentTurnResponse, Analysis
from agentes.analista.core.workflow_graph import WorkflowRuntime
from agentes.analista.core.workflow_models import FlowMode, WorkflowCreateRequest, WorkflowStage
from agentes.analista.memory.repositorio import RepositorioHU


def _analyst_response():
    return AgentTurnResponse(
        conversation_id=uuid4(), request_id=uuid4(), turn_id=uuid4(), estado="completado",
        respuesta_markdown="Análisis validado.",
        analisis=Analysis(conocida=["La fecha de nacimiento se muestra en Datos del cliente."],
                          faltante=[], supuesta=[], ambigua=[]),
        preguntas=[], fuentes_consultadas=[], listo_para_redactor=True,
        limitaciones=[], duracion_ms=1, prompt_version="1.0.0",
        beneficios=["Evitar errores al intercambiar la fecha con otros sistemas."],
    )


async def _draft(_state):
    return {
        "como": "Como persona usuaria del portal", "quiero": "ver la fecha como aaaa-mm-dd",
        "para": "evitar errores de conversión",
        "criterios": [{"dado": "que estoy en la pantalla Datos del cliente", "cuando": "guardo la fecha",
                       "entonces": "se muestra como 1990-04-25"}],
    }


async def _advisor(_state):
    return {
        "impacto_negocio": [{"area": "Carga masiva de clientes", "hoy": "Acepta día/mes/año.",
                             "debe": "Aceptar año-mes-día igual que la pantalla."}],
        "decision_pendiente": ["¿La carga masiva debe pedir año-mes-día?"],
        "uncertainties": ["Asesor simulado sin fuentes."],
    }


class _RepositoryDouble:
    def __init__(self):
        self.calls = []

    def guardar_hu(self, hu):
        self.calls.append(hu)
        return {"id": hu["id"], "titulo": hu["titulo"], "aprobada_en": "2026-11-26T00:00:00+00:00"}


async def _hasta_aprobacion(review):
    repository = _RepositoryDouble()

    async def analyst(_state):
        return _analyst_response()

    runtime = WorkflowRuntime(analyst=analyst, draft=_draft, review=review, advisor=_advisor, repository=repository)
    impacto = await runtime.execute(WorkflowCreateRequest(
        mode=FlowMode.PRE_GROOMING, requirement="Formato aaaa-mm-dd para la fecha de nacimiento",
    ))
    pausado = await runtime.resume(impacto.workflow_id, {"answers": [
        {"question_id": "decision-1", "answer": "Sí, igual que la pantalla."},
    ]})
    assert pausado.current_stage == WorkflowStage.PO_APPROVAL
    return runtime, pausado, repository


@pytest.mark.asyncio
async def test_el_redactor_no_repite_que_ni_como_al_inicio():
    async def review(_state):
        return {"requires_correction": False, "observations": ["Sin defectos."]}

    _, pausado, _ = await _hasta_aprobacion(review)

    assert pausado.draft_story.como == "persona usuaria del portal"
    assert pausado.draft_story.criterios[0].dado == "estoy en la pantalla Datos del cliente"


@pytest.mark.asyncio
async def test_la_hu_aprobada_guarda_lo_util_y_no_el_control_de_calidad():
    revisiones = []

    async def review(state):
        revisiones.append(state.get("devoluciones_po", []))
        ronda = len(revisiones)
        return {
            "requires_correction": False,
            "observations": [f"No detecté defectos en la pasada {ronda}."],
            "notas_hu": [
                {"tipo": "dependencia", "texto": "Servicio al Cliente avisará el nuevo formato."},
                {"tipo": "dependencia", "texto": "servicio al cliente avisará el nuevo formato."},
                {"tipo": "pendiente_tecnico", "texto": "Confirmar si la fecha aparece en otros reportes."},
            ],
            **({"atencion_devolucion": "Se quitó el criterio general."} if ronda > 1 else {}),
        }

    runtime, pausado, repository = await _hasta_aprobacion(review)
    devuelto = await runtime.resume(pausado.workflow_id, {
        "decision": "devolver_redactor", "reason": "Quitar el criterio general de otros lugares.",
    })

    # En pantalla solo la última ronda; las notas se reemplazan por las de la última revisión.
    assert devuelto.ultima_revision == ["No detecté defectos en la pasada 2."]
    assert [nota.tipo for nota in devuelto.notas_hu] == ["dependencia", "pendiente_tecnico"]
    assert devuelto.devoluciones_po[0].motivo == "Quitar el criterio general de otros lugares."
    assert devuelto.devoluciones_po[0].atencion == "Se quitó el criterio general."

    await runtime.resume(pausado.workflow_id, {"decision": "aprobar", "reason": "Revisar con Desarrollo."})

    seguimiento = repository.calls[0]["seguimiento"]
    assert seguimiento["beneficios"] == ["Evitar errores al intercambiar la fecha con otros sistemas."]
    assert "impacto_negocio" not in seguimiento
    assert seguimiento["decisiones_impacto"] == [
        {"pregunta": "¿La carga masiva debe pedir año-mes-día?", "respuesta": "Sí, igual que la pantalla."},
    ]
    assert len(seguimiento["notas"]) == 2
    assert seguimiento["devoluciones_po"][0]["destino"] == "redactor"
    assert seguimiento["nota_aprobacion"] == "Revisar con Desarrollo."
    assert "No detecté defectos" not in str(seguimiento)


def test_el_repositorio_agrega_la_columna_de_seguimiento_a_una_tabla_existente(tmp_path):
    ruta = tmp_path / "anterior.db"
    motor = create_engine(f"sqlite:///{ruta}")
    with motor.begin() as conexion:
        conexion.execute(text(
            "CREATE TABLE hu_aprobada (id VARCHAR(36) PRIMARY KEY, codigo VARCHAR(60), titulo VARCHAR(200) NOT NULL, "
            "tipo_informacion VARCHAR(60) NOT NULL, requerimiento TEXT NOT NULL, historia TEXT NOT NULL, "
            "criterios TEXT NOT NULL, aclaraciones TEXT NOT NULL, aprobada_en VARCHAR(40) NOT NULL)"
        ))
    motor.dispose()

    repositorio = RepositorioHU(f"sqlite:///{ruta}")
    columnas = {columna["name"] for columna in inspect(repositorio.motor).get_columns("hu_aprobada")}
    assert "seguimiento" in columnas

    hu_id = str(uuid4())
    repositorio.guardar_hu({
        "id": hu_id, "titulo": "Fecha", "tipo_informacion": "Historia de Usuario", "requerimiento": "Fecha",
        "historia": {}, "criterios": [], "aclaraciones": [],
        "seguimiento": {"notas": [{"tipo": "dependencia", "texto": "Avisar."}]},
    })
    assert "Avisar." in repositorio.obtener_hu(hu_id)["seguimiento"]
