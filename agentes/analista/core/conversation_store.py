"""Bounded in-memory conversation state with per-conversation serialization."""
from __future__ import annotations

import asyncio
import hashlib
import unicodedata
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import AsyncIterator
from uuid import UUID, uuid4

from agentes.analista.core.models import (
    AgentTurnResponse,
    Analysis,
    CompletedTurn,
    ConversationRecord,
    ConversationStatus,
    ErrorCode,
    ErrorDetail,
    Question,
    SourceConsultation,
    ToolExecution,
    TurnRecord,
    TurnStatus,
)


class StoreError(Exception):
    """A safe domain error that can be translated to the REST contract."""

    def __init__(self, code: ErrorCode, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def as_detail(self, request_id: UUID | None = None) -> ErrorDetail:
        return ErrorDetail(code=self.code, message=self.message, retryable=self.retryable, request_id=request_id)


@dataclass(frozen=True)
class TurnStart:
    turn: TurnRecord
    generation: int
    replayed: bool = False
    response: AgentTurnResponse | None = None
    error: ErrorDetail | None = None


def _summarize_state(analysis: Analysis, questions: list[Question]) -> str:
    entries: list[str] = []
    for category, values in (
        ("Conocido", analysis.conocida),
        ("Faltante", analysis.faltante),
        ("Supuesto", analysis.supuesta),
        ("Ambiguo", analysis.ambigua),
    ):
        entries.extend(f"{category}: {value}" for value in values)
    entries.extend(f"Pregunta {item.estado.value}: {item.pregunta}" for item in questions)
    summary = "\n".join(entries)
    return summary[:2000]


class ConversationStore:
    """Keep only active conversation state and completed turns in memory."""

    def __init__(
        self,
        *,
        prompt_version: str,
        prompt_hash: str,
        ttl_seconds: int = 1800,
        max_conversations: int = 32,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if ttl_seconds < 1 or max_conversations < 1:
            raise ValueError("TTL y capacidad deben ser positivos")
        self.prompt_version = prompt_version
        self.prompt_hash = prompt_hash
        self.ttl = timedelta(seconds=ttl_seconds)
        self.max_conversations = max_conversations
        self._clock = clock or (lambda: datetime.now(UTC))
        self._records: dict[UUID, ConversationRecord] = {}
        self._locks: dict[UUID, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[None] | None = None

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("El reloj del store debe devolver una fecha con zona horaria")
        return value.astimezone(UTC)

    @staticmethod
    def hash_message(message: str) -> str:
        normalized = unicodedata.normalize("NFC", " ".join(message.split()))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _new_record(self, now: datetime, *, replaced_id: UUID | None = None) -> ConversationRecord:
        del replaced_id  # The replacement relationship is returned by the API, not persisted.
        return ConversationRecord(
            conversation_id=uuid4(),
            created_at=now,
            last_activity_at=now,
            expires_at=now + self.ttl,
            generation=0,
            status=ConversationStatus.ACTIVE,
            context_turns=[],
            questions=[],
            request_cache={},
            last_sources=[],
            prompt_version=self.prompt_version,
            prompt_hash=self.prompt_hash,
            turns_count=0,
        )

    async def create(self) -> ConversationRecord:
        now = self._now()
        async with self._registry_lock:
            self._expire_records_locked(now)
            if len(self._records) >= self.max_conversations:
                candidates = [record for record in self._records.values() if record.active_turn_id is None]
                if not candidates:
                    raise StoreError(
                        ErrorCode.CAPACITY_EXCEEDED,
                        "El servicio alcanzó su capacidad de conversaciones activas.",
                        retryable=True,
                    )
                victim = min(
                    candidates,
                    key=lambda record: (record.last_activity_at, record.created_at, str(record.conversation_id)),
                )
                self._remove_locked(victim.conversation_id)

            record = self._new_record(now)
            self._records[record.conversation_id] = record
            self._locks[record.conversation_id] = asyncio.Lock()
            return record.model_copy(deep=True)

    def _expire_records_locked(self, now: datetime) -> list[UUID]:
        expired: list[UUID] = []
        for conversation_id, record in list(self._records.items()):
            if record.expires_at <= now and record.active_turn_id is None:
                record.status = ConversationStatus.EXPIRED
                record.generation += 1
                self._remove_locked(conversation_id)
                expired.append(conversation_id)
        return expired

    def _remove_locked(self, conversation_id: UUID) -> ConversationRecord | None:
        self._locks.pop(conversation_id, None)
        return self._records.pop(conversation_id, None)

    @asynccontextmanager
    async def _guard(self, conversation_id: UUID) -> AsyncIterator[ConversationRecord]:
        async with self._registry_lock:
            record = self._records.get(conversation_id)
            lock = self._locks.get(conversation_id)
        if record is None or lock is None:
            raise StoreError(ErrorCode.CONVERSATION_NOT_FOUND, "La conversación no existe o ya expiró.")

        await lock.acquire()
        try:
            if self._records.get(conversation_id) is not record:
                raise StoreError(ErrorCode.CONVERSATION_NOT_FOUND, "La conversación no existe o ya expiró.")
            if record.expires_at <= self._now():
                record.status = ConversationStatus.EXPIRED
                record.generation += 1
                async with self._registry_lock:
                    if self._records.get(conversation_id) is record:
                        self._remove_locked(conversation_id)
                raise StoreError(ErrorCode.CONVERSATION_NOT_FOUND, "La conversación expiró por inactividad.")
            if record.status != ConversationStatus.ACTIVE and record.status != ConversationStatus.PROCESSING:
                raise StoreError(ErrorCode.CONVERSATION_NOT_FOUND, "La conversación ya no está disponible.")
            yield record
        finally:
            lock.release()

    def _touch(self, record: ConversationRecord, now: datetime) -> None:
        record.last_activity_at = now
        record.expires_at = now + self.ttl

    async def get(self, conversation_id: UUID) -> ConversationRecord:
        async with self._guard(conversation_id) as record:
            return record.model_copy(deep=True)

    async def begin_turn(self, conversation_id: UUID, request_id: UUID, message: str) -> TurnStart:
        digest = self.hash_message(message)
        async with self._guard(conversation_id) as record:
            existing = record.request_cache.get(request_id)
            if existing is not None:
                if existing.message_hash != digest:
                    raise StoreError(
                        ErrorCode.REQUEST_ID_CONFLICT,
                        "Este request_id ya fue usado con un mensaje distinto.",
                    )
                if existing.status == TurnStatus.COMPLETED and existing.response is not None:
                    return TurnStart(existing.model_copy(deep=True), record.generation, True, existing.response.model_copy(deep=True))
                if existing.status in {TurnStatus.FAILED, TurnStatus.CANCELLED, TurnStatus.EXPIRED}:
                    return TurnStart(
                        existing.model_copy(deep=True),
                        record.generation,
                        True,
                        error=existing.error.model_copy(deep=True) if existing.error else None,
                    )
                raise StoreError(ErrorCode.TURN_IN_PROGRESS, "Ya hay un turno en proceso para esta conversación.", retryable=True)

            if record.active_turn_id is not None:
                raise StoreError(ErrorCode.TURN_IN_PROGRESS, "Ya hay un turno en proceso para esta conversación.", retryable=True)

            now = self._now()
            turn = TurnRecord(
                turn_id=uuid4(),
                request_id=request_id,
                conversation_id=conversation_id,
                message=message,
                message_hash=digest,
                status=TurnStatus.PROCESSING,
                created_at=now,
                started_at=now,
                tool_results=[],
                repair_attempts=0,
            )
            record.request_cache[request_id] = turn
            record.active_turn_id = turn.turn_id
            record.status = ConversationStatus.PROCESSING
            record.turns_count += 1
            self._touch(record, now)
            return TurnStart(turn.model_copy(deep=True), record.generation)

    def _get_active_turn(self, record: ConversationRecord, turn_id: UUID, generation: int) -> TurnRecord:
        if record.generation != generation or record.active_turn_id != turn_id:
            raise StoreError(ErrorCode.TURN_INVALIDATED, "El turno fue invalidado por un cambio de conversación.")
        turn = next((item for item in record.request_cache.values() if item.turn_id == turn_id), None)
        if turn is None or turn.status != TurnStatus.PROCESSING:
            raise StoreError(ErrorCode.TURN_INVALIDATED, "El turno ya no está activo.")
        return turn

    async def add_tool_execution(
        self, conversation_id: UUID, turn_id: UUID, generation: int, execution: ToolExecution
    ) -> None:
        async with self._guard(conversation_id) as record:
            turn = self._get_active_turn(record, turn_id, generation)
            if any(item.tool_name == execution.tool_name for item in turn.tool_results):
                raise StoreError(ErrorCode.INTERNAL_ERROR, "La misma herramienta no puede registrarse dos veces.")
            turn.tool_results.append(execution)

    async def set_opencode_session(
        self, conversation_id: UUID, turn_id: UUID, generation: int, session_id: str
    ) -> None:
        async with self._guard(conversation_id) as record:
            turn = self._get_active_turn(record, turn_id, generation)
            turn.opencode_session_id = session_id

    async def complete_turn(
        self,
        conversation_id: UUID,
        turn_id: UUID,
        generation: int,
        response: AgentTurnResponse,
        *,
        analysis: Analysis | None = None,
        questions: list[Question] | None = None,
    ) -> TurnRecord:
        async with self._guard(conversation_id) as record:
            turn = self._get_active_turn(record, turn_id, generation)
            if response.conversation_id != conversation_id or response.turn_id != turn_id or response.request_id != turn.request_id:
                raise StoreError(ErrorCode.INTERNAL_ERROR, "La respuesta no corresponde al turno activo.")
            now = self._now()
            turn.status = TurnStatus.COMPLETED
            turn.completed_at = now
            turn.duration_ms = max(0, int((now - (turn.started_at or turn.created_at)).total_seconds() * 1000))
            turn.response = response.model_copy(deep=True)
            turn.analysis = (analysis or response.analisis).model_copy(deep=True)
            turn.questions = [item.model_copy(deep=True) for item in (questions or response.preguntas)]
            record.context_turns.append(
                CompletedTurn(
                    turn_id=turn.turn_id,
                    request_id=turn.request_id,
                    message=turn.message,
                    response=response.model_copy(deep=True),
                    completed_at=now,
                )
            )
            record.context_turns = record.context_turns[-6:]
            record.analysis = turn.analysis.model_copy(deep=True)
            record.questions = [item.model_copy(deep=True) for item in turn.questions]
            record.previous_summary = _summarize_state(record.analysis, record.questions)
            record.last_sources = [item.model_copy(deep=True) for item in response.fuentes_consultadas]
            record.status = ConversationStatus.ACTIVE
            record.active_turn_id = None
            self._touch(record, now)
            return turn.model_copy(deep=True)

    async def fail_turn(
        self,
        conversation_id: UUID,
        turn_id: UUID,
        generation: int,
        error: ErrorDetail,
        *,
        status: TurnStatus = TurnStatus.FAILED,
    ) -> TurnRecord:
        if status not in {TurnStatus.FAILED, TurnStatus.CANCELLED, TurnStatus.EXPIRED, TurnStatus.DISCARDED}:
            raise ValueError("El turno debe terminar en estado de fallo, cancelación, expiración o descarte")
        async with self._guard(conversation_id) as record:
            turn = self._get_active_turn(record, turn_id, generation)
            now = self._now()
            turn.status = status
            turn.error = error.model_copy(deep=True)
            turn.completed_at = now
            turn.duration_ms = max(0, int((now - (turn.started_at or turn.created_at)).total_seconds() * 1000))
            turn.invalidated_by_generation = record.generation if status == TurnStatus.DISCARDED else None
            record.status = ConversationStatus.ACTIVE
            record.active_turn_id = None
            self._touch(record, now)
            return turn.model_copy(deep=True)

    async def cancel_turn(self, conversation_id: UUID, request_id: UUID) -> tuple[bool, UUID | None, str]:
        async with self._guard(conversation_id) as record:
            turn_id = record.active_turn_id
            if turn_id is None:
                return False, None, "NO_ACTIVE_TURN"
            turn = next((item for item in record.request_cache.values() if item.turn_id == turn_id), None)
            if turn is None:
                return False, None, "ALREADY_TERMINAL"
            if turn.request_id != request_id:
                return False, turn_id, "REQUEST_ID_MISMATCH"
            now = self._now()
            turn.status = TurnStatus.CANCELLED
            turn.cancel_requested_at = now
            turn.completed_at = now
            turn.duration_ms = max(0, int((now - (turn.started_at or turn.created_at)).total_seconds() * 1000))
            turn.error = ErrorDetail(
                code=ErrorCode.TURN_CANCELLED,
                message="El turno fue cancelado.",
                retryable=False,
                request_id=turn.request_id,
            )
            turn.invalidated_by_generation = record.generation
            record.status = ConversationStatus.ACTIVE
            record.active_turn_id = None
            self._touch(record, now)
            return True, turn_id, "CANCELED"

    async def reset(self, conversation_id: UUID) -> tuple[ConversationRecord, UUID | None]:
        async with self._guard(conversation_id) as record:
            active_turn_id = record.active_turn_id
            if active_turn_id is not None:
                active = next((item for item in record.request_cache.values() if item.turn_id == active_turn_id), None)
                if active is not None:
                    active.status = TurnStatus.DISCARDED
                    active.completed_at = self._now()
                    active.invalidated_by_generation = record.generation + 1
            record.status = ConversationStatus.REPLACED
            record.generation += 1
            record.active_turn_id = None
            async with self._registry_lock:
                self._remove_locked(conversation_id)
                replacement = self._new_record(self._now())
                self._records[replacement.conversation_id] = replacement
                self._locks[replacement.conversation_id] = asyncio.Lock()
            return replacement.model_copy(deep=True), active_turn_id

    async def delete(self, conversation_id: UUID) -> UUID | None:
        async with self._registry_lock:
            record = self._records.get(conversation_id)
            lock = self._locks.get(conversation_id)
        if record is None or lock is None:
            return None
        await lock.acquire()
        try:
            if self._records.get(conversation_id) is not record:
                return None
            active_turn_id = record.active_turn_id
            if active_turn_id is not None:
                active = next((item for item in record.request_cache.values() if item.turn_id == active_turn_id), None)
                if active is not None:
                    active.status = TurnStatus.DISCARDED
                    active.completed_at = self._now()
                    active.invalidated_by_generation = record.generation + 1
            record.status = ConversationStatus.DELETED
            record.generation += 1
            record.active_turn_id = None
            async with self._registry_lock:
                self._remove_locked(conversation_id)
            return active_turn_id
        finally:
            lock.release()

    async def expire_idle(self) -> list[UUID]:
        async with self._registry_lock:
            return self._expire_records_locked(self._now())

    async def start_cleanup(self, interval_seconds: int = 60) -> None:
        if interval_seconds < 1:
            raise ValueError("El intervalo de limpieza debe ser positivo")
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop(interval_seconds))

    async def _cleanup_loop(self, interval_seconds: int) -> None:
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                await self.expire_idle()
        except asyncio.CancelledError:
            raise

    async def stop_cleanup(self) -> None:
        task = self._cleanup_task
        self._cleanup_task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def count(self) -> int:
        async with self._registry_lock:
            self._expire_records_locked(self._now())
            return len(self._records)
