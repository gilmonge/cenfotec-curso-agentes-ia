"""In-memory conversation lifecycle and message routes."""
from __future__ import annotations

import logging
from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from agentes.analista.core.conversation_store import ConversationStore, StoreError
from agentes.analista.core.models import (
    CancelRequest,
    CancelResponse,
    CreateConversationResponse,
    AgentTurnResponse,
    ErrorCode,
    ErrorDetail,
    ResetResponse,
    SendMessageRequest,
)
from agentes.analista.core.opencode_client import OpenCodeClient, OpenCodeClientError
from agentes.analista.core.orchestrator import OrchestrationError, run_turn
from agentes.analista.core.prompt_loader import PromptLoadError, load_prompt


logger = logging.getLogger(__name__)
router = APIRouter()


def _conversation_response(record, request: Request) -> CreateConversationResponse:
    return CreateConversationResponse(
        conversation_id=record.conversation_id,
        created_at=record.created_at,
        expires_at=record.expires_at,
        message_limit=4000,
        timeout_seconds=request.app.state.settings.turn_timeout_seconds,
    )


async def _active_session(store: ConversationStore, conversation_id: UUID, turn_id: UUID | None) -> str | None:
    if turn_id is None:
        return None
    try:
        record = await store.get(conversation_id)
    except StoreError:
        return None
    turn = next((item for item in record.request_cache.values() if item.turn_id == turn_id), None)
    return turn.opencode_session_id if turn else None


async def _stop_session(session_id: str | None) -> None:
    if not session_id:
        return
    try:
        async with OpenCodeClient() as client:
            try:
                await client.interrupt(session_id)
            except OpenCodeClientError:
                pass
            await client.delete_session(session_id)
    except OpenCodeClientError as exc:
        logger.warning("opencode_cleanup_failed", extra={"event": "opencode_cleanup_failed", "error_code": exc.code})


@router.post("/conversaciones", response_model=CreateConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(request: Request) -> CreateConversationResponse:
    store: ConversationStore = request.app.state.store
    return _conversation_response(await store.create(), request)


@router.post("/conversaciones/{conversation_id}/mensajes", response_model=AgentTurnResponse)
async def send_message(conversation_id: UUID, body: SendMessageRequest, request: Request):
    try:
        current_prompt = load_prompt()
    except PromptLoadError as exc:
        raise OrchestrationError(ErrorCode.PROMPT_INVALID, "El prompt configurado no está disponible.") from exc
    request.app.state.restart_required = current_prompt.sha256 != request.app.state.prompt_snapshot.sha256
    if request.app.state.restart_required:
        raise OrchestrationError(ErrorCode.PROMPT_RESTART_REQUIRED, "Reinicia el backend para cargar el prompt actualizado.")
    return await run_turn(
        request.app.state.store,
        conversation_id,
        body,
        observability=request.app.state.observability,
    )


@router.post("/conversaciones/{conversation_id}/cancelar", response_model=CancelResponse)
async def cancel_turn(conversation_id: UUID, body: CancelRequest, request: Request) -> CancelResponse:
    store: ConversationStore = request.app.state.store
    canceled, turn_id, reason = await store.cancel_turn(conversation_id, body.request_id)
    if canceled:
        await _stop_session(await _active_session(store, conversation_id, turn_id))
    return CancelResponse(canceled=canceled, turn_id=turn_id, reason=reason)


@router.post("/conversaciones/{conversation_id}/reiniciar", response_model=ResetResponse)
async def reset_conversation(conversation_id: UUID, request: Request) -> ResetResponse:
    store: ConversationStore = request.app.state.store
    active = await store.get(conversation_id)
    active_id = active.active_turn_id
    session_id = await _active_session(store, conversation_id, active_id)
    replacement, _ = await store.reset(conversation_id)
    await _stop_session(session_id)
    return ResetResponse(
        **_conversation_response(replacement, request).model_dump(),
        replaced_conversation_id=conversation_id,
    )


@router.delete("/conversaciones/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: UUID, request: Request) -> Response:
    store: ConversationStore = request.app.state.store
    try:
        record = await store.get(conversation_id)
        session_id = await _active_session(store, conversation_id, record.active_turn_id)
    except StoreError:
        session_id = None
    await store.delete(conversation_id)
    await _stop_session(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
