"""Seguridad, esquemas y trazabilidad de fuentes autorizadas para RAG."""
from __future__ import annotations

import asyncio
import json

import pytest

from agentes.analista.mcp.tools import mcp
from agentes.conocimiento.sources import (
    AUTHORIZED_NAMESPACES,
    AuthorizedSourceLoader,
    SourceError,
    SourceRecord,
    validate_namespace,
)


def test_reads_real_json_files_and_validates_all_records():
    loader = AuthorizedSourceLoader()
    records = loader.load_json_sources()
    assert len(records) == 136
    assert {record.namespace for record in records} == {
        "glosario", "estandares", "checklist", "hu_aprobadas",
    }
    assert all(record.text.startswith("{") and record.source_ref.startswith("agentes/analista/fuentes/") for record in records)
    assert all(record.source_kind == "simulated_fixture" for record in records if record.namespace != "hu_aprobadas")
    expected = {
        "glosario.json": "glosario", "estandares.json": "estandares",
        "checklist_vacios.json": "checklist", "hu_similares.json": "hu_aprobadas",
    }
    assert {record.source_ref.split("/")[-1].split("#")[0]: record.namespace for record in records} == expected


def test_similar_story_json_is_simulated_and_never_approved():
    records = AuthorizedSourceLoader().load_json_sources()
    refs = [record for record in records if record.source_ref.startswith("agentes/analista/fuentes/hu_similares.json#")]
    assert len(refs) == 3
    assert all(record.namespace == "hu_aprobadas" for record in refs)
    assert all(record.source_kind == "simulated_reference" and record.approval_status is None for record in refs)


def test_only_six_namespaces_and_four_existing_mcp_tools_are_exposed():
    assert AUTHORIZED_NAMESPACES == {"glosario", "estandares", "checklist", "hu_aprobadas", "lecciones", "codigo"}
    tools = asyncio.run(mcp.list_tools())
    assert {tool.name for tool in tools} == {
        "consultar_glosario", "buscar_hu_similares", "consultar_estandares", "aplicar_checklist_vacios",
    }


@pytest.mark.parametrize("namespace", ["hu", "historias", "admin", "", "codigo/../hu_aprobadas"])
def test_rejects_unauthorized_namespace(namespace):
    with pytest.raises(SourceError, match="Namespace"):
        validate_namespace(namespace)


def test_rejects_unauthorized_json_source_and_extra_fields(tmp_path):
    root = tmp_path / "project"
    sources = root / "agentes" / "analista" / "fuentes"
    sources.mkdir(parents=True)
    (sources / "glosario.json").write_text(
        json.dumps([{"termino": "x", "definicion": "y", "fuente": "simulada", "terminos": [], "path": "secreto"}]),
        encoding="utf-8",
    )
    loader = AuthorizedSourceLoader(root)
    with pytest.raises(SourceError, match="Fuente"):
        loader.load_json_source("historias_reales.json")
    with pytest.raises(SourceError, match="esquema"):
        loader.load_json_sources(fuentes_root=sources)
    with pytest.raises(SourceError):
        loader.load_json_sources(fuentes_root=tmp_path)


def test_reads_only_fictional_py_and_md_without_importing_or_executing(tmp_path):
    project = tmp_path / "project"
    root = project / "ejemplos" / "polizas_demo"
    root.mkdir(parents=True)
    marker = tmp_path / "executed.txt"
    py_file = root / "malicioso.py"
    py_file.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('ejecutado')\n", encoding="utf-8")
    md_file = root / "mapa.md"
    md_file.write_text("Contenido de ejemplo", encoding="utf-8")
    (root / "datos.json").write_text("{}", encoding="utf-8")
    loader = AuthorizedSourceLoader(project)
    records = loader.load_demo_code()
    assert {record.source_ref for record in records} == {
        "ejemplos/polizas_demo/malicioso.py", "ejemplos/polizas_demo/mapa.md",
    }
    assert not marker.exists()
    assert loader.read_code_file("ejemplos/polizas_demo/malicioso.py").source_ref == "ejemplos/polizas_demo/malicioso.py"


@pytest.mark.parametrize("path", [
    "../outside.py", "ejemplos/polizas_demo/../../outside.py", "C:/outside.py",
    "/outside.py", "ejemplos\\polizas_demo\\x.py", "ejemplos/polizas_demo/data.json",
])
def test_rejects_path_traversal_absolute_and_unapproved_extension(tmp_path, path):
    project = tmp_path / "project"
    root = project / "ejemplos" / "polizas_demo"
    root.mkdir(parents=True)
    loader = AuthorizedSourceLoader(project)
    with pytest.raises(SourceError, match="Ruta"):
        loader.read_code_file(path)


def test_rejects_symbolic_link_outside_authorized_root(tmp_path):
    project = tmp_path / "project"
    root = project / "ejemplos" / "polizas_demo"
    root.mkdir(parents=True)
    outside = tmp_path / "outside.py"
    outside.write_text("print('no')", encoding="utf-8")
    link = root / "escape.py"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("El sistema no permite crear enlaces simbólicos en este entorno")
    loader = AuthorizedSourceLoader(project)
    with pytest.raises(SourceError, match="Ruta"):
        loader.read_code_file("ejemplos/polizas_demo/escape.py")


def test_rejects_resolved_symlink_target_outside_root(tmp_path, monkeypatch):
    from pathlib import Path

    project = tmp_path / "project"
    root = project / "ejemplos" / "polizas_demo"
    root.mkdir(parents=True)
    alias = root / "escape.py"
    alias.write_text("# ruta alias", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text("# fuera de la raíz", encoding="utf-8")
    original_resolve = Path.resolve
    alias_path = alias.absolute()

    def resolve(path, *args, **kwargs):
        if path.absolute() == alias_path:
            return original_resolve(outside, *args, **kwargs)
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    loader = AuthorizedSourceLoader(project)
    with pytest.raises(SourceError, match="Ruta"):
        loader.read_code_file("ejemplos/polizas_demo/escape.py")


def test_source_record_rejects_approval_claim_for_simulated_data():
    with pytest.raises(SourceError, match="simulada"):
        SourceRecord("hu_aprobadas", "HU-REF-001", "simulated_reference", "fixture#1", "fixture", "dato", "aprobada")
