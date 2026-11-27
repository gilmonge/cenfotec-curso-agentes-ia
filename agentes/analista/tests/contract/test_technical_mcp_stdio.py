import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.asyncio
async def test_technical_server_exposes_only_read_only_allowed_sources():
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agentes.equipo.asesor_tecnico.servidor_mcp"],
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            by_name = {tool.name: tool for tool in listed.tools}
            assert set(by_name) == {
                "consultar_estandares", "consultar_codigo_demo", "leer_archivo_codigo", "buscar_hu_similares",
                "buscar_referencias_codigo",
            }
            parameter = {"leer_archivo_codigo": {"ruta"}, "buscar_referencias_codigo": {"termino"}}
            for name, tool in by_name.items():
                expected = parameter.get(name, {"consulta", "limite"})
                assert set(tool.input_schema["properties"]) == expected
                assert tool.input_schema["additionalProperties"] is False
                assert tool.output_schema["additionalProperties"] is False

            found = await session.call_tool("buscar_referencias_codigo", {"termino": "telefono"})
            assert not found.is_error
            assert {
                "ejemplos/polizas_demo/clientes/pantalla_cliente.py",
                "ejemplos/polizas_demo/notificaciones/aviso_cliente.py",
                "ejemplos/polizas_demo/reportes/exportacion_cliente.py",
                "ejemplos/polizas_demo/cargas/carga_cliente.py",
            } <= set(found.structured_content["archivos"])
            invalid_term = await session.call_tool("buscar_referencias_codigo", {"termino": "x"})
            assert invalid_term.is_error

            opened = await session.call_tool("leer_archivo_codigo", {"ruta": "servicios/primas.py"})
            assert not opened.is_error
            assert opened.structured_content["encontrado"] is True
            assert opened.structured_content["archivo"]["source_ref"] == "ejemplos/polizas_demo/servicios/primas.py"
            for unsafe in ("../../agentes/analista/core/opencode_client.py", "/etc/passwd", "servicios/primas.txt"):
                blocked = await session.call_tool("leer_archivo_codigo", {"ruta": unsafe})
                assert not blocked.is_error
                assert blocked.structured_content["encontrado"] is False

            result = await session.call_tool("consultar_codigo_demo", {
                "consulta": "póliza prima renovación pago cobertura", "limite": 12,
            })
            assert not result.is_error
            refs = {item["source_ref"] for item in result.structured_content["fuentes"]}
            assert "ejemplos/polizas_demo/servicios/primas.py" in refs
            assert "ejemplos/polizas_demo/mapa_dependencias.md" in refs
            assert all(ref.startswith("ejemplos/polizas_demo/") for ref in refs)
            assert result.structured_content["total"] == len(refs)

            standards = await session.call_tool("consultar_estandares", {
                "consulta": "validación de datos y mensajes", "limite": 5,
            })
            assert not standards.is_error
            assert standards.structured_content["total"] == len(standards.structured_content["estandares"])
            assert standards.structured_content["contenido_no_confiable"] is True

            no_results = await session.call_tool("consultar_codigo_demo", {
                "consulta": "sin coincidencias xyzzy", "limite": 12,
            })
            assert not no_results.is_error
            assert no_results.structured_content["fuentes"] == []

            invalid = await session.call_tool("consultar_codigo_demo", {
                "consulta": "póliza", "ruta": "../../secreto.txt",
            })
            assert invalid.is_error


@pytest.mark.asyncio
@pytest.mark.parametrize(("module", "expected"), [
    ("agentes.equipo.redactor_revisor.servidor_mcp", {"consultar_estandares", "aplicar_checklist_vacios", "buscar_hu_similares"}),
    ("agentes.equipo.gestor_cambios.servidor_mcp", {"buscar_hu_similares", "consultar_lecciones", "aplicar_checklist_vacios"}),
])
async def test_each_role_server_exposes_only_its_allowlisted_tools(module, expected):
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", module], cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            assert {tool.name for tool in listed.tools} == expected
            for tool in listed.tools:
                assert tool.input_schema["additionalProperties"] is False
            result = await session.call_tool("aplicar_checklist_vacios", {"consulta": "validación de vigencia", "limite": 5})
            assert not result.is_error
            assert result.structured_content["contenido_no_confiable"] is True
