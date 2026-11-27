"""Agente Analista de Requerimientos: un turno Percibir → Pensar → Actuar con MCP y OpenCode.

Propiedades de agente:
- Autonomía: decide qué fuentes consultar y con qué consulta (plan), y si pide criterio al Asesor;
  se detiene al entregar las preguntas a Negocio.
- Razonamiento: clasifica la información (conocida, faltante, supuesta, ambigua) y planifica.
- Herramientas: su servidor MCP (glosario, HU similares, estándares, checklist) con RAG detrás.
- Memoria: historial del requerimiento en la sesión y Repositorio de HU (vía RAG).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import os
from datetime import datetime
from collections.abc import Collection
from typing import Any
from uuid import uuid4

from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from agentes.analista.core.agent_registry import AgentId
from agentes.analista.core.ciclo_agente import ResultadoCiclo, ejecutar_ciclo
from agentes.analista.core.ejecutor_mcp import MCPNoDisponibleError, ResultadoHerramienta
from agentes.analista.core.context_builder import build_context, render_user_prompt
from agentes.analista.core.models import (
    AgentTurnResponse,
    Analysis,
    ErrorCode,
    ErrorDetail,
    Question,
    QuestionCategory,
    QuestionState,
    SourceConsultation,
    ToolExecution,
    ToolName,
    ToolStatus,
    TurnStatus,
)
from agentes.analista.core.opencode_client import OpenCodeClient, OpenCodeClientError, OpenCodeSettings
from agentes.analista.core.output_parser import AgentOutput, VinculoVacio, format_instructions, parse_agent_output
from agentes.conocimiento.similitud import similitud_maxima
from agentes.analista.core.prompt_loader import load_prompt
from agentes.analista.core.conversation_store import ConversationStore, StoreError
from agentes.analista.core.observability import Observability


logger = logging.getLogger(__name__)
# Tiempo que se reserva para la respuesta final cuando el Analista consulta al Asesor Técnico.
RESERVA_RESPUESTA_SEGUNDO = 25.0
_TAREA_ANALISTA = (
    "Analiza el requerimiento de Negocio: identifica la necesidad, clasifica la información en conocida, "
    "faltante, supuesta y ambigua, y prepara preguntas por categoría. Decide qué fuentes te ayudan: glosario "
    "para términos de seguros, HU similares para ver qué se tuvo que aclarar antes, estándares que aplican y "
    "el checklist de vacíos (estados, permisos, validaciones, excepciones, cálculo de riesgo y comparativo)."
)

# Costura de pruebas: el ciclo agéntico (plan del modelo + ejecución MCP) se puede sustituir.
_ejecutar_ciclo = ejecutar_ciclo


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


def _ejecuciones(resultado: list[ResultadoHerramienta]) -> list[ToolExecution]:
    """Agrupa por herramienta las consultas del plan (una herramienta puede usarse con varias consultas)."""
    salida: list[ToolExecution] = []
    for nombre in ToolName:
        grupo = [item for item in resultado if item.nombre == nombre.value]
        if not grupo:
            continue
        correcto = [item for item in grupo if item.estado == "ok"]
        if correcto:
            estado, codigo = ToolStatus.OK, None
        elif any(item.estado == "timeout" for item in grupo):
            estado, codigo = ToolStatus.TIMEOUT, "MCP_TIMEOUT"
        else:
            estado, codigo = ToolStatus.ERROR, "MCP_TOOL_FAILED"
        digest = hashlib.sha256("|".join(item.digest or "" for item in correcto).encode()).hexdigest() if correcto else None
        salida.append(ToolExecution(
            tool_name=nombre, status=estado,
            result_count=sum(int(item.cantidad or 0) for item in correcto) if correcto else None,
            duration_ms=max(item.duracion_ms for item in grupo), error_code=codigo, result_digest=digest,
        ))
    return salida


def _plan_publico(ciclo: ResultadoCiclo) -> list[dict[str, Any]]:
    """Resumen del plan para la interfaz: razonamiento y consultas, sin resultados ni datos."""
    salida = []
    for paso in ciclo.paso[:3]:
        salida.append({
            "ronda": paso.ronda,
            "origen": paso.origen,
            "razonamiento": paso.razonamiento[:800],
            "consultas": [
                {"herramienta": item["herramienta"][:60], "consulta": item["consulta"][:500]}
                for item in paso.consulta[:6]
            ],
            "asesor_consultado": paso.ronda == 1 and ciclo.asesor is not None,
        })
    return salida


_PLANTILLA_VACIO: dict[str, tuple[QuestionCategory, str]] = {
    "faltante": (QuestionCategory.REQUIRED_DATA, "Falta definir: «{}». ¿Cuál es la regla o el dato correcto?"),
    "supuesta": (QuestionCategory.BUSINESS_RULES, "Se está suponiendo lo siguiente: «{}». ¿Es correcto?"),
    "ambigua": (QuestionCategory.EXPECTED_BEHAVIOR, "Esto no está claro: «{}». ¿Cómo debe entenderse?"),
}
_ETIQUETA_SUPUESTO_PO = {"faltante": "Falta definir", "supuesta": "Se supone", "ambigua": "No está claro"}
PREFIJO_PREGUNTA_VACIO = "vacio-"
# Rondas de preguntas automáticas por conversación. Sin similitud no se distingue un tema repetido de uno
# nuevo, así que solo se permite una: cada tema se le pregunta a Negocio una sola vez.
MAXIMO_RONDA_VACIO_CON_SIMILITUD = 2
MAXIMO_RONDA_VACIO_SIN_SIMILITUD = 1
UMBRAL_SIMILITUD_VACIO = float(os.environ.get("ANALISTA_UMBRAL_SIMILITUD_VACIO", "0.9"))


def _similitud_vacio(lista_punto: list[str], lista_referencia: list[str]) -> list[float] | None:
    """Costura de pruebas: similitud por significado (una llamada a Pinecone por turno)."""
    return similitud_maxima(lista_punto, lista_referencia)


def _tema_pregunta(question: Question) -> str:
    """El tema de la pregunta: en las automáticas, el punto entre «»; en las demás, la pregunta completa."""
    if question.question_id.startswith(PREFIJO_PREGUNTA_VACIO) and "«" in question.pregunta and "»" in question.pregunta:
        return question.pregunta.split("«", 1)[1].rsplit("»", 1)[0]
    return question.pregunta


def _resolver_vacio(
    analisis: Analysis,
    questions: list[Question],
    question_key: Any,
    turn_id: Any,
    vinculos: list[VinculoVacio],
) -> tuple[Analysis, list[Question], list[str]]:
    """Decide qué pasa con cada vacío: confirmado, pregunta nueva o supuesto a validar con el PO.

    1. Confirmado: el Analista lo enlazó a una pregunta respondida (por ID) o es el mismo texto de una
       pregunta automática respondida. Pasa a «conocida».
    2. Si quedan preguntas pendientes, el vacío sigue abierto: Negocio aún no responde.
    3. Si se parece por significado a algo ya respondido, no se vuelve a preguntar: va al PO.
    4. Si aún hay rondas automáticas disponibles, se convierte en pregunta para Negocio.
    5. Si no, va al PO. Así el ciclo siempre termina.
    """
    respondida_por_id = {item.question_id: item for item in questions if item.estado == QuestionState.ANSWERED}
    respondida_por_texto = {question_key(item.pregunta) for item in respondida_por_id.values()}
    vinculo_valido = {question_key(item.punto) for item in vinculos if item.question_id in respondida_por_id}
    hay_pendiente = any(item.estado == QuestionState.PENDING for item in questions)
    conocida = list(analisis.conocida)
    restante: dict[str, list[str]] = {campo: [] for campo in _PLANTILLA_VACIO}
    candidato: list[tuple[str, str]] = []
    for campo, (_, plantilla) in _PLANTILLA_VACIO.items():
        for item in getattr(analisis, campo):
            texto = item.strip()
            if question_key(texto) in vinculo_valido or question_key(plantilla.format(texto)) in respondida_por_texto:
                conocida.append(f"{texto[:970]} (confirmado por Negocio)")
            elif hay_pendiente:
                restante[campo].append(item)
            else:
                candidato.append((campo, texto))

    generada: list[Question] = []
    supuesto_po: list[str] = []
    if candidato:
        referencia = [_tema_pregunta(item) for item in respondida_por_id.values()]
        similitud = _similitud_vacio([texto for _, texto in candidato], referencia)
        ronda_previa = len({
            item.created_turn_id for item in questions if item.question_id.startswith(PREFIJO_PREGUNTA_VACIO)
        })
        maximo = MAXIMO_RONDA_VACIO_SIN_SIMILITUD if similitud is None else MAXIMO_RONDA_VACIO_CON_SIMILITUD
        existente = {question_key(item.pregunta) for item in questions}
        for indice, (campo, texto) in enumerate(candidato):
            categoria, plantilla = _PLANTILLA_VACIO[campo]
            parecido = similitud is not None and similitud[indice] >= UMBRAL_SIMILITUD_VACIO
            if parecido or ronda_previa >= maximo:
                supuesto_po.append(f"{_ETIQUETA_SUPUESTO_PO[campo]}: {texto}"[:1000])
                continue
            restante[campo].append(texto)
            pregunta = plantilla.format(texto)[:500]
            if question_key(pregunta) in existente:
                continue
            existente.add(question_key(pregunta))
            generada.append(Question(
                question_id=f"{PREFIJO_PREGUNTA_VACIO}{uuid4()}", categoria=categoria, pregunta=pregunta,
                estado=QuestionState.PENDING, created_turn_id=turn_id, updated_turn_id=None,
            ))
        if supuesto_po:
            logger.info("Vacíos enviados al PO como supuestos a validar: %d (similitud %s).",
                        len(supuesto_po), "no disponible" if similitud is None else "disponible")
    nuevo = analisis.model_copy(update={"conocida": conocida[:100], **restante})
    return nuevo, generada, supuesto_po[:50]


# Un vacío o una pregunta que el propio Analista atribuye al Asesor Técnico no se le pregunta a Negocio.
_ES_PARA_ASESOR = re.compile(r"asesor\s+t[eé]cnico", re.IGNORECASE)


def _separar_para_asesor(analisis: Analysis, lista_tema: list[str], question_key: Any) -> tuple[Analysis, list[str]]:
    """Saca del análisis los vacíos que solo se resuelven revisando el sistema; quedan para el Asesor."""
    clave = {question_key(tema) for tema in lista_tema}
    para_asesor = list(dict.fromkeys(tema.strip() for tema in lista_tema if tema.strip()))
    cambio: dict[str, list[str]] = {}
    for campo in ("faltante", "supuesta", "ambigua"):
        queda: list[str] = []
        for item in getattr(analisis, campo):
            if question_key(item) in clave or _ES_PARA_ASESOR.search(item):
                if item.strip() not in para_asesor:
                    para_asesor.append(item.strip()[:500])
            else:
                queda.append(item)
        cambio[campo] = queda
    return analisis.model_copy(update=cambio), para_asesor[:20]


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
    plan: list[dict[str, Any]] | None = None,
    respondidas: Collection[str] | None = None,
) -> AgentTurnResponse:
    def question_key(value: str) -> str:
        return " ".join(value.casefold().split()).rstrip(".,;:!?¿¡")

    # Las preguntas que Negocio respondió en este turno quedan respondidas por decisión del backend,
    # aunque el modelo las omita o las repita como pendientes.
    respondida = set(respondidas or ())
    prior_questions = [
        item.model_copy(update={"estado": QuestionState.ANSWERED}) if str(item.question_id) in respondida else item
        for item in prior_questions
    ]
    prior_by_text = {question_key(item.pregunta): item for item in prior_questions}
    questions: list[Question] = []
    seen: set[str] = set()
    para_asesor_pregunta: list[str] = []
    for item in output.preguntas:
        key = question_key(item.pregunta)
        if key in seen:
            continue
        if key not in prior_by_text and _ES_PARA_ASESOR.search(item.pregunta):
            # Pregunta que el propio Analista atribuye al Asesor: la verifica el Asesor, no Negocio.
            para_asesor_pregunta.append(item.pregunta.strip()[:500])
            seen.add(key)
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
    # Los vacíos que el modelo dejó sin preguntar se resuelven aquí; el ciclo siempre avanza o termina.
    analisis_propio, para_asesor = _separar_para_asesor(
        output.analisis, [*output.para_asesor, *para_asesor_pregunta], question_key,
    )
    analisis, generadas, supuesto_po = _resolver_vacio(
        analisis_propio, questions, question_key, turn_id, output.vinculos,
    )
    questions.extend(generadas[:50 - len(questions)])
    ready = not (analisis.faltante or analisis.supuesta or analisis.ambigua)
    ready = ready and not any(item.estado == QuestionState.PENDING for item in questions)
    return AgentTurnResponse(
        conversation_id=conversation_id,
        request_id=request_id,
        turn_id=turn_id,
        estado="completado",
        respuesta_markdown=output.respuesta_markdown.strip(),
        analisis=analisis,
        preguntas=questions,
        fuentes_consultadas=sources[:4],
        listo_para_redactor=ready,
        supuesto_validar_po=supuesto_po,
        para_asesor=para_asesor,
        beneficios=output.beneficios,
        limitaciones=limitations[:10],
        duracion_ms=duration_ms,
        prompt_version=load_prompt().version,
        plan_agente=plan or [],
    )


async def run_turn(
    store: ConversationStore,
    conversation_id: Any,
    request: Any,
    *,
    observability: Observability | None = None,
    respondidas: Collection[str] | None = None,
) -> AgentTurnResponse:
    """Execute one real turn; every OpenCode session is deleted in a finally block.

    ``respondidas``: ids de preguntas que Negocio respondió en este turno; quedan marcadas como respondidas.
    """
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
        executions: list[ToolExecution] = []
        limitations: list[str] = []
        plan: list[dict[str, Any]] = []
        from agentes.equipo.asesor_tecnico.asesor_tecnico_service import AsesorTecnicoService

        asesor = AsesorTecnicoService()

        async def consultar_asesor(pregunta: str, contexto: str) -> dict[str, Any]:
            disponible = deadline - asyncio.get_running_loop().time() - RESERVA_RESPUESTA_SEGUNDO
            if disponible < 10:
                raise TimeoutError("No queda tiempo para consultar al Asesor Técnico en este turno.")
            return await asyncio.wait_for(asesor.consultar(pregunta, contexto), timeout=disponible)

        async def invoke_opencode(message_text: str) -> AgentOutput:
            async with OpenCodeClient() as client:
                client.set_deadline(deadline)
                await client.server_info()
                agent = await client.verify_agent("analista")
                model = await client.select_model(agent)
                operation = trace.operation(
                    kind="generation",
                    name="opencode-generation",
                    metadata={"provider": model["providerID"], "model": model["id"]},
                )
                try:
                    title = f"analista-{str(conversation_id)[:8]}-{str(turn_id)[:8]}"
                    async with client.session(title=title, model=model) as session:
                        session_id = session["id"]
                        await store.set_opencode_session(conversation_id, turn_id, generation, session_id)
                        # Pensar y actuar: el Analista planifica sus consultas MCP y el backend las ejecuta.
                        memoria = build_context(record, message_text, [], [])
                        try:
                            ciclo: ResultadoCiclo = await _ejecutar_ciclo(
                                agent_id=AgentId.ANALYST, client=client, session_id=session_id, deadline=deadline,
                                tarea=_TAREA_ANALISTA,
                                contexto=json.dumps(memoria.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")),
                                consulta_base=message_text, trace=trace, consultor_asesor=consultar_asesor,
                            )
                        except MCPNoDisponibleError as exc:
                            raise OrchestrationError(
                                ErrorCode.MCP_UNAVAILABLE, "No fue posible consultar las fuentes autorizadas.", retryable=True,
                            ) from exc
                        executions.extend(_ejecuciones(ciclo.resultado))
                        limitations.extend(dict.fromkeys(ciclo.limitacion))
                        plan.extend(_plan_publico(ciclo))
                        for execution in executions:
                            await store.add_tool_execution(conversation_id, turn_id, generation, execution)
                        payload = build_context(record, message_text, ciclo.observacion(), limitations)
                        prompt_text = render_user_prompt(payload, format_instructions())
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

        output = await _within_deadline(RunnableLambda(invoke_opencode).ainvoke(request.message), deadline)
        if asyncio.get_running_loop().time() >= deadline:
            raise OrchestrationError(ErrorCode.TURN_TIMEOUT, "Se agotó el tiempo del turno.", retryable=True)

        duration_ms = max(0, int((timeout_seconds - max(0, deadline - asyncio.get_running_loop().time())) * 1000))
        # Puede consultar Pinecone (similitud): se ejecuta fuera del event loop.
        response = await asyncio.to_thread(
            _to_response,
            output,
            conversation_id=conversation_id,
            request_id=request.request_id,
            turn_id=turn_id,
            prior_questions=record.questions,
            tool_executions=executions,
            limitations=limitations,
            duration_ms=duration_ms,
            plan=plan,
            respondidas=respondidas,
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
        except StoreError as store_error:
            logger.warning("turn_failure_not_recorded", extra={"event": "turn_failure_not_recorded", "error_code": store_error.code.value})
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
        except StoreError as store_error:
            logger.warning("turn_failure_not_recorded", extra={"event": "turn_failure_not_recorded", "error_code": store_error.code.value})
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
        except StoreError as store_error:
            logger.warning("turn_failure_not_recorded", extra={"event": "turn_failure_not_recorded", "error_code": store_error.code.value})
        raise OrchestrationError(ErrorCode.INTERNAL_ERROR, "No fue posible completar el análisis.", retryable=True) from exc
    finally:
        if not trace_finished:
            trace.finish(status="error", error_code=trace_error_code or "TURN_FAILED")
