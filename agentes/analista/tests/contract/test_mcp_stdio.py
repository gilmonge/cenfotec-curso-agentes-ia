import asyncio
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.asyncio
async def test_stdio_server_exposes_exact_allowlist_and_validated_contracts():
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agentes.analista.mcp.server"],
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = sorted(tool.name for tool in listed.tools)
            assert names == sorted(
                [
                    "consultar_glosario",
                    "buscar_hu_similares",
                    "consultar_estandares",
                    "aplicar_checklist_vacios",
                ]
            )
            for tool in listed.tools:
                assert tool.input_schema["additionalProperties"] is False
                assert tool.input_schema["properties"]["consulta"]["maxLength"] == 4000
                assert tool.input_schema["properties"]["limite"]["maximum"] == 5
                assert tool.output_schema["additionalProperties"] is False

            first = await session.call_tool("consultar_glosario", {"consulta": "plazo"})
            second = await session.call_tool("consultar_glosario", {"consulta": "plazo"})
            assert not first.is_error
            assert first.structured_content == second.structured_content
            assert first.structured_content["total"] == len(first.structured_content["definiciones"])
            assert first.structured_content["contenido_no_confiable"] is True

            for name in names[1:]:
                result = await session.call_tool(name, {"consulta": "fecha datos regla usuario validación"})
                assert not result.is_error
                assert result.structured_content["total"] >= 0
                assert result.structured_content["contenido_no_confiable"] is True

            invalid = await session.call_tool("consultar_glosario", {"consulta": " ", "limite": 0})
            assert invalid.is_error


@pytest.mark.asyncio
async def test_stdio_server_returns_empty_success_for_unmatched_query():
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agentes.analista.mcp.server"],
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("consultar_glosario", {"consulta": "sin coincidencias xyzzy"})
            assert not result.is_error
            assert result.structured_content["definiciones"] == []
            assert result.structured_content["total"] == 0
