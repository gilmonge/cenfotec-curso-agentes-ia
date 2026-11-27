"""Escenarios de docs/evaluacion-asesor-tecnico.md: la evidencia de impacto debe ser alcanzable por MCP.

Se verifica la parte determinista: con los términos del escenario, la herramienta
buscar_referencias_codigo encuentra todos los archivos que el Asesor debería reportar.
"""
from __future__ import annotations

import pytest

from agentes.analista.mcp.technical_tools import buscar_referencias_codigo

RAIZ = "ejemplos/polizas_demo/"

ESCENARIO = {
    "telefono_opcional": (
        ("telefono", "TEL"),
        {"clientes/pantalla_cliente.py", "cargas/carga_cliente.py", "notificaciones/aviso_cliente.py",
         "reportes/exportacion_cliente.py", "clientes/modelo_cliente.py"},
    ),
    "formato_fecha_nacimiento": (
        ("fecha_nacimiento", "FORMATO_FECHA", "FNAC"),
        {"clientes/modelo_cliente.py", "clientes/pantalla_cliente.py", "reportes/exportacion_cliente.py",
         "cargas/carga_cliente.py"},
    ),
    "correo_secundario": (
        ("correo", "EMAIL"),
        {"clientes/modelo_cliente.py", "clientes/pantalla_cliente.py", "notificaciones/aviso_cliente.py",
         "reportes/exportacion_cliente.py", "cargas/carga_cliente.py"},
    ),
}


@pytest.mark.parametrize("nombre", sorted(ESCENARIO))
def test_reference_search_reaches_every_expected_module(nombre):
    lista_termino, esperado = ESCENARIO[nombre]
    encontrado: set[str] = set()
    for termino in lista_termino:
        resultado = buscar_referencias_codigo(termino)
        assert all(ref.contenido_no_confiable for ref in resultado.coincidencias)
        encontrado |= {archivo.removeprefix(RAIZ) for archivo in resultado.archivos}
    assert esperado <= encontrado, f"faltan: {sorted(esperado - encontrado)}"


def test_format_trap_is_only_visible_by_searching_the_field_not_the_constant():
    por_constante = {a.removeprefix(RAIZ) for a in buscar_referencias_codigo("FORMATO_FECHA").archivos}
    por_campo = {a.removeprefix(RAIZ) for a in buscar_referencias_codigo("fecha_nacimiento").archivos}

    assert "cargas/carga_cliente.py" not in por_constante
    assert "cargas/carga_cliente.py" in por_campo


def test_reference_search_returns_line_numbers_and_is_case_insensitive():
    resultado = buscar_referencias_codigo("tel")
    lineas = {(ref.source_ref.removeprefix(RAIZ), ref.linea) for ref in resultado.coincidencias}

    assert any(archivo == "cargas/carga_cliente.py" for archivo, _ in lineas)
    assert all(linea >= 1 for _, linea in lineas)
    assert resultado.total >= len(resultado.coincidencias)


@pytest.mark.parametrize("termino", ["x", "", "  ", "a\nb", "y" * 81])
def test_reference_search_rejects_unbounded_terms(termino):
    with pytest.raises(ValueError):
        buscar_referencias_codigo(termino)
