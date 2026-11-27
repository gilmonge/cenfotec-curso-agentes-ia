"""Conexión de un agente con su servidor MCP de solo lectura.

Cada rol tiene su propio servidor (proceso stdio). Al abrir la sesión se verifica que
el servidor exponga exactamente las herramientas permitidas para ese rol; si expone
otra cosa, la sesión se rechaza. Cada invocación tiene tiempo límite, se registra en
la traza y su resultado se trata como dato no confiable.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain.mcp import MCPAdapter

from agentes.analista.core.agent_registry import (
    AgentId, allowed_mcp_tools, authorize_mcp_tool, definicion_de, tool_namespace,
)

logger = logging.getLogger(__name__)

TIEMPO_HERRAMIENTA_SEGUNDO = 8.0
LIMITE_RESULTADO = 5


def servidor_del_rol(agent_id: AgentId) -> Path | Any:
    """stdio (proceso aparte, predeterminado) o memoria (mismo proceso; pruebas y diagnóstico).

    El servidor de cada agente está en su carpeta (``agentes/equipo/<id>/servidor_mcp.py``).
    ``ANALISTA_MCP_TRANSPORTE=memoria`` conecta el cliente MCP con el servidor dentro del
    mismo proceso: el protocolo MCP es el mismo, solo cambia el transporte.
    """
    if os.environ.get("ANALISTA_MCP_TRANSPORTE", "stdio").strip().casefold() != "memoria":
        return definicion_de(agent_id).ruta_servidor_mcp
    from agentes.analista.mcp.tools import servidor_del_agente

    return servidor_del_agente(agent_id)


class MCPNoDisponibleError(RuntimeError):
    """El servidor MCP del rol no arrancó o no expone el conjunto autorizado."""


@dataclass(frozen=True, slots=True)
class HerramientaDisponible:
    nombre: str
    descripcion: str
    parametro: str  # "consulta", "ruta" o "termino"


@dataclass(slots=True)
class ResultadoHerramienta:
    nombre: str
    consulta: str
    estado: str  # ok | timeout | error | rechazada
    datos: Any = None
    cantidad: int | None = None
    duracion_ms: int = 0
    digest: str | None = None
    detalle: str | None = None

    def como_observacion(self) -> dict[str, Any]:
        return {"nombre": self.nombre, "consulta": self.consulta, "datos": self.datos, "resultados": self.cantidad}


@dataclass(slots=True)
class _Estado:
    adaptador: Any = None
    herramienta: dict[str, Any] = field(default_factory=dict)


def desempaquetar(value: Any) -> Any:
    """Normaliza las variantes que devuelven MCP/LangChain a un dict o lista JSON."""
    if isinstance(value, tuple) and len(value) == 2 and value[1] is not None:
        value = value[1]
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
        return desempaquetar(artifact)
    if isinstance(value, str):
        return json.loads(value)
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


def contar_resultado(datos: Any) -> int:
    if not isinstance(datos, dict):
        return 0
    if isinstance(datos.get("total"), int):
        return int(datos["total"])
    if "encontrado" in datos:
        return 1 if datos.get("encontrado") else 0
    if isinstance(datos.get("coincidencias"), list):
        return len(datos["coincidencias"])
    return 0


def _parametro(tool: Any) -> str:
    """Nombre del parámetro de texto de la herramienta: consulta (búsqueda), ruta (archivo) o termino (referencia)."""
    argumento = getattr(tool, "args", None) or {}
    for nombre in ("ruta", "termino"):
        if nombre in argumento:
            return nombre
    return "consulta"


class SesionMCP:
    """Sesión con el servidor MCP de un rol; úsese como ``async with``."""

    def __init__(self, agent_id: AgentId, *, trace: Any = None, servidor: Path | Any | None = None) -> None:
        self.agent_id = AgentId(agent_id)
        self._trace = trace
        self._servidor = servidor or servidor_del_rol(self.agent_id)
        self._estado = _Estado()

    async def __aenter__(self) -> "SesionMCP":
        try:
            self._estado.adaptador = MCPAdapter(self._servidor)
            await self._estado.adaptador.__aenter__()
            listado = await self._estado.adaptador.list_tools()
        except Exception as exc:
            await self._cerrar()
            logger.warning("mcp_no_disponible", extra={"event": "mcp_no_disponible", "agent": self.agent_id.value, "error": type(exc).__name__})
            raise MCPNoDisponibleError("No fue posible iniciar el servidor MCP del agente.") from exc
        por_nombre = {tool.name: tool for tool in listado}
        if set(por_nombre) != set(allowed_mcp_tools(self.agent_id)):
            await self._cerrar()
            raise MCPNoDisponibleError("El servidor MCP no expone exactamente las herramientas autorizadas para el rol.")
        self._estado.herramienta = por_nombre
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self._cerrar()

    async def _cerrar(self) -> None:
        adaptador, self._estado.adaptador = self._estado.adaptador, None
        if adaptador is None:
            return
        try:
            await adaptador.__aexit__(None, None, None)
        except Exception as exc:
            logger.warning("mcp_cierre_fallido", extra={"event": "mcp_cierre_fallido", "error": type(exc).__name__})

    def catalogo(self) -> list[HerramientaDisponible]:
        salida: list[HerramientaDisponible] = []
        for nombre in sorted(self._estado.herramienta):
            tool = self._estado.herramienta[nombre]
            parametro = _parametro(tool)
            salida.append(HerramientaDisponible(nombre, (getattr(tool, "description", "") or "")[:300], parametro))
        return salida

    async def invocar(self, nombre: str, consulta: str, *, limite: int = LIMITE_RESULTADO) -> ResultadoHerramienta:
        inicio = time.monotonic()
        tool = self._estado.herramienta.get(nombre)
        try:
            namespace = tool_namespace(nombre)
            authorize_mcp_tool(self.agent_id, nombre, namespace)
        except PermissionError:
            return ResultadoHerramienta(nombre, consulta, "rechazada", detalle="Herramienta no permitida para el rol.")
        if tool is None:
            return ResultadoHerramienta(nombre, consulta, "rechazada", detalle="El servidor no expone la herramienta.")
        parametro = _parametro(tool)
        argumento = {parametro: consulta} if parametro != "consulta" else {"consulta": consulta, "limite": limite}
        operacion = self._trace.operation(
            kind="tool", name=f"mcp-{nombre}", metadata={"tool_name": nombre, "agent": self.agent_id.value},
        ) if self._trace else None
        try:
            crudo = await asyncio.wait_for(tool.ainvoke(argumento), timeout=TIEMPO_HERRAMIENTA_SEGUNDO)
            datos = desempaquetar(crudo)
            cantidad = contar_resultado(datos)
            if operacion:
                operacion.finish(status="ok", metadata={"result_count": cantidad})
            return ResultadoHerramienta(
                nombre, consulta, "ok", datos=datos, cantidad=cantidad,
                duracion_ms=max(0, int((time.monotonic() - inicio) * 1000)),
                digest=hashlib.sha256(json.dumps(datos, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            )
        except asyncio.TimeoutError:
            if operacion:
                operacion.finish(status="timeout", error_code="MCP_TIMEOUT")
            return ResultadoHerramienta(nombre, consulta, "timeout", duracion_ms=max(0, int((time.monotonic() - inicio) * 1000)))
        except asyncio.CancelledError:
            if operacion:
                operacion.finish(status="cancelled", error_code="TURN_CANCELLED")
            raise
        except Exception as exc:
            if operacion:
                operacion.finish(status="error", error_code="MCP_TOOL_FAILED")
            logger.warning("mcp_herramienta_fallida", extra={"event": "mcp_herramienta_fallida", "tool_name": nombre, "error": type(exc).__name__})
            return ResultadoHerramienta(nombre, consulta, "error", duracion_ms=max(0, int((time.monotonic() - inicio) * 1000)))
