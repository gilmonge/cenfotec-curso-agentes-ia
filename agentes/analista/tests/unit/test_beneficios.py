"""Los beneficios esperados los propone el agente y son opcionales."""
import json

from agentes.analista.core.output_parser import parse_agent_output

BASE = {
    "respuesta_markdown": "### Resumen\nTexto",
    "analisis": {"conocida": ["a"], "faltante": [], "supuesta": [], "ambigua": []},
    "preguntas": [],
    "listo_para_redactor": True,
}


def test_benefits_are_optional_and_default_to_empty():
    assert parse_agent_output(json.dumps(BASE)).beneficios == []


def test_benefits_are_cleaned_and_kept():
    salida = parse_agent_output(json.dumps({**BASE, "beneficios": ["  Trazabilidad de bloqueos  ", "", "Menos accesos no autorizados"]}))
    assert salida.beneficios == ["Trazabilidad de bloqueos", "Menos accesos no autorizados"]
