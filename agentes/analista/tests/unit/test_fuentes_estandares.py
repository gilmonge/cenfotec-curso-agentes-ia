"""El archivo estandares.json de Proyecto Contexto alimenta la herramienta consultar_estandares y el checklist."""
import re
import uuid

from agentes.analista.mcp import tools
from agentes.analista.mcp.repositories import load_sources

# Nombres propios que no deben aparecer en las fuentes; se arman por partes para no escribirlos en el código.
PALABRAS_PROHIBIDAS = tuple("".join(partes) for partes in (("ka", "dsi"), ("po", "pular seg"), ("fc", "sc"), ("it", "op")))

REQUERIMIENTO_CAMPO = (
    "Agregar un campo monto de prima en moneda dólares al formulario de cliente "
    "y mostrarlo en la tabla de resultados"
)


def test_standards_load_with_unique_ids_and_valid_contract_fields():
    entries = load_sources()["estandares"]
    ids = [entry["id"] for entry in entries]
    assert len(ids) == len(set(ids))
    for entry in entries:
        model = tools.StandardEntry.model_validate({key: entry[key] for key in tools.StandardEntry.model_fields})
        assert model.regla and model.referencia
    for expected in ("FORM-01", "FORM-08", "TABL-02", "BOTO-02", "BOTO-07", "MENS-01", "MENS-05", "ADJU-01", "ADJU-06", "IDEN-02", "A11Y-01", "CODI-03", "SIM-POL-01", "SIM-SEG-01", "SIM-PSN-01"):
        assert expected in ids


def test_simulated_standards_are_always_flagged_for_confirmation():
    simulated = [entry for entry in load_sources()["estandares"] if entry["id"].startswith("SIM-")]
    assert simulated
    for entry in simulated:
        assert entry["regla"].startswith("[SIMULADO, confirmar con Negocio]")


def test_field_change_query_returns_form_and_numeric_standards():
    result = tools.consultar_estandares(REQUERIMIENTO_CAMPO, 5)
    ids = {item.id for item in result.estandares}
    assert result.total == len(result.estandares) <= 5
    assert ids & {"FORM-05", "FORM-08", "FORM-01"}


def _descripciones(result):
    return [item.descripcion for category in result.categorias for item in category.items]


def test_checklist_ids_are_unique_guids():
    entries = load_sources()["checklist"]
    ids = [entry["id"] for entry in entries]
    assert len(ids) == len(set(ids))
    for value in ids:
        assert str(uuid.UUID(value)) == value


def test_checklist_asks_about_field_definition_when_a_form_field_changes():
    result = tools.aplicar_checklist_vacios(REQUERIMIENTO_CAMPO, 5)
    assert "nombre exacto, tipo de dato" in " ".join(_descripciones(result))


def test_checklist_is_general_and_covers_required_fields_and_permissions():
    texto = " ".join(entry["descripcion"] for entry in load_sources()["checklist"])
    assert "Qué campos son obligatorios" in texto
    assert "Qué roles pueden ver y ejecutar" in texto
    assert len(load_sources()["checklist"]) <= 25


def test_checklist_scope_is_limited_to_policies_persons_and_security():
    texto = " ".join(entry["descripcion"] + " ".join(entry["terminos"]) for entry in load_sources()["checklist"]).casefold()
    for fuera_de_alcance in ("carga masiva", "cargas masivas", "plantilla", "cumplimiento", "listas de control", "riesgo", "comparativo", "lote"):
        assert fuera_de_alcance not in texto


def test_module_context_skill_is_flagged_and_excludes_secrets():
    entries = [e for e in load_sources()["estandares"] if e["id"].startswith("MODU-")]
    assert len(entries) >= 9
    for entry in entries:
        assert entry["regla"].startswith("[CONTEXTO simulado")
    text = (tools.__file__ and "".join(e["regla"] + e["referencia"] for e in entries)).lower()
    for forbidden in ("password", "connectionstring", "apitransaccional", "secret"):
        assert forbidden not in text


def test_sources_do_not_name_real_systems_or_companies():
    for fuente in load_sources().values():
        texto = " ".join(str(entry) for entry in fuente).lower()
        for prohibido in PALABRAS_PROHIBIDAS:
            assert prohibido not in texto


def test_module_context_covers_only_policies_persons_and_security():
    result = tools.consultar_estandares("Cambiar los roles y permisos de los usuarios", 5)
    assert "MODU-07" in {item.id for item in result.estandares}
    texto = " ".join(e["regla"] + e["id"] for e in load_sources()["estandares"] if e["id"].startswith(("MODU-", "SIM-"))).casefold()
    for fuera_de_alcance in ("carga masiva", "cargas masivas", "cumplimiento", "listas de control", "cálculo de riesgo", "comparativo"):
        assert fuera_de_alcance not in texto


def test_glossary_entries_are_valid_unique_and_neutral():
    entries = load_sources()["glosario"]
    terms = [entry["termino"].casefold() for entry in entries]
    assert len(terms) == len(set(terms)) >= 30
    for entry in entries:
        tools.GlossaryEntry.model_validate({key: entry[key] for key in tools.GlossaryEntry.model_fields})
        assert entry["terminos"]
    texto = " ".join(entry["termino"] + entry["definicion"] for entry in entries).lower()
    for prohibido in PALABRAS_PROHIBIDAS:
        assert prohibido not in texto


def test_glossary_finds_policy_person_and_security_terms():
    result = tools.consultar_glosario("Agregar un campo a la póliza hija de la póliza madre", 5)
    assert "póliza hija" in " ".join(item.termino for item in result.definiciones)
    assert 1 <= result.total <= 5
    result = tools.consultar_glosario("Asignar un rol y un permiso al usuario", 5)
    assert {"rol", "usuario"} & {item.termino for item in result.definiciones}


def test_glossary_scope_excludes_loads_and_compliance():
    texto = " ".join(entry["termino"] + entry["definicion"] + " ".join(entry["terminos"]) for entry in load_sources()["glosario"]).casefold()
    for fuera_de_alcance in ("carga masiva", "cargas", "cumplimiento", "lista de control", "cálculo de riesgo", "comparativo", "lote"):
        assert fuera_de_alcance not in texto
