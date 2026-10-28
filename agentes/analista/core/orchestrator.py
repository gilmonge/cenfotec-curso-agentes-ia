"""Real LangChain/MCP/OpenCode turn orchestration with bounded failure handling."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain.mcp import MCPAdapter
from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import RunnableLambda, RunnableParallel
from pydantic import TypeAdapter, ValidationError

from agentes.analista.core.context_builder import build_context, render_user_prompt
from agentes.analista.core.models import (
    AgentTurnResponse,
    Analysis,
    ErrorCode,
    ErrorDetail,
    Question,
    QuestionState,
    SourceConsultation,
    ToolExecution,
    ToolName,
    ToolStatus,
    TurnStatus,
)
from agentes.analista.core.opencode_client import OpenCodeClient, OpenCodeClientError, OpenCodeSettings
from agentes.analista.core.output_parser import AgentOutput, format_instructions, parse_agent_output
from agentes.analista.core.prompt_loader import load_prompt
from agentes.analista.core.conversation_store import ConversationStore, StoreError
from agentes.analista.core.observability import Observability
from agentes.analista.mcp.tools import ChecklistResult, GlossaryResult, StandardsResult, StoriesResult


logger = logging.getLogger(__name__)
MCP_SERVER = Path(__file__).resolve().parents[1] / "mcp" / "server.py"
MCP_TIMEOUT_SECONDS = 5.0
EXPECTED_TOOLS = {item.value for item in ToolName}
_RESULT_MODELS: dict[str, type[Any]] = {
    "consultar_glosario": GlossaryResult,
    "buscar_hu_similares": StoriesResult,
    "consultar_estandares": StandardsResult,
    "aplicar_checklist_vacios": ChecklistResult,
}


class OrchestrationError(RuntimeError):
    def __init__(
        self, code: ErrorCode, message: str, *, retryable: bool = False,
        retry_at: datetime | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.retry_at = retry_at


async def _within_deadline(awaitable: Any, deadline: float) -> Any:
    remaining = deadline - asyncio.get_running_loop().time()
    if remaining <= 0:
        raise OrchestrationError(ErrorCode.TURN_TIMEOUT, "Se agotó el tiempo del turno.", retryable=True)
    try:
        return await asyncio.wait_for(awaitable, timeout=remaining)
    except asyncio.TimeoutError as exc:
        raise OrchestrationError(ErrorCode.TURN_TIMEOUT, "Se agotó el tiempo del turno.", retryable=True) from exc


def _unwrap_tool_result(value: Any) -> Any:
    if isinstance(value, tuple) and len(value) == 2:
        artifact = value[1]
        if artifact is not None:
            value = artifact
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        for key in ("structuredContent", "structured_content", "data"):
            if key in value and isinstance(value[key], (dict, list)):
                return value[key]
        return value
    if isinstance(value, list):
        for item in value:
            text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
            if isinstance(text, str):
                try:
                    return json.loads(text)
                except ValueError:
                    continue
        raise ValueError("El resultado MCP no contiene JSON estructurado")
    artifact = getattr(value, "artifact", None)
    if artifact is not None:
        return _unwrap_tool_result(artifact)
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    content = getattr(value, "content", None)
    if isinstance(content, list):
        for item in content:
            text = getattr(item, "text", None)
            if isinstance(text, str):
                try:
                    return json.loads(text)
                except ValueError:
                    continue
    raise ValueError("La respuesta MCP no contiene resultado estructurado")


def _result_count(name: str, data: Any) -> int:
    fields = {
        "consultar_glosario": ("definiciones",),
        "buscar_hu_similares": ("historias",),
        "consultar_estandares": ("estandares",),
        "aplicar_checklist_vacios": ("total",),
    }
    if name == "aplicar_checklist_vacios":
        return int(data["total"])
    return len(data[fields[name][0]])


async def _execute_tools(query: str, trace: Any = None) -> tuple[list[dict[str, Any]], list[ToolExecution], list[str]]:
    started = time.monotonic()
    try:
        async with MCPAdapter(MCP_SERVER) as adapter:
            tools = await adapter.list_tools()
            by_name = {tool.name: tool for tool in tools}
            if set(by_name) != EXPECTED_TOOLS:
                raise OrchestrationError(ErrorCode.MCP_UNAVAILABLE, "El servidor MCP no expone el conjunto autorizado.", retryable=True)

            async def invoke(name: str, tool: Any) -> dict[str, Any]:
                start = time.monotonic()
                operation = trace.operation(
                    kind="tool", name=f"mcp-{name}", metadata={"tool_name": name}
                ) if trace else None
                try:
                    raw = await asyncio.wait_for(
                        tool.ainvoke({"consulta": query, "limite": 5}), timeout=MCP_TIMEOUT_SECONDS
                    )
                    parsed = TypeAdapter(_RESULT_MODELS[name]).validate_python(_unwrap_tool_result(raw))
                    data = parsed.model_dump(mode="json")
                    count = _result_count(name, data)
                    if operation:
                        operation.finish(status="ok", metadata={"result_count": count})
                    return {
                        "name": name,
                        "data": data,
                        "count": count,
                        "duration_ms": max(0, int((time.monotonic() - start) * 1000)),
                        "status": ToolStatus.OK,
                    }
                except asyncio.TimeoutError:
                    if operation:
                        operation.finish(status="timeout", error_code="MCP_TIMEOUT")
                    return {"name": name, "data": None, "count": None, "duration_ms": max(0, int((time.monotonic() - start) * 1000)), "status": ToolStatus.TIMEOUT}
                except asyncio.CancelledError:
                    if operation:
                        operation.finish(status="cancelled", error_code="TURN_CANCELLED")
                    raise
                except Exception:
                    if operation:
                        operation.finish(status="error", error_code="MCP_TOOL_FAILED")
                    return {"name": name, "data": None, "count": None, "duration_ms": max(0, int((time.monotonic() - start) * 1000)), "status": ToolStatus.ERROR}

            def tool_runner(name: str, tool: Any) -> RunnableLambda:
                async def run(_input: Any) -> dict[str, Any]:
                    return await invoke(name, tool)

                return RunnableLambda(run)

            parallel = RunnableParallel(**{
                name: tool_runner(name, tool)
                for name, tool in by_name.items()
            })
            results = await asyncio.wait_for(parallel.ainvoke({"consulta": query}), timeout=MCP_TIMEOUT_SECONDS + 1)
    except OrchestrationError:
        raise
    except Exception as exc:
        logger.warning("mcp_call_failed", extra={"event": "mcp_call_failed", "error_code": "MCP_UNAVAILABLE"})
        raise OrchestrationError(ErrorCode.MCP_UNAVAILABLE, "No fue posible consultar las fuentes autorizadas.", retryable=True) from exc

    observations: list[dict[str, Any]] = []
    executions: list[ToolExecution] = []
    limitations: list[str] = []
    for name in sorted(EXPECTED_TOOLS):
        result = results[name]
        status = result["status"]
        error_code = None if status == ToolStatus.OK else ("MCP_TIMEOUT" if status == ToolStatus.TIMEOUT else "MCP_TOOL_FAILED")
        digest = hashlib.sha256(json.dumps(result["data"], sort_keys=True, ensure_ascii=False).encode()).hexdigest() if result["data"] is not None else None
        executions.append(ToolExecution(
            tool_name=ToolName(name), status=status, result_count=result["count"],
            duration_ms=result["duration_ms"], error_code=error_code, result_digest=digest,
        ))
        if status == ToolStatus.OK:
            observations.append({"nombre": name, "datos": result["data"], "resultados": result["count"]})
        else:
            limitations.append(f"No se pudo consultar {name}; sus resultados no se usaron.")
    return observations, executions, limitations


def _to_response(
    output: AgentOutput,
    *,
    conversation_id: Any,
    request_id: Any,
    turn_id: Any,
    prior_questions: list[Question],
    tool_executions: list[ToolExecution],
    limitations: list[str],
    duration_ms: int,
) -> AgentTurnResponse:
    def question_key(value: str) -> str:
        return " ".join(value.casefold().split()).rstrip(".,;:!?¿¡")

    prior_by_text = {question_key(item.pregunta): item for item in prior_questions}
    questions: list[Question] = []
    seen: set[str] = set()
    for item in output.preguntas:
        key = question_key(item.pregunta)
        if key in seen:
            continue
        seen.add(key)
        previous = prior_by_text.get(key)
        state = item.estado
        if previous:
            if previous.estado == QuestionState.ANSWERED:
                state = QuestionState.ANSWERED
            updated_turn_id = turn_id
        else:
            updated_turn_id = None
        questions.append(Question(
            question_id=previous.question_id if previous else str(uuid4()),
            categoria=item.categoria,
            pregunta=item.pregunta.strip(),
            estado=state,
            created_turn_id=previous.created_turn_id if previous else turn_id,
            updated_turn_id=updated_turn_id,
        ))

    # Keep omitted questions visible; an open item remains unresolved and an
    # answered item remains history even when the model omits it this turn.
    for previous in prior_questions:
        key = question_key(previous.pregunta)
        if key in seen:
            continue
        seen.add(key)
        questions.append(previous.model_copy(deep=True))
    if len(questions) > 50:
        raise OrchestrationError(
            ErrorCode.AGENT_OUTPUT_INVALID,
            "La consolidación superó el máximo de 50 preguntas.",
        )
    sources = [
        SourceConsultation(nombre=ToolName(str(item.tool_name)), resultados=int(item.result_count or 0), duracion_ms=item.duration_ms)
        for item in tool_executions if item.status == ToolStatus.OK
    ]
    # The readiness gate is derived from validated facts, never trusted to the model.
    ready = not (output.analisis.faltante or output.analisis.supuesta or output.analisis.ambigua)
    ready = ready and not any(item.estado == QuestionState.PENDING for item in questions)
    return AgentTurnResponse(
        conversation_id=conversation_id,
        request_id=request_id,
        turn_id=turn_id,
        estado="completado",
        respuesta_markdown=output.respuesta_markdown.strip(),
        analisis=output.analisis,
        preguntas=questions,
        fuentes_consultadas=sources[:4],
        listo_para_redactor=ready,
        limitaciones=limitations[:10],
        duracion_ms=duration_ms,
        prompt_version=load_prompt().version,
    )


async def run_turn(
    store: ConversationStore,
    conversation_id: Any,
    request: Any,
    *,
    observability: Observability | None = None,
) -> AgentTurnResponse:
    """Execute one real turn; every OpenCode session is deleted in a finally block."""
    start = await store.begin_turn(conversation_id, request.request_id, request.message)
    if start.replayed:
        if start.response is not None:
            return start.response
        if start.error is not None:
            raise OrchestrationError(
                start.error.code, start.error.message,
                retryable=start.error.retryable, retry_at=start.error.retry_at,
            )
        raise OrchestrationError(ErrorCode.TURN_IN_PROGRESS, "El mismo request_id ya está procesándose.", retryable=True)

    timeout_seconds = OpenCodeSettings.from_environment().turn_timeout_seconds
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    turn_id = start.turn.turn_id
    generation = start.generation
    trace = (observability or Observability()).start_turn(
        conversation_id=conversation_id,
        request_id=request.request_id,
        turn_id=turn_id,
    )
    trace_finished = False
    trace_error_code: str | None = None
    try:
        record = await store.get(conversation_id)
        tool_results, executions, limitations = await _within_deadline(
            _execute_tools(request.message, trace), deadline
        )
        for execution in executions:
            await store.add_tool_execution(conversation_id, turn_id, generation, execution)
        payload = build_context(record, request.message, tool_results, limitations)
        user_prompt = render_user_prompt(payload, format_instructions())

        async def invoke_opencode(prompt_text: str) -> AgentOutput:
            async with OpenCodeClient() as client:
                client.set_deadline(deadline)
                await client.server_info()
                agent = await client.verify_agent("analista")
                model = await client.select_model(agent)
                operation = trace.operation(
                    kind="generation",
                    name="opencode-generation",
                    metadata={"provider": "opencode", "model": model["id"]},
                )
                try:
                    title = f"analista-{str(conversation_id)[:8]}-{str(turn_id)[:8]}"
                    async with client.session(title=title, model=model) as session:
                        session_id = session["id"]
                        await store.set_opencode_session(conversation_id, turn_id, generation, session_id)
                        admission = await client.submit_prompt(session_id, prompt_text)
                        after = admission.get("time", {}).get("created")
                        generated = await client.wait_for_assistant(session_id, deadline=deadline, after=after)
                        raw = generated["text"]
                        repaired_output = False
                        try:
                            output = parse_agent_output(raw)
                        except (OutputParserException, ValidationError, ValueError):
                            remaining = deadline - asyncio.get_running_loop().time()
                            if remaining <= 0:
                                raise OrchestrationError(ErrorCode.TURN_TIMEOUT, "Se agotó el tiempo para validar la respuesta.", retryable=True)
                            repair = (
                                "La salida anterior no cumplió el formato requerido. Devuelve únicamente un objeto JSON válido "
                                "conforme al esquema indicado. No agregues texto, markdown fences ni campos nuevos.\n\n"
                                + raw[:8000]
                            )
                            repair_admission = await client.submit_prompt(session_id, repair)
                            repair_after = repair_admission.get("time", {}).get("created")
                            repaired = await client.wait_for_assistant(
                                session_id, deadline=deadline, after=repair_after
                            )
                            try:
                                output = parse_agent_output(repaired["text"])
                                repaired_output = True
                            except (OutputParserException, ValidationError, ValueError) as exc:
                                raise OrchestrationError(
                                    ErrorCode.AGENT_OUTPUT_INVALID,
                                    "El agente no produjo una respuesta estructurada válida.",
                                ) from exc
                    operation.finish(status="ok", metadata={"repaired": repaired_output, "finish": generated.get("finish")})
                    return output
                except OpenCodeClientError as exc:
                    operation.finish(status="error", error_code=exc.code)
                    raise
                except OrchestrationError as exc:
                    operation.finish(status="error", error_code=exc.code.value)
                    raise
                except Exception:
                    operation.finish(status="error", error_code="GENERATION_FAILED")
                    raise

        output = await _within_deadline(RunnableLambda(invoke_opencode).ainvoke(user_prompt), deadline)
        if asyncio.get_running_loop().time() >= deadline:
            raise OrchestrationError(ErrorCode.TURN_TIMEOUT, "Se agotó el tiempo del turno.", retryable=True)

        duration_ms = max(0, int((timeout_seconds - max(0, deadline - asyncio.get_running_loop().time())) * 1000))
        response = _to_response(
            output,
            conversation_id=conversation_id,
            request_id=request.request_id,
            turn_id=turn_id,
            prior_questions=record.questions,
            tool_executions=executions,
            limitations=limitations,
            duration_ms=duration_ms,
        )
        if asyncio.get_running_loop().time() >= deadline:
            raise OrchestrationError(ErrorCode.TURN_TIMEOUT, "Se agotó el tiempo del turno.", retryable=True)
        await store.complete_turn(conversation_id, turn_id, generation, response)
        trace.finish(status="ok", metadata={"duration_ms": duration_ms, "tool_count": len(executions)})
        trace_finished = True
        return response
    except StoreError as exc:
        if exc.code == ErrorCode.TURN_INVALIDATED:
            raise OrchestrationError(ErrorCode.TURN_CANCELLED, "El turno fue cancelado o invalidado.") from exc
        raise
    except OpenCodeClientError as exc:
        trace_error_code = exc.code
        try:
            current = await store.get(conversation_id)
            if current.active_turn_id != turn_id:
                raise OrchestrationError(ErrorCode.TURN_CANCELLED, "El turno fue cancelado o invalidado.") from exc
        except StoreError as store_error:
            if store_error.code == ErrorCode.CONVERSATION_NOT_FOUND:
                raise OrchestrationError(ErrorCode.TURN_CANCELLED, "La conversación fue eliminada durante el turno.") from exc
        try:
            await store.fail_turn(conversation_id, turn_id, generation, ErrorDetail(
                code=ErrorCode(exc.code), message=str(exc), retryable=exc.retryable,
                request_id=request.request_id, retry_at=exc.retry_at,
            ))
        except StoreError:
            pass
        raise OrchestrationError(
            ErrorCode(exc.code), str(exc), retryable=exc.retryable, retry_at=exc.retry_at
        ) from exc
    except (OrchestrationError, asyncio.TimeoutError) as exc:
        code = exc.code if isinstance(exc, OrchestrationError) else ErrorCode.TURN_TIMEOUT
        trace_error_code = code.value
        message = str(exc) if isinstance(exc, OrchestrationError) else "Se agotó el tiempo del turno."
        retryable = exc.retryable if isinstance(exc, OrchestrationError) else True
        try:
            await store.fail_turn(conversation_id, turn_id, generation, ErrorDetail(
                code=code, message=message, retryable=retryable, request_id=request.request_id,
                retry_at=exc.retry_at if isinstance(exc, OrchestrationError) else None,
            ), status=TurnStatus.EXPIRED if code == ErrorCode.TURN_TIMEOUT else TurnStatus.FAILED)
        except StoreError:
            pass
        raise OrchestrationError(
            code, message, retryable=retryable,
            retry_at=exc.retry_at if isinstance(exc, OrchestrationError) else None,
        ) from exc
    except Exception as exc:
        trace_error_code = ErrorCode.INTERNAL_ERROR.value
        logger.error("turn_failed", extra={"event": "turn_failed", "error_code": "INTERNAL_ERROR"})
        try:
            await store.fail_turn(conversation_id, turn_id, generation, ErrorDetail(
                code=ErrorCode.INTERNAL_ERROR, message="No fue posible completar el análisis.", retryable=True,
                request_id=request.request_id,
            ))
        except StoreError:
            pass
        raise OrchestrationError(ErrorCode.INTERNAL_ERROR, "No fue posible completar el análisis.", retryable=True) from exc
    finally:
        if not trace_finished:
            trace.finish(status="error", error_code=trace_error_code or "TURN_FAILED")
