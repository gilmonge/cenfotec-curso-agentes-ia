from __future__ import annotations

import io
import json

import pytest

from agentes.conocimiento.ingesta import main, run_ingestion
from agentes.conocimiento.batches import prepare_batches
from agentes.conocimiento.ingesta import _reconcile_source
from agentes.conocimiento.errors import PineconeIndexIncompatibleError
from agentes.conocimiento.sources import SourceRecord


class FakeLoader:
    def load_json_source(self, name):
        namespaces = {"glosario": "glosario", "estandares": "estandares", "checklist": "checklist",
                      "hu_similares": "hu_aprobadas"}
        if name == "glosario":
            return [SourceRecord(namespaces[name], "g-1", "simulated_fixture", "fixture/glosario#g-1", "fixture", "póliza prima")]
        if name == "hu_similares":
            return [SourceRecord(namespaces[name], "ref-1", "simulated_reference", "fixture/hu_similares#ref-1", "fixture", "póliza cobertura")]
        return []

    def load_approved_repository(self, repository):
        return [
            SourceRecord("hu_aprobadas", "hu-1", "approved_history", "RepositorioHU:hu_aprobada/hu-1", "repo", "póliza", "aprobada"),
            SourceRecord("lecciones", "lesson-1", "approved_lesson", "RepositorioHU:leccion/lesson-1", "repo", "prima", "aprobada"),
        ]

    def load_demo_code(self):
        return [SourceRecord("codigo", "ejemplos/polizas_demo/demo.py", "simulated_code",
                             "ejemplos/polizas_demo/demo.py", "fixture", "calcular prima")]


class FakeIndex:
    def __init__(self):
        self.queries = []
        self.deleted = []

    def query(self, **kwargs):
        self.queries.append(kwargs)
        return {"matches": [
            {"id": "stale-same-source", "metadata": {
                "namespace": kwargs["namespace"],
                "source_id": kwargs["filter"]["source_id"]["$eq"],
                "source_ref": kwargs["filter"]["source_ref"]["$eq"], "chunk": 9,
            }},
            {"id": "other-source", "metadata": {
                "namespace": kwargs["namespace"], "source_id": "someone-else",
                "source_ref": kwargs["filter"]["source_ref"]["$eq"], "chunk": 9,
            }},
            {"id": "other-namespace", "metadata": {
                "namespace": "codigo" if kwargs["namespace"] != "codigo" else "glosario",
                "source_id": kwargs["filter"]["source_id"]["$eq"],
                "source_ref": kwargs["filter"]["source_ref"]["$eq"], "chunk": 9,
            }},
        ]}

    def delete(self, *, ids, namespace):
        self.deleted.append((tuple(ids), namespace))


class FakeStore:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = []

    def add_documents(self, documents, *, ids):
        self.calls.append((documents, ids))
        if self.fail:
            raise RuntimeError("secret-no-debe-reportarse")


class FakeClient:
    def __init__(self, *, fail_namespace=None):
        self.validated = 0
        self.created = 0
        self.index = FakeIndex()
        self.stores = {}
        self.fail_namespace = fail_namespace

    def validate_index(self):
        self.validated += 1

    def create_index_if_missing(self):
        self.created += 1

    def create_vector_store(self, *, namespace):
        self.stores.setdefault(namespace, FakeStore(fail=namespace == self.fail_namespace))
        return self.stores[namespace]

    def get_vector_index(self):
        return self.index


def test_dry_run_prepares_six_namespace_counts_without_remote_calls_or_writes():
    result = run_ingestion(
        fuente="todas", dry_run=True, loader=FakeLoader(),
        client_factory=lambda: pytest.fail("dry-run no debe construir cliente Pinecone"),
        repository_factory=lambda: object(),
    )
    assert result["status"] == "dry_run"
    assert result["index"] == "not_contacted"
    assert set(result["namespaces"]) == {"glosario", "estandares", "checklist", "hu_aprobadas", "lecciones", "codigo"}
    assert result["namespaces"]["glosario"]["validated"] == 1
    assert result["namespaces"]["hu_aprobadas"]["validated"] == 2
    assert result["namespaces"]["lecciones"]["validated"] == 1


def test_cli_outputs_sanitized_mock_counts_for_dry_run():
    output = io.StringIO()
    code = main(
        ["--fuente", "todas", "--dry-run"], loader=FakeLoader(),
        repository_factory=lambda: object(), stdout=output,
    )
    result = json.loads(output.getvalue())
    assert code == 0
    assert result["status"] == "dry_run"
    assert len(result["namespaces"]) == 6
    assert "PINECONE_API_KEY" not in output.getvalue()
    assert "secret-no-debe-reportarse" not in output.getvalue()


def test_normal_cli_validates_index_and_reconciles_only_exact_source_in_namespace():
    client = FakeClient()
    result = run_ingestion(
        fuente="todas", loader=FakeLoader(), client_factory=lambda: client,
        repository_factory=lambda: object(),
    )
    assert result["status"] == "success"
    assert client.validated == 1 and client.created == 0
    assert client.index.queries
    for query in client.index.queries:
        assert query["namespace"] in {"glosario", "hu_aprobadas", "lecciones", "codigo"}
        assert query["filter"]["source_id"]["$eq"]
        assert query["filter"]["source_ref"]["$eq"]
    assert all(ids == ("stale-same-source",) for ids, _namespace in client.index.deleted)
    assert {namespace for _, namespace in client.index.deleted} == {"glosario", "hu_aprobadas", "lecciones", "codigo"}
    assert result["namespaces"]["hu_aprobadas"]["upserted"] == 2


def test_explicit_create_option_calls_create_or_validate_instead_of_default_validate():
    client = FakeClient()
    result = run_ingestion(
        fuente="glosario", crear_indice=True, loader=FakeLoader(), client_factory=lambda: client,
    )
    assert result["status"] == "success"
    assert client.created == 1 and client.validated == 0


def test_partial_upsert_failure_is_reported_and_never_claims_total_success():
    client = FakeClient(fail_namespace="glosario")
    result = run_ingestion(
        fuente="todas", loader=FakeLoader(), client_factory=lambda: client,
        repository_factory=lambda: object(),
    )
    assert result["status"] == "partial_failure"
    assert any(item["namespace"] == "glosario" and item["code"] == "UPSERT_FAILED" for item in result["errors"])
    assert "secret-no-debe-reportarse" not in json.dumps(result)
    assert result["namespaces"]["estandares"]["upserted"] == 0
    assert client.stores["hu_aprobadas"].calls


def test_unknown_source_is_rejected_and_parser_exposes_only_allowlist():
    with pytest.raises(ValueError, match="Fuente"):
        run_ingestion(fuente="../../untrusted", dry_run=True, loader=FakeLoader())
    with pytest.raises(SystemExit):
        main(["--fuente", "../../untrusted", "--dry-run"], loader=FakeLoader())


def test_incompatible_index_fails_before_any_vector_write():
    class BadIndexClient(FakeClient):
        def validate_index(self):
            raise PineconeIndexIncompatibleError()

    client = BadIndexClient()
    result = run_ingestion(fuente="glosario", loader=FakeLoader(), client_factory=lambda: client)
    assert result["status"] == "failed"
    assert result["errors"] == [{"source": "pinecone_index", "code": "PINECONE_INDEX_INCOMPATIBLE"}]
    assert client.stores == {}
    assert client.index.queries == []


def test_reconciliation_aborts_without_deleting_when_results_may_be_truncated():
    batch = prepare_batches([SourceRecord(
        "glosario", "g1", "simulated_fixture", "fixture/glosario#g1", "fixture", "póliza",
    )])[0]

    class TruncatedIndex:
        def query(self, **_kwargs):
            return {"matches": [{"id": str(index), "metadata": {}} for index in range(10_000)]}

        def delete(self, **_kwargs):
            pytest.fail("No debe borrar si el listado quedó truncado")

    with pytest.raises(RuntimeError, match="RECONCILIATION_RESULT_LIMIT"):
        _reconcile_source(TruncatedIndex(), batch)


def test_partial_source_load_is_reported_as_failure_without_total_success():
    class PartialLoader(FakeLoader):
        def load_json_source(self, name):
            if name == "glosario":
                raise RuntimeError("secret source details")
            return super().load_json_source(name)

    result = run_ingestion(
        fuente="todas", dry_run=True, loader=PartialLoader(), repository_factory=lambda: object(),
    )
    assert result["status"] == "partial_failure"
    assert result["errors"][0] == {"source": "glosario", "code": "SOURCE_UNAVAILABLE"}
    assert "secret source details" not in json.dumps(result)


def test_read_only_repository_factory_does_not_create_tables(monkeypatch):
    from agentes.analista.memory import repositorio

    engine = object()
    monkeypatch.setattr(repositorio, "crear_motor", lambda _source: engine)
    monkeypatch.setattr(repositorio, "_verificar_esquema", lambda _engine: None)
    monkeypatch.setattr(
        repositorio._metadata, "create_all",
        lambda *_args, **_kwargs: pytest.fail("La lectura de ingesta no debe ejecutar DDL"),
    )

    instance = repositorio.RepositorioHU("sqlite:///mock.db", crear_esquema=False)
    assert instance.motor is engine


def test_mock_cli_repeat_upserts_the_same_deterministic_ids_without_duplicates():
    class StatefulIndex:
        def __init__(self, data):
            self.data = data

        def query(self, *, namespace, filter, **_kwargs):
            source_id = filter["source_id"]["$eq"]
            source_ref = filter["source_ref"]["$eq"]
            return {"matches": [
                {"id": document_id, "metadata": document.metadata}
                for document_id, document in self.data[namespace].items()
                if document.metadata.get("source_id") == source_id and document.metadata.get("source_ref") == source_ref
            ]}

        def delete(self, *, ids, namespace):
            for document_id in ids:
                self.data[namespace].pop(document_id, None)

    class StatefulStore:
        def __init__(self, namespace, data):
            self.namespace = namespace
            self.data = data

        def add_documents(self, documents, *, ids):
            self.data[self.namespace].update(dict(zip(ids, documents)))

    class StatefulClient(FakeClient):
        def __init__(self):
            super().__init__()
            from collections import defaultdict

            self.data = defaultdict(dict)
            self.index = StatefulIndex(self.data)

        def create_vector_store(self, *, namespace):
            return StatefulStore(namespace, self.data)

    client = StatefulClient()
    for _ in range(2):
        result = run_ingestion(fuente="glosario", loader=FakeLoader(), client_factory=lambda: client)
        assert result["status"] == "success"
    ids = set(client.data["glosario"])
    assert len(ids) == 1
    assert next(iter(client.data["glosario"].values())).id in ids
