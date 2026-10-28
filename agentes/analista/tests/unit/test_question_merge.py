from uuid import uuid4

import pytest

from agentes.analista.core import orchestrator
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
