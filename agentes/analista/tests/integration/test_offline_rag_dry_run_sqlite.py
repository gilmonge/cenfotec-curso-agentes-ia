from __future__ import annotations

from agentes.analista.memory.repositorio import RepositorioHU
from agentes.conocimiento.ingesta import run_ingestion


HU = {
    "id": "fa3d6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01",
    "codigo": "HU-OFFLINE-001",
    "titulo": "Validar vigencia de cobertura",
    "tipo_informacion": "Minuta",
    "requerimiento": "Validar la vigencia de la cobertura antes de renovar.",
    "historia": {"asA": "persona analista", "iWant": "validar vigencia", "soThat": "evitar renovaciones inválidas"},
    "criterios": [{"text": "La vigencia se valida antes de renovar."}],
    "aclaraciones": [],
}


def _create_lesson(repo: RepositorioHU, suffix: str) -> str:
    result = repo.registrar_cambio(
        hu_id=HU["id"], solicitud=f"Solicitud ficticia {suffix}",
        clasificacion="cambio_alcance", causa_raiz="Reglas de negocio",
        pregunta_sugerida=f"¿Qué condición aplica en el escenario {suffix}?",
        terminos=["condición", suffix],
    )
    return result["leccion_id"]


def test_offline_dry_run_uses_valid_sqlite_schema_and_lists_sources_without_pinecone(tmp_path, monkeypatch):
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_url = f"sqlite:///{(tmp_path / 'repositorio-valido.sqlite').as_posix()}"
    repo = RepositorioHU(database_url, crear_esquema=True)
    repo.guardar_hu(HU)
    proposed_id = _create_lesson(repo, "propuesta")
    rejected_id = _create_lesson(repo, "rechazada")
    approved_id = _create_lesson(repo, "aprobada")
    repo.decidir_leccion(rejected_id, "rechazar")
    repo.decidir_leccion(approved_id, "aprobar")
    before_hu = repo.listar_hu()
    before_lessons = repo.listar_lecciones()

    def forbidden_pinecone_client():
        raise AssertionError("El dry-run no debe construir ni llamar el cliente Pinecone.")

    result = run_ingestion(
        fuente="todas",
        dry_run=True,
        loader=None,
        client_factory=forbidden_pinecone_client,
        repository_factory=lambda: RepositorioHU(database_url, crear_esquema=False),
    )

    assert result["status"] == "dry_run"
    assert result["dry_run"] is True
    assert result["index"] == "not_contacted"
    assert result["errors"] == []
    assert set(result["namespaces"]) == {
        "glosario", "estandares", "checklist", "hu_aprobadas", "lecciones", "codigo",
    }
    assert all(counts["validated"] > 0 for counts in result["namespaces"].values())
    assert result["batches"] == len(result["batch_manifest"]) > 0
    assert all(batch["chunk_ids"] for batch in result["batch_manifest"])

    batches_by_kind = {}
    for batch in result["batch_manifest"]:
        batches_by_kind.setdefault(batch["source_kind"], []).append(batch)
        if batch["source_kind"] in {"approved_history", "approved_lesson"}:
            assert batch["approval_status"] == "aprobada"
        else:
            assert batch["approval_status"] is None
    assert batches_by_kind["approved_history"][0]["source_id"] == HU["id"]
    assert [batch["source_id"] for batch in batches_by_kind["approved_lesson"]] == [approved_id]
    assert batches_by_kind["simulated_reference"]
    assert proposed_id not in {batch["source_id"] for batch in result["batch_manifest"]}
    assert rejected_id not in {batch["source_id"] for batch in result["batch_manifest"]}
    assert before_hu == repo.listar_hu()
    assert before_lessons == repo.listar_lecciones()
