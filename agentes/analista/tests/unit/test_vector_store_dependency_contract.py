def test_conventional_pinecone_components_are_available_without_network_access(monkeypatch):
    from types import SimpleNamespace

    from langchain_pinecone import PineconeEmbeddings, PineconeVectorStore
    from pinecone import Pinecone

    assert callable(PineconeEmbeddings)
    assert callable(PineconeVectorStore)
    assert callable(Pinecone)

    # The embedding integration checks Pinecone's model catalog at construction.
    # Supply a local catalog result and a fake existing dense index for this contract test.
    monkeypatch.setattr(
        PineconeEmbeddings,
        "list_supported_models",
        lambda _self, vector_type=None: [{"model": "multilingual-e5-large"}],
    )
    embeddings = PineconeEmbeddings(
        model="multilingual-e5-large",
        dimension=1024,
        pinecone_api_key="test-only",
    )
    index = SimpleNamespace(config=SimpleNamespace(host="index.invalid", api_key="test-only"))
    store = PineconeVectorStore(index=index, embedding=embeddings, namespace="glosario")

    assert embeddings.model == "multilingual-e5-large"
    assert embeddings.dimension == 1024
    assert store._index is index
    assert store._embedding is embeddings
    assert store._namespace == "glosario"
