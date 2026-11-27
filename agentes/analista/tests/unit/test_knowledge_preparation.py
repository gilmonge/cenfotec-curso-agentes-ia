"""Documentos, chunking determinista, IDs y límites de reconciliación."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

import pytest
from langchain_core.documents import Document

from agentes.conocimiento.batches import PreparedBatch, obsolete_ids, prepare_batches
from agentes.conocimiento.chunking import MAX_EMBEDDING_INPUT_TOKENS, RESERVED_SPECIAL_TOKENS, chunk_documents
from agentes.conocimiento.documents import source_to_document, split_approval_classes
from agentes.conocimiento.ids import stable_document_id
from agentes.conocimiento.sources import SourceRecord
from agentes.conocimiento.sources import AuthorizedSourceLoader


def _source(text: str = "póliza y cobertura") -> SourceRecord:
    return SourceRecord(
        namespace="glosario", source_id="termino-1", source_kind="simulated_fixture",
        source_ref="agentes/analista/fuentes/glosario.json#termino-1", origin="fixture ficticio", text=text,
    )


def _mock_batch_write(adapter, batch: PreparedBatch) -> None:
    """Simula el ciclo de upsert/reconciliación; no contiene cliente ni llamada remota."""
    try:
        adapter.upsert_documents(batch.namespace, batch.documents)
        current = adapter.namespace_documents(batch.namespace)
        stale = obsolete_ids(current, batch)
        adapter.delete_ids(batch.namespace, stale)
    except Exception:
        raise RuntimeError("No fue posible completar la preparación simulada del lote.") from None


class MockVectorAdapter:
    def __init__(self):
        self.data = defaultdict(dict)
        self.upserts = 0
        self.deletes = []
        self.fail_after_first = False

    def upsert_documents(self, namespace, documents):
        self.upserts += 1
        for index, document in enumerate(documents):
            self.data[namespace][document.id] = deepcopy(document)
            if self.fail_after_first and index == 0:
                raise TimeoutError("secreto-real debe omitirse")

    def namespace_documents(self, namespace):
        return list(self.data[namespace].values())

    def delete_ids(self, namespace, ids):
        self.deletes.append((namespace, set(ids)))
        for document_id in ids:
            self.data[namespace].pop(document_id, None)


def test_langchain_document_has_validated_metadata_and_stable_identity():
    document = source_to_document(_source())
    assert isinstance(document, Document)
    assert document.metadata == {
        "namespace": "glosario", "source_id": "termino-1", "source_kind": "simulated_fixture",
        "source_ref": "agentes/analista/fuentes/glosario.json#termino-1", "chunk": 0,
        "origin": "fixture ficticio", "content_untrusted": True,
    }
    assert document.id == stable_document_id("glosario", document.metadata["source_ref"], "termino-1", 0)


def test_authorized_json_and_demo_files_convert_to_langchain_documents():
    loader = AuthorizedSourceLoader()
    sources = loader.load_json_sources() + loader.load_demo_code()
    batches = prepare_batches(sources)
    documents = [document for batch in batches for document in batch.documents]
    assert len({document.metadata["source_ref"] for document in documents}) == len(sources)
    assert {document.metadata["namespace"] for document in documents} == {
        "glosario", "estandares", "checklist", "hu_aprobadas", "codigo",
    }
    assert all(document.metadata["content_untrusted"] is True for document in documents)
    assert all(document.metadata["origin"] and document.metadata["source_ref"] for document in documents)
    assert all(document.metadata["source_kind"] == "simulated_reference" and "hu_similares.json" in document.metadata["source_ref"]
               for document in documents if document.metadata["namespace"] == "hu_aprobadas")


def test_chunking_is_deterministic_ordered_and_within_embedding_limit():
    text = "Primera sección. " + ("área técnica y póliza. " * 120)
    document = source_to_document(_source(text))
    counter = lambda value: len(value.split())
    first = chunk_documents([document], token_counter=counter, token_limit=40, char_limit=240)
    second = chunk_documents([document], token_counter=counter, token_limit=40, char_limit=240)
    assert [item.page_content for item in first] == [item.page_content for item in second]
    assert [item.id for item in first] == [item.id for item in second]
    assert [item.metadata["chunk"] for item in first] == list(range(len(first)))
    assert "".join(item.page_content for item in first) == text
    assert all(counter(item.page_content) <= 40 for item in first)
    assert all(item.id == stable_document_id("glosario", document.metadata["source_ref"], "termino-1", i)
               for i, item in enumerate(first))
    assert MAX_EMBEDDING_INPUT_TOKENS == 507


def test_chunking_rejects_a_chunk_that_cannot_fit_a_single_character():
    document = source_to_document(_source("x"))
    with pytest.raises(ValueError, match="carácter"):
        chunk_documents([document], token_counter=lambda _text: 2, token_limit=1)


def test_default_chunk_bound_uses_utf8_bytes_and_reserves_model_special_tokens():
    text = "🙂 póliza 界 " * 300
    document = source_to_document(_source(text))
    chunks = chunk_documents([document])
    safe_content_limit = MAX_EMBEDDING_INPUT_TOKENS - RESERVED_SPECIAL_TOKENS
    assert "".join(chunk.page_content for chunk in chunks) == text
    assert len(chunks) > 1
    assert all(len(chunk.page_content.encode("utf-8")) <= safe_content_limit for chunk in chunks)


def test_ids_include_namespace_source_reference_and_chunk_number():
    base = stable_document_id("glosario", "source-a", "id-1", 0)
    assert base != stable_document_id("checklist", "source-a", "id-1", 0)
    assert base != stable_document_id("glosario", "source-b", "id-1", 0)
    assert base != stable_document_id("glosario", "source-a", "id-1", 1)


def test_preparing_identical_source_twice_produces_same_batch_and_ids():
    source = _source("póliza " * 140)
    first = prepare_batches([source], token_counter=lambda text: len(text.split()))
    second = prepare_batches([source], token_counter=lambda text: len(text.split()))
    assert len(first) == len(second) == 1
    assert [doc.id for doc in first[0].documents] == [doc.id for doc in second[0].documents]
    assert len({doc.id for doc in first[0].documents}) == len(first[0].documents)
    assert [doc.page_content for doc in first[0].documents] == [doc.page_content for doc in second[0].documents]


def test_approved_and_simulated_records_are_partitioned():
    approved = SourceRecord("hu_aprobadas", "hu-1", "approved_history", "RepositorioHU:1", "repo", "HU", "aprobada")
    similar = SourceRecord("hu_aprobadas", "HU-REF-001", "simulated_reference", "hu_similares.json#1", "fixture", "ref")
    documents = [source_to_document(approved), source_to_document(similar)]
    approved_docs, simulated_docs = split_approval_classes(documents)
    assert [doc.metadata["source_id"] for doc in approved_docs] == ["hu-1"]
    assert [doc.metadata["source_id"] for doc in simulated_docs] == ["HU-REF-001"]


def test_stale_ids_are_scoped_to_exact_source_and_namespace():
    batch = prepare_batches([_source("nuevo")])[0]
    matching = Document(id="old-glossary-vector", page_content="", metadata={
        **batch.documents[0].metadata, "chunk": 3,
    })
    other_namespace = deepcopy(matching)
    other_namespace.id = "other-namespace"
    other_namespace.metadata["namespace"] = "checklist"
    other_source = deepcopy(matching)
    other_source.id = "other-source"
    other_source.metadata["source_ref"] = "different-source"
    assert obsolete_ids([matching, other_namespace, other_source], batch) == {"old-glossary-vector"}


def test_batch_rejects_cross_source_document():
    document = source_to_document(_source())
    with pytest.raises(ValueError, match="otra fuente"):
        PreparedBatch("checklist", "termino-1", document.metadata["source_ref"], (document,))


def test_mock_ingest_is_idempotent_replaces_changed_content_and_cleans_only_stale_ids():
    adapter = MockVectorAdapter()
    original = prepare_batches([_source("contenido largo " * 110)], token_counter=lambda value: len(value.split()))[0]
    changed = prepare_batches([_source("contenido revisado")])[0]
    _mock_batch_write(adapter, original)
    first_ids = set(adapter.data["glosario"])
    _mock_batch_write(adapter, original)
    assert set(adapter.data["glosario"]) == first_ids
    assert len(adapter.data["glosario"]) == len(original.documents)
    _mock_batch_write(adapter, changed)
    assert set(adapter.data["glosario"]) == {changed.documents[0].id}
    assert adapter.data["glosario"][changed.documents[0].id].page_content == "contenido revisado"
    assert adapter.deletes[-1] == ("glosario", first_ids - {changed.documents[0].id})


def test_mock_ingest_keeps_namespaces_isolated():
    adapter = MockVectorAdapter()
    glossary = prepare_batches([_source("dato")])[0]
    checklist_source = SourceRecord("checklist", "termino-1", "simulated_fixture", glossary.source_ref, "fixture", "check")
    checklist = prepare_batches([checklist_source])[0]
    _mock_batch_write(adapter, glossary)
    _mock_batch_write(adapter, checklist)
    assert set(adapter.data) == {"glosario", "checklist"}
    _mock_batch_write(adapter, PreparedBatch("glosario", glossary.source_id, glossary.source_ref, ()))
    assert adapter.data["checklist"]
    assert not adapter.data["glosario"]


def test_mock_partial_failure_is_sanitized_and_never_uses_pinecone():
    adapter = MockVectorAdapter()
    adapter.fail_after_first = True
    batch = prepare_batches([_source("fragmento " * 150)], token_counter=lambda value: len(value.split()))[0]
    with pytest.raises(RuntimeError, match="preparación simulada") as error:
        _mock_batch_write(adapter, batch)
    assert "secreto-real" not in str(error.value)
    assert adapter.upserts == 1
    assert len(adapter.data["glosario"]) == 1
    assert "pinecone" not in adapter.__class__.__module__.casefold()

