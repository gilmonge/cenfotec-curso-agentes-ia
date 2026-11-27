from __future__ import annotations

import pytest
from langchain_core.documents import Document

from agentes.analista.core.agent_registry import AgentId
from agentes.conocimiento.documents import source_to_document
from agentes.conocimiento.errors import (
    PineconeAuthenticationError,
    PineconeCredentialsMissingError,
    PineconeIndexIncompatibleError,
    PineconeIndexNotFoundError,
    PineconeRateLimitError,
    PineconeTimeoutError,
)
from agentes.conocimiento.retrieval import KnowledgeRetriever
from agentes.conocimiento.sources import SourceRecord


def source(namespace="glosario", *, source_id=None, source_kind="simulated_fixture", ref=None, approval=None, text=None):
    ids = {"glosario": "g1", "estandares": "s1", "checklist": "c1", "hu_aprobadas": "h1",
           "lecciones": "l1", "codigo": "ejemplos/polizas_demo/modelos.py"}
    if source_kind == "approved_history":
        ref = ref or "RepositorioHU:hu_aprobada/h1"
        approval = "aprobada"
        namespace = "hu_aprobadas"
    elif source_kind == "approved_lesson":
        ref = ref or "RepositorioHU:leccion/l1"
        approval = "aprobada"
        namespace = "lecciones"
    elif namespace == "codigo":
        ref = ref or ids[namespace]
        source_kind = "simulated_code"
    else:
        if namespace == "lecciones":
            source_kind = "approved_lesson"
            approval = "aprobada"
            ref = ref or "RepositorioHU:leccion/l1"
        source_id = source_id or ids[namespace]
        filenames = {"glosario": "glosario.json", "estandares": "estandares.json",
                     "checklist": "checklist_vacios.json", "hu_aprobadas": "hu_similares.json"}
        if namespace == "hu_aprobadas" and source_kind == "simulated_fixture":
            source_kind = "simulated_reference"
        if namespace != "lecciones":
            ref = ref or f"agentes/analista/fuentes/{filenames[namespace]}#{source_id}"
    return SourceRecord(
        namespace=namespace, source_id=source_id or ids[namespace], source_kind=source_kind,
        source_ref=ref, origin="fixture", text=text or "póliza prima cobertura renovación",
        approval_status=approval,
    )


class FakeStore:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def similarity_search_with_score(self, query, *, k, filter=None):
        self.calls.append((query, k, filter))
        return self.results[:k]


class FakeClient:
    def __init__(self, stores):
        self.stores = stores
        self.namespaces = []

    def create_vector_store(self, *, namespace):
        self.namespaces.append(namespace)
        return self.stores[namespace]


@pytest.mark.parametrize(
    ("namespace", "role"),
    [
        ("glosario", AgentId.ANALYST),
        ("estandares", AgentId.WRITER_REVIEWER),
        ("checklist", AgentId.ANALYST),
        ("hu_aprobadas", AgentId.ANALYST),
        ("lecciones", AgentId.CHANGE_MANAGER),
        ("codigo", AgentId.TECHNICAL_ADVISOR),
    ],
)
def test_mocked_search_queries_each_of_the_six_namespaces(namespace, role):
    doc = source_to_document(source(namespace))
    store = FakeStore([(doc, 0.82)])
    client = FakeClient({namespace: store})
    retriever = KnowledgeRetriever(client_factory=lambda: client, local_source_provider=lambda: [])

    result = retriever.search(agent_role=role, query="póliza prima", namespace=namespace, limit=3)

    assert result.status == "ok"
    assert result.backend == "pinecone"
    assert result.namespace == namespace
    assert result.sources[0].source_ref == doc.metadata["source_ref"]
    assert result.sources[0].backend == "pinecone"
    assert result.sources[0].citation == doc.metadata["source_ref"]
    assert result.sources[0].content_untrusted is True
    assert client.namespaces == [namespace]


def test_rejects_arbitrary_namespace_and_cross_role_access_before_client_creation():
    client = FakeClient({})
    retriever = KnowledgeRetriever(client_factory=lambda: client, local_source_provider=lambda: [])
    with pytest.raises(ValueError, match="Namespace"):
        retriever.search(agent_role=AgentId.ANALYST, query="x", namespace="codigo")
    with pytest.raises(ValueError, match="Namespace"):
        retriever.search(agent_role=AgentId.ANALYST, query="x", namespace="glosario/../codigo")
    with pytest.raises(ValueError, match="Rol"):
        retriever.search(agent_role="superusuario", query="x", namespace="glosario")
    assert client.namespaces == []


def test_strict_namespace_validation_skips_a_cross_namespace_match():
    doc = source_to_document(source("checklist"))
    doc.metadata["namespace"] = "estandares"
    store = FakeStore([(doc, 1.0)])
    retriever = KnowledgeRetriever(
        client_factory=lambda: FakeClient({"checklist": store}), local_source_provider=lambda: [],
    )
    result = retriever.search(agent_role=AgentId.ANALYST, query="póliza", namespace="checklist")
    assert result.sources == []
    assert result.backend == "pinecone"
    assert store.calls[0][1] == 5


def test_preserves_result_order_and_honors_limit():
    docs = [source_to_document(source(source_id=f"g{index}", text=f"póliza {index}")) for index in range(4)]
    store = FakeStore([(doc, 1.0 - index / 10) for index, doc in enumerate(docs)])
    retriever = KnowledgeRetriever(
        client_factory=lambda: FakeClient({"glosario": store}), local_source_provider=lambda: [],
    )
    result = retriever.search(agent_role=AgentId.ANALYST, query="póliza", namespace="glosario", limit=2)
    assert [item.source_ref for item in result.sources] == [
        "agentes/analista/fuentes/glosario.json#g0", "agentes/analista/fuentes/glosario.json#g1",
    ]
    assert [item.chunk for item in result.sources] == [0, 0]
    assert [item.score for item in result.sources] == [1.0, 0.9]
    assert store.calls[0][1] == 2


def test_empty_semantic_results_are_an_ok_empty_response():
    retriever = KnowledgeRetriever(
        client_factory=lambda: FakeClient({"glosario": FakeStore([])}), local_source_provider=lambda: [],
    )
    result = retriever.search(agent_role=AgentId.ANALYST, query="sin evidencia", namespace="glosario")
    assert result.status == "ok" and result.backend == "pinecone" and result.sources == []


def test_invented_citation_metadata_is_filtered_out():
    doc = source_to_document(source(ref="../../inventado.py"))
    store = FakeStore([(doc, 0.9)])
    retriever = KnowledgeRetriever(
        client_factory=lambda: FakeClient({"glosario": store}), local_source_provider=lambda: [],
    )
    result = retriever.search(agent_role=AgentId.ANALYST, query="póliza", namespace="glosario")
    assert result.sources == []


@pytest.mark.parametrize(
    "failure",
    [
        PineconeCredentialsMissingError(), PineconeAuthenticationError(), PineconeTimeoutError(),
        PineconeRateLimitError(), PineconeIndexNotFoundError(), PineconeIndexIncompatibleError(),
    ],
)
def test_pinecone_errors_use_real_local_backend_and_degraded_status(failure):
    local = source("glosario")
    retriever = KnowledgeRetriever(
        client_factory=lambda: (_ for _ in ()).throw(failure),
        local_source_provider=lambda: [local],
    )
    result = retriever.search(agent_role=AgentId.ANALYST, query="póliza cobertura", namespace="glosario")
    assert result.status == "degraded"
    assert result.backend == "local"
    assert result.sources[0].backend == "local"
    assert result.sources[0].source_ref == local.source_ref
    assert result.error_code == failure.code


def test_pinecone_error_without_local_source_returns_controlled_empty_degraded_result():
    retriever = KnowledgeRetriever(
        client_factory=lambda: (_ for _ in ()).throw(PineconeTimeoutError()),
        local_source_provider=lambda: [],
    )
    result = retriever.search(agent_role=AgentId.ANALYST, query="póliza", namespace="glosario")
    assert (result.status, result.backend, result.sources) == ("degraded", "none", [])


def test_missing_api_key_falls_back_before_constructing_the_pinecone_sdk(monkeypatch):
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    local = source("glosario")
    retriever = KnowledgeRetriever(local_source_provider=lambda: [local])
    result = retriever.search(agent_role=AgentId.ANALYST, query="póliza", namespace="glosario")
    assert result.status == "degraded" and result.backend == "local"
    assert result.error_code == "PINECONE_CREDENTIALS_MISSING"


def test_change_manager_is_filtered_to_persisted_approved_records_only():
    simulated = source("hu_aprobadas", source_kind="simulated_reference", ref="agentes/analista/fuentes/hu_similares.json#REF")
    approved = source("hu_aprobadas", source_kind="approved_history")
    rejected_lesson = source("lecciones", source_kind="approved_lesson", ref="RepositorioHU:leccion/l2")
    store = FakeStore([
        (source_to_document(simulated), 0.99),
        (source_to_document(approved), 0.8),
    ])
    rejected_document = source_to_document(rejected_lesson)
    rejected_document.metadata["approval_status"] = "propuesta"
    lesson_store = FakeStore([(rejected_document, 0.99)])
    client = FakeClient({"hu_aprobadas": store, "lecciones": lesson_store})
    retriever = KnowledgeRetriever(
        client_factory=lambda: client,
        local_source_provider=lambda: [simulated, approved, rejected_lesson],
    )

    stories = retriever.search(agent_role=AgentId.CHANGE_MANAGER, query="póliza", namespace="hu_aprobadas")
    lessons = retriever.search(agent_role=AgentId.CHANGE_MANAGER, query="póliza", namespace="lecciones")

    assert [item.source_kind for item in stories.sources] == ["approved_history"]
    assert stories.sources[0].source_ref.startswith("RepositorioHU:")
    assert store.calls[0][2] == {"source_kind": {"$eq": "approved_history"}, "approval_status": {"$eq": "aprobada"}}
    assert lessons.sources == []
    assert lesson_store.calls[0][2]["approval_status"] == {"$eq": "aprobada"}


def test_local_search_has_deterministic_order_and_never_labels_results_pinecone():
    records = [source(text="póliza renovación"), source(text="póliza cobertura")]
    retriever = KnowledgeRetriever(
        client_factory=lambda: (_ for _ in ()).throw(PineconeTimeoutError()),
        local_source_provider=lambda: records,
    )
    result = retriever.search(agent_role=AgentId.ANALYST, query="póliza cobertura", namespace="glosario")
    assert result.status == "degraded" and result.backend == "local"
    assert all(item.backend == "local" for item in result.sources)
    assert result.sources[0].text == "póliza cobertura"
