"""Acceso de solo lectura a HU y lecciones aprobadas vía RepositorioHU público."""
from __future__ import annotations

import pytest

from agentes.analista.memory.repositorio import RepositorioHU
from agentes.conocimiento.batches import prepare_batches
from agentes.conocimiento.sources import AuthorizedSourceLoader, SourceError


HU = {
    "id": "fa3d6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01",
    "codigo": "HU-DEMO-001",
    "titulo": "Actualizar vigencia de cobertura",
    "tipo_informacion": "Minuta",
    "requerimiento": "Negocio solicita validar la vigencia antes de renovar.",
    "historia": {"asA": "persona analista", "iWant": "validar vigencia", "soThat": "evitar renovación inválida"},
    "criterios": [{"text": "La vigencia se valida al guardar"}],
    "aclaraciones": [{"pregunta": "¿Desde cuándo aplica?", "respuesta": "En la próxima renovación"}],
}


def _repo(tmp_path):
    return RepositorioHU(tmp_path / "repositorio-temporal.sqlite")


def _lesson(repo, index: int) -> str:
    result = repo.registrar_cambio(
        hu_id=HU["id"], solicitud=f"Solicitud de prueba {index}", clasificacion="cambio_alcance",
        causa_raiz="Reglas de negocio", pregunta_sugerida=f"¿Aplica la regla {index}?", terminos=[f"regla{index}"],
    )
    return result["leccion_id"]


def test_sqlite_source_includes_only_approved_hu_and_lessons(tmp_path):
    repo = _repo(tmp_path)
    repo.guardar_hu(HU)
    # Historias de trabajo permanecen como borradores y no se consultan.
    repo.guardar_historia("borrador-1", {"title": "Borrador privado", "number": "HU-DRAFT-1"})
    proposal_id = _lesson(repo, 1)
    rejected_id = _lesson(repo, 2)
    approved_id = _lesson(repo, 3)
    repo.decidir_leccion(rejected_id, "rechazar")
    repo.decidir_leccion(approved_id, "aprobar")

    hu_before = repo.listar_hu()
    lessons_before = repo.listar_lecciones()
    records = AuthorizedSourceLoader().load_approved_repository(repo)
    documents = [document for batch in prepare_batches(records) for document in batch.documents]
    hu_after = repo.listar_hu()
    lessons_after = repo.listar_lecciones()

    histories = [record for record in records if record.namespace == "hu_aprobadas"]
    lessons = [record for record in records if record.namespace == "lecciones"]
    assert [record.source_id for record in histories] == [HU["id"]]
    assert histories[0].source_kind == "approved_history" and histories[0].approval_status == "aprobada"
    assert [record.source_id for record in lessons] == [approved_id]
    assert lessons[0].source_kind == "approved_lesson" and lessons[0].approval_status == "aprobada"
    assert {document.metadata["source_kind"] for document in documents} == {"approved_history", "approved_lesson"}
    assert all(document.metadata["approval_status"] == "aprobada" for document in documents)
    assert proposal_id not in {record.source_id for record in records}
    assert rejected_id not in {record.source_id for record in records}
    assert "Borrador privado" not in " ".join(record.text for record in records)
    assert hu_before == hu_after and lessons_before == lessons_after


def test_repository_reader_uses_only_public_approved_read_methods():
    class RepositoryDouble:
        def __init__(self):
            self.calls = []

        def listar_hu(self):
            self.calls.append(("listar_hu",))
            return [{"id": "HU-APP-1"}]

        def obtener_hu(self, identifier):
            self.calls.append(("obtener_hu", identifier))
            return {"id": identifier, "titulo": "Historia de prueba", "historia": {"iWant": "revisar"}}

        def listar_lecciones(self, *, estado=None):
            self.calls.append(("listar_lecciones", estado))
            assert estado == "aprobada"
            return [{"id": "LEC-APP-1", "estado": "aprobada", "pregunta_sugerida": "¿Qué aplica?"}]

        def __getattr__(self, name):
            raise AssertionError(f"Método no autorizado: {name}")

    repository = RepositoryDouble()
    records = AuthorizedSourceLoader().load_approved_repository(repository)
    assert [item[0] for item in repository.calls] == ["listar_hu", "obtener_hu", "listar_lecciones"]
    assert repository.calls[-1] == ("listar_lecciones", "aprobada")
    assert {record.namespace for record in records} == {"hu_aprobadas", "lecciones"}


def test_repo_failure_is_sanitized_without_exposing_exception_details():
    class BrokenRepository:
        def listar_hu(self):
            raise RuntimeError("DATABASE_URL=password-secret")

    with pytest.raises(SourceError, match="RepositorioHU") as error:
        AuthorizedSourceLoader().load_approved_repository(BrokenRepository())
    assert "password-secret" not in str(error.value)


def test_potential_personal_data_is_rejected_from_repository_record():
    class PersonalDataRepository:
        def listar_hu(self):
            return [{"id": "HU-1"}]

        def obtener_hu(self, _identifier):
            return {"id": "HU-1", "titulo": "Contacto", "historia": "correo real persona@ejemplo.invalid"}

        def listar_lecciones(self, *, estado=None):
            return []

    with pytest.raises(SourceError, match="dato personal"):
        AuthorizedSourceLoader().load_approved_repository(PersonalDataRepository())

