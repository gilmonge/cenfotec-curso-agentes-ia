from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agentes.analista.core.models import (
    AgentTurnResponse,
    Analysis,
    CheckStatus,
    ContextPayload,
    HealthChecks,
    HealthResponse,
    HealthStatus,
    LangfuseCheck,
    McpCheck,
    OpenCodeCheck,
    Question,
    QuestionCategory,
    QuestionState,
    SendMessageRequest,
    ToolName,
)


def valid_response(**overrides):
    response = {
        "conversation_id": uuid4(),
        "request_id": uuid4(),
        "turn_id": uuid4(),
        "estado": "completado",
        "respuesta_markdown": "Análisis realizado.",
        "analisis": {"conocida": ["Dato confirmado"], "faltante": [], "supuesta": [], "ambigua": []},
        "preguntas": [],
        "fuentes_consultadas": [],
        "listo_para_redactor": True,
        "limitaciones": [],
        "duracion_ms": 10,
        "prompt_version": "1.0.0",
    }
    response.update(overrides)
    return response


def test_send_message_accepts_4000_unicode_codepoints_and_rejects_whitespace():
    request = SendMessageRequest(request_id=uuid4(), message="😀" * 4000)
    assert len(request.message) == 4000
    with pytest.raises(ValidationError):
        SendMessageRequest(request_id=uuid4(), message=" " * 4000)
    with pytest.raises(ValidationError):
        SendMessageRequest(request_id=uuid4(), message="😀" * 4001)


def test_analysis_requires_all_four_lists_and_applies_item_limits():
    with pytest.raises(ValidationError):
        Analysis(conocida=[], faltante=[], supuesta=[])
    with pytest.raises(ValidationError):
        Analysis(conocida=[" "], faltante=[], supuesta=[], ambigua=[])
    with pytest.raises(ValidationError):
        Analysis(conocida=["x" * 1001], faltante=[], supuesta=[], ambigua=[])
    assert Analysis(conocida=[], faltante=[], supuesta=[], ambigua=[]).ambigua == []


def test_question_enums_and_lengths_are_enforced():
    question = Question(
        question_id="q-1",
        categoria=QuestionCategory.BUSINESS_RULES,
        pregunta="¿Cuál es el plazo?",
        estado=QuestionState.PENDING,
    )
    assert question.estado == QuestionState.PENDING
    with pytest.raises(ValidationError):
        Question(question_id="q-2", categoria="otra", pregunta="Pregunta", estado="pendiente")
    with pytest.raises(ValidationError):
        Question(question_id="q-3", categoria=QuestionCategory.VALIDATIONS, pregunta=" " * 501, estado="pendiente")


def test_public_response_rejects_extra_fields_and_inconsistent_readiness():
    with pytest.raises(ValidationError):
        AgentTurnResponse(**valid_response(trace_id="internal"))
    with pytest.raises(ValidationError):
        AgentTurnResponse(
            **valid_response(analisis={"conocida": [], "faltante": ["Falta dato"], "supuesta": [], "ambigua": []})
        )


def test_readiness_requires_no_gaps_assumptions_ambiguities_or_pending_questions():
    pending = {
        "question_id": "q-1",
        "categoria": QuestionCategory.REQUIRED_DATA,
        "pregunta": "¿Qué dato se requiere?",
        "estado": QuestionState.PENDING,
    }
    with pytest.raises(ValidationError):
        AgentTurnResponse(**valid_response(preguntas=[pending]))
    answered = {**pending, "estado": QuestionState.ANSWERED}
    response = AgentTurnResponse(**valid_response(preguntas=[answered]))
    assert response.listo_para_redactor is True


def test_context_total_is_limited_and_preserves_unicode_message():
    context = ContextPayload(
        current_state={},
        recent_turns=[],
        current_message="😀",
        tool_results=[],
        limitations=[],
    )
    assert context.current_message == "😀"
    with pytest.raises(ValidationError):
        ContextPayload(
            current_state={"text": "x" * 25_000},
            recent_turns=[],
            current_message="actual current message",
            tool_results=[],
            limitations=[],
        )


@pytest.mark.parametrize("version", ["2.0.27", "2.1.2"])
def test_health_ready_accepts_supported_opencode_versions(version):
    checks = HealthChecks(
        opencode=OpenCodeCheck(status=CheckStatus.OK, version=version, agent="analista"),
        mcp=McpCheck(status=CheckStatus.OK, tools=list(ToolName)),
        langfuse=LangfuseCheck(status=CheckStatus.OK),
    )
    response = HealthResponse(
        status=HealthStatus.READY,
        checked_at=datetime.now(UTC),
        backend_version="1.0.0",
        timeout_seconds=90,
        message_limit=4000,
        restart_required=False,
        checks=checks,
    )
    assert response.status == HealthStatus.READY


def test_health_ready_rejects_unsupported_opencode_version():
    checks = HealthChecks(
        opencode=OpenCodeCheck(status=CheckStatus.OK, version="2.1.3", agent="analista"),
        mcp=McpCheck(status=CheckStatus.OK, tools=list(ToolName)),
        langfuse=LangfuseCheck(status=CheckStatus.OK),
    )
    with pytest.raises(ValidationError):
        HealthResponse(
            status=HealthStatus.READY,
            checked_at=datetime.now(UTC),
            backend_version="1.0.0",
            timeout_seconds=90,
            message_limit=4000,
            restart_required=False,
            checks=checks,
        )


def test_health_ready_requires_all_dependencies_and_restart_clear():
    checks = HealthChecks(
        opencode=OpenCodeCheck(status=CheckStatus.OK, version="2.0.27", agent="analista"),
        mcp=McpCheck(status=CheckStatus.OK, tools=list(ToolName)),
        langfuse=LangfuseCheck(status=CheckStatus.OK),
    )
    with pytest.raises(ValidationError):
        HealthResponse(
            status=HealthStatus.READY,
            checked_at=datetime.now(UTC),
            backend_version="1.0.0",
            timeout_seconds=90,
            message_limit=4000,
            restart_required=True,
            checks=checks,
        )


def test_internal_opencode_and_trace_ids_are_not_public_response_fields():
    fields = AgentTurnResponse.model_fields
    assert "opencode_session_id" not in fields
    assert "trace_id" not in fields
