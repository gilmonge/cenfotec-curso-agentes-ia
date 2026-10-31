"""Translate private errors into the stable public REST envelope."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from agentes.analista.core.conversation_store import StoreError
from agentes.analista.core.models import ErrorCode, ErrorDetail, ErrorResponse, ValidationIssue
from agentes.analista.core.orchestrator import OrchestrationError
from agentes.analista.memory.repositorio import RepositorioError

logger = logging.getLogger(__name__)


def _status(code: ErrorCode) -> int:
    if code in {ErrorCode.CONVERSATION_NOT_FOUND, ErrorCode.REPOSITORY_NOT_FOUND}:
        return 404
    if code in {ErrorCode.TURN_IN_PROGRESS, ErrorCode.REQUEST_ID_CONFLICT, ErrorCode.TURN_CANCELLED, ErrorCode.TURN_INVALIDATED}:
        return 409
    if code == ErrorCode.AGENT_OUTPUT_INVALID:
        return 502
    if code == ErrorCode.TURN_TIMEOUT:
        return 504
    if code in {ErrorCode.OPENCODE_RATE_LIMITED, ErrorCode.MODEL_UNAVAILABLE}:
        return 503
    if code in {
        ErrorCode.OPENCODE_UNAVAILABLE, ErrorCode.OPENCODE_AUTH_FAILED,
        ErrorCode.MCP_UNAVAILABLE, ErrorCode.PROMPT_INVALID,
        ErrorCode.PROMPT_RESTART_REQUIRED, ErrorCode.CAPACITY_EXCEEDED,
    }:
        return 503
    if code == ErrorCode.INVALID_REQUEST or code in {ErrorCode.MESSAGE_EMPTY, ErrorCode.MESSAGE_TOO_LONG}:
        return 422
    return 500


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StoreError)
    async def store_error(_: Request, exc: StoreError) -> JSONResponse:
        detail = ErrorDetail(code=exc.code, message=exc.message, retryable=exc.retryable)
        return JSONResponse(status_code=_status(exc.code), content=ErrorResponse(error=detail).model_dump(mode="json"))

    @app.exception_handler(RepositorioError)
    async def repositorio_error(_: Request, exc: RepositorioError) -> JSONResponse:
        code = ErrorCode.REPOSITORY_NOT_FOUND if exc.not_found else ErrorCode.INVALID_REQUEST
        detail = ErrorDetail(code=code, message=exc.message[:500], retryable=False)
        return JSONResponse(status_code=_status(code), content=ErrorResponse(error=detail).model_dump(mode="json"))

    @app.exception_handler(OrchestrationError)
    async def orchestration_error(_: Request, exc: OrchestrationError) -> JSONResponse:
        # Deja la causa en los logs del hosting: el código HTTP solo no dice qué falló.
        logger.warning(
            "turno_fallido",
            extra={"event": "turno_fallido", "error_code": exc.code.value, "status": _status(exc.code)},
        )
        detail = ErrorDetail(
            code=exc.code, message=str(exc), retryable=exc.retryable, retry_at=exc.retry_at,
        )
        return JSONResponse(status_code=_status(exc.code), content=ErrorResponse(error=detail).model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        issues = [
            ValidationIssue(field=".".join(str(part) for part in item.get("loc", ()) if part != "body")[:120],
                            message=str(item.get("msg", "Valor inválido"))[:300])
            for item in exc.errors()[:20]
        ]
        detail = ErrorDetail(
            code=ErrorCode.INVALID_REQUEST,
            message="La solicitud no cumple el contrato.",
            retryable=False,
            issues=issues,
        )
        return JSONResponse(status_code=422, content=ErrorResponse(error=detail).model_dump(mode="json"))
