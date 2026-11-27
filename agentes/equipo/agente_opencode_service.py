"""Clase base de los agentes que responden con OpenCode (patrón Template Method).

El ciclo es el mismo para todos y se escribe una sola vez aquí:

1. cargar el prompt del agente y abrir el cliente de OpenCode con su plazo;
2. verificar la versión de OpenCode, el agente configurado y elegir el modelo;
3. abrir una sesión y ejecutar el ciclo planificar → consultar por MCP (evidencia del agente);
4. armar el mensaje final, enviarlo y esperar la respuesta;
5. interpretar la salida y, si no cumple el contrato, pedir una corrección en la misma sesión (una vez).

Cada agente solo aporta lo que es suyo: la tarea, el contexto, cómo armar el mensaje con la evidencia y cómo
interpretar (y validar) la salida. Ver ``RedactorRevisorService`` como ejemplo.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar

from agentes.analista.core.agent_registry import AgentId, get_agent_spec
from agentes.analista.core.ciclo_agente import ConsultorAsesor, ResultadoCiclo, ejecutar_ciclo, pedir_reparacion
from agentes.analista.core.ejecutor_mcp import SesionMCP
from agentes.analista.core.opencode_client import OpenCodeClient, OpenCodeClientError
from agentes.analista.core.opencode_compat import is_supported_opencode_version
from agentes.analista.core.prompt_loader import PromptLoadError

logger = logging.getLogger(__name__)

_Salida = TypeVar("_Salida")


class SalidaAgenteInvalidaError(RuntimeError):
    """La salida del modelo no cumple el contrato del agente. Los errores de salida de cada agente heredan
    de esta clase para que la base sepa cuándo pedir una corrección."""


class PreparacionAgenteError(RuntimeError):
    """No se pudo cargar el prompt o preparar el contrato del agente."""


@dataclass(frozen=True, slots=True)
class Turno:
    """Lo que el agente tiene a mano para armar su mensaje: el cliente, la sesión y la evidencia del ciclo."""

    client: Any
    session_id: str
    deadline: float
    ciclo: ResultadoCiclo | None


# Estrategia opcional para reemplazar la consulta MCP (por ejemplo, fuentes ya recuperadas en las pruebas).
ConsultaPropia = Callable[[Turno], Awaitable[Any]]


class AgenteOpenCodeService(Generic[_Salida]):
    """Base de un agente: las subclases definen ``agente`` y ``titulo_sesion`` y llaman a ``_ejecutar_turno``."""

    agente: ClassVar[AgentId]
    titulo_sesion: ClassVar[str]
    # Si la salida no cumple el contrato, se pide una corrección en la misma sesión (una vez).
    corregir_salida: ClassVar[bool] = True
    # Error que ve quien llama cuando no se puede cargar el prompt (cada agente puede usar el suyo).
    error_preparacion: ClassVar[type[Exception]] = PreparacionAgenteError

    def __init__(self, client_factory: Any | None = None, *, sesion_mcp_factory: Any | None = None) -> None:
        # Se resuelven al crear el servicio para que las pruebas puedan inyectar dobles sin credenciales.
        self._client_factory = client_factory or OpenCodeClient
        self._sesion_mcp_factory = sesion_mcp_factory or SesionMCP

    @property
    def prompt(self):
        try:
            return get_agent_spec(self.agente).prompt
        except (PromptLoadError, ValueError, TypeError) as exc:
            raise self.error_preparacion("No se pudo cargar el prompt del agente.") from exc

    async def _ejecutar_turno(
        self,
        *,
        tarea: str,
        contexto: str,
        consulta_base: str,
        armar_mensaje: Callable[[Turno], str],
        interpretar: Callable[[dict[str, Any], Turno], _Salida],
        maximo_ronda: int | None = None,
        consultor_asesor: ConsultorAsesor | None = None,
        consulta_propia: ConsultaPropia | None = None,
    ) -> _Salida:
        prompt = self.prompt
        async with self._client_factory(prompt=prompt, agent_id=self.agente) as client:
            deadline = asyncio.get_running_loop().time() + client.settings.turn_timeout_seconds
            client.set_deadline(deadline)
            server = await client.server_info()
            if not is_supported_opencode_version(server.get("version")):
                raise OpenCodeClientError("OPENCODE_INCOMPATIBLE", "La versión de OpenCode no es compatible.")
            agent = await client.verify_agent(self.agente)
            model = await client.select_model(agent)
            async with client.session(title=self.titulo_sesion, model=model) as session:
                base = Turno(client=client, session_id=session["id"], deadline=deadline, ciclo=None)
                if consulta_propia is not None:
                    ciclo = await consulta_propia(base)
                else:
                    # Pensar y actuar: el agente decide qué consultar en su servidor MCP (RAG detrás).
                    ciclo = await ejecutar_ciclo(
                        agent_id=self.agente, client=client, session_id=session["id"], deadline=deadline,
                        tarea=tarea, contexto=contexto, consulta_base=consulta_base, maximo_ronda=maximo_ronda,
                        consultor_asesor=consultor_asesor, sesion_mcp_factory=self._sesion_mcp_factory,
                    )
                turno = Turno(client=client, session_id=session["id"], deadline=deadline, ciclo=ciclo)
                admision = await client.submit_prompt(session["id"], armar_mensaje(turno))
                generado = await client.wait_for_assistant(
                    session["id"], deadline=deadline, after=admision.get("time", {}).get("created"),
                )
                try:
                    return interpretar(generado, turno)
                except SalidaAgenteInvalidaError as exc:
                    if not self.corregir_salida:
                        raise
                    # No se registra el contenido del modelo, solo el motivo que escribe el backend.
                    logger.warning("%s: salida inválida (%s); se pide una corrección.", self.agente.value, exc)
                    corregido = await pedir_reparacion(client, session["id"], str(exc), deadline)
                    if corregido is None:
                        raise
        return interpretar(corregido, turno)
