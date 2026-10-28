from types import SimpleNamespace

from agentes.analista.core.context_builder import build_context
from agentes.analista.core.models import Analysis, Question, QuestionCategory, QuestionState


def test_context_trims_oldest_turns_before_touching_current_message():
    turns = [
        SimpleNamespace(message=f"turn-{index}", response=SimpleNamespace(respuesta_markdown="x" * 4500))
        for index in range(6)
    ]
    record = SimpleNamespace(
        context_turns=turns,
        previous_summary="Previously confirmed: payment is due in 30 days.",
        analysis=None,
        questions=[],
        turns_count=6,
    )

    payload = build_context(record, "current request", [], [])

    assert payload.current_message == "current request"
    assert payload.previous_summary == "Previously confirmed: payment is due in 30 days."
    assert len(payload.model_dump_json()) <= 24_000
    assert payload.recent_turns[-1]["user"] == "turn-5"
    assert len(payload.recent_turns) < 6
    assert payload.current_state["context_was_trimmed"] is True


def test_oversized_state_and_tool_results_are_compacted_with_pending_questions_prioritized():
    pending = [
        Question(
            question_id=f"q-{index}",
            categoria=QuestionCategory.REQUIRED_DATA,
            pregunta=f"Question {index}: " + ("p" * 450),
            estado=QuestionState.PENDING,
        )
        for index in range(50)
    ]
    analysis = Analysis(
        conocida=["k" * 900 for _ in range(100)],
        faltante=["f" * 900 for _ in range(100)],
        supuesta=["s" * 900 for _ in range(100)],
        ambigua=["a" * 900 for _ in range(100)],
    )
    record = SimpleNamespace(
        context_turns=[], previous_summary="S" * 2000, analysis=analysis, questions=pending, turns_count=12
    )
    results = [
        {"nombre": f"tool-{tool}", "datos": [{"detail": "d" * 1000} for _ in range(5)]}
        for tool in range(4)
    ]

    payload = build_context(record, "😀" * 4000, results, ["warning"] * 10)

    assert payload.current_message == "😀" * 4000
    assert len(payload.previous_summary) < 2000
    assert len(payload.model_dump_json()) <= 24_000
    assert payload.current_state["context_was_trimmed"] is True
    assert payload.current_state["questions"]
    assert all(question["estado"] == "pendiente" for question in payload.current_state["questions"])
    assert len(payload.tool_results) == 4
