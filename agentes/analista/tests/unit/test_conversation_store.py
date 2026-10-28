import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from agentes.analista.core.conversation_store import ConversationStore, StoreError
from agentes.analista.core.models import (
    AgentTurnResponse,
    ErrorCode,
    ErrorDetail,
    TurnStatus,
)


class FakeClock:
    def __init__(self):
        self.value = datetime(2026, 10, 26, 12, tzinfo=UTC)

    def __call__(self):
        return self.value

    def advance(self, delta: timedelta):
        self.value += delta


def store(*, clock=None, capacity=32, ttl=1800):
    return ConversationStore(
        prompt_version="1.0.0",
        prompt_hash="a" * 64,
        ttl_seconds=ttl,
        max_conversations=capacity,
        clock=clock,
    )


def response_for(conversation_id, start, message="analizar esto"):
    return AgentTurnResponse(
        conversation_id=conversation_id,
        request_id=start.turn.request_id,
        turn_id=start.turn.turn_id,
        estado="completado",
        respuesta_markdown=f"Análisis: {message}",
        analisis={"conocida": ["Dato confirmado"], "faltante": [], "supuesta": [], "ambigua": []},
        preguntas=[],
        fuentes_consultadas=[],
        listo_para_redactor=True,
        limitaciones=[],
        duracion_ms=5,
        prompt_version="1.0.0",
    )


@pytest.mark.asyncio
async def test_completed_turn_is_cached_and_only_success_enters_context():
    state = store()
    conversation = await state.create()
    request_id = uuid4()
    start = await state.begin_turn(conversation.conversation_id, request_id, "analizar esto")
    await state.complete_turn(
        conversation.conversation_id,
        start.turn.turn_id,
        start.generation,
        response_for(conversation.conversation_id, start),
    )

    replay = await state.begin_turn(conversation.conversation_id, request_id, "analizar esto")
    current = await state.get(conversation.conversation_id)
    assert replay.replayed is True
    assert replay.response is not None
    assert len(current.context_turns) == 1
    assert current.context_turns[0].message == "analizar esto"


@pytest.mark.asyncio
async def test_request_id_conflict_and_active_turn_are_rejected():
    state = store()
    conversation = await state.create()
    request_id = uuid4()
    start = await state.begin_turn(conversation.conversation_id, request_id, "texto original")

    with pytest.raises(StoreError) as conflict:
        await state.begin_turn(conversation.conversation_id, request_id, "texto diferente")
    assert conflict.value.code == ErrorCode.REQUEST_ID_CONFLICT

    with pytest.raises(StoreError) as active:
        await state.begin_turn(conversation.conversation_id, uuid4(), "otro turno")
    assert active.value.code == ErrorCode.TURN_IN_PROGRESS

    with pytest.raises(StoreError) as retry_active:
        await state.begin_turn(conversation.conversation_id, request_id, "texto original")
    assert retry_active.value.code == ErrorCode.TURN_IN_PROGRESS
    assert start.turn.status == TurnStatus.PROCESSING


@pytest.mark.asyncio
async def test_cancel_invalidates_turn_without_committing_context():
    state = store()
    conversation = await state.create()
    request_id = uuid4()
    start = await state.begin_turn(conversation.conversation_id, request_id, "cancelar")

    canceled, turn_id, reason = await state.cancel_turn(conversation.conversation_id, request_id)
    assert (canceled, turn_id, reason) == (True, start.turn.turn_id, "CANCELED")
    with pytest.raises(StoreError) as invalidated:
        await state.complete_turn(
            conversation.conversation_id,
            start.turn.turn_id,
            start.generation,
            response_for(conversation.conversation_id, start),
        )
    assert invalidated.value.code == ErrorCode.TURN_INVALIDATED

    current = await state.get(conversation.conversation_id)
    assert current.context_turns == []
    assert current.active_turn_id is None
    assert (await state.cancel_turn(conversation.conversation_id, request_id))[2] == "NO_ACTIVE_TURN"


@pytest.mark.asyncio
async def test_failure_is_cached_but_never_added_to_context():
    state = store()
    conversation = await state.create()
    request_id = uuid4()
    start = await state.begin_turn(conversation.conversation_id, request_id, "falla")
    error = ErrorDetail(code=ErrorCode.OPENCODE_UNAVAILABLE, message="Servicio no disponible.", retryable=True)
    await state.fail_turn(conversation.conversation_id, start.turn.turn_id, start.generation, error)

    replay = await state.begin_turn(conversation.conversation_id, request_id, "falla")
    current = await state.get(conversation.conversation_id)
    assert replay.replayed is True
    assert replay.error is not None and replay.error.code == ErrorCode.OPENCODE_UNAVAILABLE
    assert current.context_turns == []


@pytest.mark.asyncio
async def test_reset_replaces_identity_and_discards_active_generation():
    state = store()
    conversation = await state.create()
    start = await state.begin_turn(conversation.conversation_id, uuid4(), "en progreso")

    replacement, discarded_turn_id = await state.reset(conversation.conversation_id)
    assert replacement.conversation_id != conversation.conversation_id
    assert discarded_turn_id == start.turn.turn_id
    assert replacement.context_turns == []
    with pytest.raises(StoreError) as missing:
        await state.get(conversation.conversation_id)
    assert missing.value.code == ErrorCode.CONVERSATION_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_invalidates_active_turn_before_late_completion():
    state = store()
    conversation = await state.create()
    start = await state.begin_turn(conversation.conversation_id, uuid4(), "delete while processing")

    invalidated_turn_id = await state.delete(conversation.conversation_id)

    assert invalidated_turn_id == start.turn.turn_id
    with pytest.raises(StoreError) as late_completion:
        await state.complete_turn(
            conversation.conversation_id,
            start.turn.turn_id,
            start.generation,
            response_for(conversation.conversation_id, start),
        )
    assert late_completion.value.code == ErrorCode.CONVERSATION_NOT_FOUND
    assert await state.count() == 0


@pytest.mark.asyncio
async def test_capacity_evicts_least_recent_inactive_and_never_active():
    state = store(capacity=1)
    first = await state.create()
    active = await state.begin_turn(first.conversation_id, uuid4(), "activo")

    with pytest.raises(StoreError) as capacity:
        await state.create()
    assert capacity.value.code == ErrorCode.CAPACITY_EXCEEDED

    await state.fail_turn(
        first.conversation_id,
        active.turn.turn_id,
        active.generation,
        ErrorDetail(code=ErrorCode.INTERNAL_ERROR, message="Error controlado.", retryable=False),
    )
    second = await state.create()
    assert second.conversation_id != first.conversation_id
    with pytest.raises(StoreError):
        await state.get(first.conversation_id)


@pytest.mark.asyncio
async def test_ttl_cleanup_expires_inactive_conversations():
    clock = FakeClock()
    state = store(clock=clock, ttl=30)
    conversation = await state.create()
    clock.advance(timedelta(seconds=31))

    expired = await state.expire_idle()
    assert expired == [conversation.conversation_id]
    assert await state.count() == 0


@pytest.mark.asyncio
async def test_parallel_requests_for_one_conversation_create_one_active_turn():
    state = store()
    conversation = await state.create()
    starts = await asyncio.gather(
        state.begin_turn(conversation.conversation_id, uuid4(), "uno"),
        state.begin_turn(conversation.conversation_id, uuid4(), "dos"),
        return_exceptions=True,
    )
    assert sum(not isinstance(result, Exception) for result in starts) == 1
    errors = [result for result in starts if isinstance(result, StoreError)]
    assert len(errors) == 1 and errors[0].code == ErrorCode.TURN_IN_PROGRESS
