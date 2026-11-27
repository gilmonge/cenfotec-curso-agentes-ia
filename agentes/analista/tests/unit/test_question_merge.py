from uuid import uuid4

import pytest

from agentes.equipo.analista import analista_service as orchestrator
from agentes.analista.core.models import Question, QuestionCategory, QuestionState
from agentes.analista.core.output_parser import AgentOutput, AgentQuestionOutput


def test_question_merge_preserves_ids_answered_state_and_omitted_pending_questions():
    conversation_id, request_id, turn_id = uuid4(), uuid4(), uuid4()
    first_turn, second_turn = uuid4(), uuid4()
    pending = Question(
        question_id="pending-1",
        categoria=QuestionCategory.BUSINESS_RULES,
        pregunta="What is the delivery deadline?",
        estado=QuestionState.PENDING,
        created_turn_id=first_turn,
    )
    answered = Question(
        question_id="answered-1",
        categoria=QuestionCategory.BUSINESS_RULES,
        pregunta="Which support channel is used?",
        estado=QuestionState.ANSWERED,
        created_turn_id=first_turn,
        updated_turn_id=second_turn,
    )
    historical = Question(
        question_id="historical-1",
        categoria=QuestionCategory.REQUIRED_DATA,
        pregunta="Which identifier was previously confirmed?",
        estado=QuestionState.ANSWERED,
        created_turn_id=first_turn,
        updated_turn_id=second_turn,
    )
    output = AgentOutput(
        respuesta_markdown="The deadline is still open.",
        analisis={"conocida": [], "faltante": [], "supuesta": [], "ambigua": []},
        preguntas=[
            AgentQuestionOutput(
                categoria=QuestionCategory.BUSINESS_RULES,
                pregunta="WHICH SUPPORT   CHANNEL IS USED?",
                estado=QuestionState.PENDING,
            ),
            AgentQuestionOutput(
                categoria=QuestionCategory.VALIDATIONS,
                pregunta="Which report format is required?",
                estado=QuestionState.PENDING,
            ),
        ],
        listo_para_redactor=True,
    )

    response = orchestrator._to_response(
        output,
        conversation_id=conversation_id,
        request_id=request_id,
        turn_id=turn_id,
        prior_questions=[pending, answered, historical],
        tool_executions=[],
        limitations=[],
        duration_ms=5,
    )

    by_id = {item.question_id: item for item in response.preguntas}
    assert by_id["pending-1"].estado == QuestionState.PENDING
    assert by_id["pending-1"].created_turn_id == first_turn
    assert by_id["answered-1"].estado == QuestionState.ANSWERED
    assert by_id["answered-1"].updated_turn_id == turn_id
    assert by_id["answered-1"].pregunta == "WHICH SUPPORT   CHANNEL IS USED?"
    assert by_id["historical-1"].estado == QuestionState.ANSWERED
    assert response.listo_para_redactor is False
    assert len(response.preguntas) == 4


def test_question_merge_rejects_overflow_instead_of_silently_dropping_items():
    existing = [
        Question(
            question_id=f"pending-{index}",
            categoria=QuestionCategory.BUSINESS_RULES,
            pregunta=f"Existing question number {index}?",
            estado=QuestionState.PENDING,
            created_turn_id=uuid4(),
        )
        for index in range(50)
    ]
    output = AgentOutput(
        respuesta_markdown="A new question was identified.",
        analisis={"conocida": [], "faltante": [], "supuesta": [], "ambigua": []},
        preguntas=[AgentQuestionOutput(
            categoria=QuestionCategory.VALIDATIONS,
            pregunta="One additional unique question?",
        )],
        listo_para_redactor=False,
    )

    with pytest.raises(orchestrator.OrchestrationError) as raised:
        orchestrator._to_response(
            output,
            conversation_id=uuid4(),
            request_id=uuid4(),
            turn_id=uuid4(),
            prior_questions=existing,
            tool_executions=[],
            limitations=[],
            duration_ms=5,
        )

    assert raised.value.code.value == "AGENT_OUTPUT_INVALID"


@pytest.fixture(autouse=True)
def _sin_similitud(monkeypatch):
    monkeypatch.setattr(orchestrator, "_similitud_vacio", lambda punto, referencia: None)


def _respuesta_con_vacio(prior_questions, respondidas=None, *, faltante=None, supuesta=None, vinculos=None):
    output = AgentOutput(
        respuesta_markdown="Quedan vacíos.",
        analisis={
            "conocida": ["El cliente tiene teléfono"],
            "faltante": ["Formato del teléfono"] if faltante is None else faltante,
            "supuesta": ["El teléfono es de Costa Rica"] if supuesta is None else supuesta,
            "ambigua": [],
        },
        preguntas=[],
        listo_para_redactor=False,
        vinculos=vinculos or [],
    )
    return orchestrator._to_response(
        output,
        conversation_id=uuid4(),
        request_id=uuid4(),
        turn_id=uuid4(),
        prior_questions=prior_questions,
        tool_executions=[],
        limitations=[],
        duration_ms=5,
        respondidas=respondidas,
    )


def test_vacio_sin_pregunta_se_convierte_en_pregunta_pendiente_para_negocio():
    response = _respuesta_con_vacio([])

    pendiente = [item for item in response.preguntas if item.estado == QuestionState.PENDING]
    assert [item.categoria for item in pendiente] == [QuestionCategory.REQUIRED_DATA, QuestionCategory.BUSINESS_RULES]
    assert all(item.question_id.startswith("vacio-") for item in pendiente)
    assert "«Formato del teléfono»" in pendiente[0].pregunta
    assert response.analisis.faltante == ["Formato del teléfono"]
    assert response.supuesto_validar_po == []
    assert response.listo_para_redactor is False


def test_vacio_ya_respondido_pasa_a_conocida_y_el_flujo_puede_avanzar():
    prior = _respuesta_con_vacio([]).preguntas

    response = _respuesta_con_vacio(prior, respondidas=[item.question_id for item in prior])

    assert all(item.estado == QuestionState.ANSWERED for item in response.preguntas)
    assert response.analisis.faltante == [] and response.analisis.supuesta == []
    assert "Formato del teléfono (confirmado por Negocio)" in response.analisis.conocida
    assert response.listo_para_redactor is True


def _respondida(question_id, pregunta, turno):
    return Question(question_id=question_id, categoria=QuestionCategory.REQUIRED_DATA, pregunta=pregunta,
                    estado=QuestionState.ANSWERED, created_turn_id=turno)


def test_vinculo_por_id_confirma_un_punto_aunque_el_analista_lo_redacte_distinto():
    prior = [_respondida("q-formato", "¿Qué formato tiene el teléfono?", uuid4())]
    vinculo = [{"punto": "Cantidad de dígitos del número telefónico", "question_id": "q-formato"}]

    response = _respuesta_con_vacio(prior, faltante=["Cantidad de dígitos del número telefónico"], supuesta=[],
                                    vinculos=vinculo)

    assert response.analisis.faltante == []
    assert "Cantidad de dígitos del número telefónico (confirmado por Negocio)" in response.analisis.conocida
    assert response.listo_para_redactor is True


def test_vinculo_a_una_pregunta_inexistente_o_sin_respuesta_se_ignora():
    pendiente = Question(question_id="q-abierta", categoria=QuestionCategory.REQUIRED_DATA,
                         pregunta="¿Aplica a póliza madre?", estado=QuestionState.PENDING, created_turn_id=uuid4())
    vinculo = [{"punto": "Formato del teléfono", "question_id": "q-abierta"},
               {"punto": "El teléfono es de Costa Rica", "question_id": "q-inventada"}]

    response = _respuesta_con_vacio([pendiente], vinculos=vinculo)

    assert response.analisis.faltante == ["Formato del teléfono"]
    assert response.analisis.supuesta == ["El teléfono es de Costa Rica"]
    assert response.listo_para_redactor is False


def test_vacio_parecido_a_una_respuesta_no_se_repregunta_y_va_al_po(monkeypatch):
    monkeypatch.setattr(orchestrator, "_similitud_vacio", lambda punto, referencia: [0.95, 0.2])
    prior = [_respondida(f"vacio-{uuid4()}", "Falta definir: «Formato del teléfono». ¿Cuál es la regla?", uuid4())]

    response = _respuesta_con_vacio(prior, faltante=["Cuántos dígitos lleva el teléfono"])

    assert response.supuesto_validar_po == ["Falta definir: Cuántos dígitos lleva el teléfono"]
    assert response.analisis.faltante == []
    assert response.analisis.supuesta == ["El teléfono es de Costa Rica"]
    nueva = [item for item in response.preguntas if item.estado == QuestionState.PENDING]
    assert len(nueva) == 1 and "Costa Rica" in nueva[0].pregunta


def test_sin_similitud_solo_hay_una_ronda_automatica_y_lo_demas_va_al_po():
    prior = [_respondida(f"vacio-{uuid4()}", "Falta definir: «Otro tema». ¿Cuál es la regla?", uuid4())]

    response = _respuesta_con_vacio(prior)

    assert not [item for item in response.preguntas if item.estado == QuestionState.PENDING]
    assert response.supuesto_validar_po == [
        "Falta definir: Formato del teléfono", "Se supone: El teléfono es de Costa Rica",
    ]
    assert response.listo_para_redactor is True


def test_con_similitud_baja_se_permite_una_segunda_ronda_y_no_una_tercera(monkeypatch):
    monkeypatch.setattr(orchestrator, "_similitud_vacio", lambda punto, referencia: [0.1] * len(punto))
    una_ronda = [_respondida(f"vacio-{uuid4()}", "Falta definir: «Otro tema». ¿Cuál es la regla?", uuid4())]
    dos_ronda = [*una_ronda, _respondida(f"vacio-{uuid4()}", "Falta definir: «Tema dos». ¿Cuál?", uuid4())]

    segunda = _respuesta_con_vacio(una_ronda, supuesta=[])
    tercera = _respuesta_con_vacio(dos_ronda, supuesta=[])

    assert [item.estado for item in segunda.preguntas].count(QuestionState.PENDING) == 1
    assert segunda.supuesto_validar_po == []
    assert tercera.supuesto_validar_po == ["Falta definir: Formato del teléfono"]
    assert tercera.listo_para_redactor is True


def test_lo_que_es_del_asesor_no_se_le_pregunta_a_negocio(monkeypatch):
    """Trabajo en equipo: lo que solo se sabe revisando el sistema pasa al Asesor, no a Negocio."""
    monkeypatch.setattr(orchestrator, "_similitud_vacio", lambda *_: None)
    output = AgentOutput(
        respuesta_markdown="Análisis.",
        analisis={
            "conocida": ["La fecha se muestra en Datos del cliente."],
            "faltante": [
                "Inventario de lugares donde aparece la fecha: corresponde al Asesor Técnico.",
                "Lugares del portal donde se muestra la fecha",
                "Mensaje si la fecha no existe",
            ],
            "supuesta": [], "ambigua": [],
        },
        preguntas=[
            {"categoria": "Reglas de negocio", "pregunta": "¿Qué mensaje ve la persona si la fecha no existe?", "estado": "pendiente"},
            {"categoria": "Reglas de negocio", "pregunta": "¿Dónde más aparece la fecha? Lo debe revisar el Asesor Técnico.", "estado": "pendiente"},
        ],
        listo_para_redactor=False,
        para_asesor=["Lugares del portal donde se muestra la fecha"],
    )
    response = orchestrator._to_response(
        output, conversation_id=uuid4(), request_id=uuid4(), turn_id=uuid4(),
        prior_questions=[], tool_executions=[], limitations=[], duration_ms=5,
    )

    assert [item.pregunta for item in response.preguntas] == ["¿Qué mensaje ve la persona si la fecha no existe?"]
    assert response.analisis.faltante == ["Mensaje si la fecha no existe"]
    assert len(response.para_asesor) == 3
    assert "Lugares del portal donde se muestra la fecha" in response.para_asesor
