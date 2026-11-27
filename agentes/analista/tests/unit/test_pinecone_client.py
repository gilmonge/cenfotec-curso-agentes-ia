from __future__ import annotations

from copy import deepcopy
import pytest

from agentes.conocimiento.client import PineconeKnowledgeClient
from agentes.conocimiento.config import PineconeSettings
from agentes.conocimiento.errors import (
    PineconeAuthenticationError,
    PineconeConfigurationError,
    PineconeCredentialsMissingError,
    PineconeIndexIncompatibleError,
    PineconeIndexNotFoundError,
    PineconeServiceError,
    PineconeTimeoutError,
)

TEST_API_KEY = "pinecone-key-for-tests-only"


class FakeSDKError(Exception):
    def __init__(self, status, message=TEST_API_KEY):
        super().__init__(message)
        self.status = status


def compatible_description(**overrides):
    description = {
        "name": "historias-usuario",
        "vector_type": "dense",
        "dimension": 1024,
        "metric": "cosine",
        "spec": {"serverless": {"cloud": "aws", "region": "us-east-1"}},
    }
    description.update(overrides)
    return description


class FakePineconeAdapter:
    def __init__(self, *, exists=True, description=None, error=None):
        self.names = ["historias-usuario"] if exists else []
        self.description = deepcopy(description or compatible_description())
        self.error = error
        self.created = []
        self.deleted = 0
        self.described = []
        self.raw_index = object()

    def list_indexes(self):
        if self.error:
            raise self.error
        return {"indexes": [{"name": name} for name in self.names]}

    def describe_index(self, name):
        self.described.append(name)
        if self.error:
            raise self.error
        return deepcopy(self.description)

    def create_index(self, **kwargs):
        self.created.append(kwargs)
        self.names.append(kwargs["name"])
        self.description = compatible_description()

    def vector_index(self, name):
        assert name == "historias-usuario"
        return self.raw_index

    def delete_index(self, _name):
        self.deleted += 1


def settings(**overrides):
    return PineconeSettings(api_key=TEST_API_KEY, **overrides)


def test_missing_index_validation_does_not_create_it():
    adapter = FakePineconeAdapter(exists=False)
    client = PineconeKnowledgeClient(settings(), adapter=adapter)

    with pytest.raises(PineconeIndexNotFoundError):
        client.validate_index()

    assert adapter.created == []


def test_explicit_admin_operation_creates_only_the_required_dense_index():
    adapter = FakePineconeAdapter(exists=False)
    client = PineconeKnowledgeClient(settings(), adapter=adapter)

    result = client.create_index_if_missing()

    assert result["name"] == "historias-usuario"
    assert adapter.created == [
        {
            "name": "historias-usuario",
            "dimension": 1024,
            "metric": "cosine",
            "cloud": "aws",
            "region": "us-east-1",
            "vector_type": "dense",
        }
    ]


def test_sdk_adapter_uses_conventional_serverless_index_api(monkeypatch):
    import pinecone

    from agentes.conocimiento.client import _PineconeSDKAdapter

    calls = {}
    serverless_spec = object()

    class FakeSDKClient:
        def __init__(self, *, api_key):
            calls["api_key"] = api_key

        def create_index(self, **kwargs):
            calls["create_index"] = kwargs

    monkeypatch.setattr(pinecone, "Pinecone", FakeSDKClient)
    monkeypatch.setattr(pinecone, "ServerlessSpec", lambda **_kwargs: serverless_spec)
    adapter = _PineconeSDKAdapter(TEST_API_KEY)

    adapter.create_index(
        name="historias-usuario",
        dimension=1024,
        metric="cosine",
        cloud="aws",
        region="us-east-1",
        vector_type="dense",
    )

    assert calls["api_key"] == TEST_API_KEY
    assert calls["create_index"] == {
        "name": "historias-usuario",
        "dimension": 1024,
        "metric": "cosine",
        "spec": serverless_spec,
        "vector_type": "dense",
    }


def test_existing_compatible_index_is_validated_without_creation():
    adapter = FakePineconeAdapter()

    result = PineconeKnowledgeClient(settings(), adapter=adapter).validate_index()

    assert result["dimension"] == 1024
    assert adapter.created == []


@pytest.mark.parametrize(
    "description",
    [
        compatible_description(dimension=768),
        compatible_description(metric="dotproduct"),
        compatible_description(spec={"serverless": {"cloud": "gcp", "region": "us-east-1"}}),
        compatible_description(spec={"serverless": {"cloud": "aws", "region": "us-west-2"}}),
        compatible_description(vector_type="sparse"),
    ],
    ids=["dimension", "metric", "cloud", "region", "vector-type"],
)
def test_incompatible_existing_index_fails_without_modifying_or_deleting(description):
    adapter = FakePineconeAdapter(description=description)
    client = PineconeKnowledgeClient(settings(), adapter=adapter)

    with pytest.raises(PineconeIndexIncompatibleError):
        client.create_index_if_missing()

    assert adapter.created == []
    assert adapter.deleted == 0


def test_missing_api_key_is_a_controlled_error_and_dotenv_is_not_loaded(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "PINECONE_API_KEY=dot-env-test-value\n", encoding="utf-8"
    )
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    loaded = PineconeSettings.from_environment()
    client = PineconeKnowledgeClient(loaded)

    with pytest.raises(PineconeCredentialsMissingError) as error:
        client.validate_index()

    assert "dot-env-test-value" not in str(error.value)
    assert "dot-env-test-value" not in repr(loaded)


@pytest.mark.parametrize(
    "sdk_error, expected_error",
    [
        (FakeSDKError(status=401), PineconeAuthenticationError),
        (TimeoutError(TEST_API_KEY), PineconeTimeoutError),
        (RuntimeError(TEST_API_KEY), PineconeServiceError),
    ],
    ids=["authentication", "timeout", "service"],
)
def test_auth_timeout_and_service_errors_are_sanitized(sdk_error, expected_error):
    adapter = FakePineconeAdapter(error=sdk_error)
    client = PineconeKnowledgeClient(settings(), adapter=adapter)

    with pytest.raises(expected_error) as error:
        client.validate_index()

    assert TEST_API_KEY not in str(error.value)


@pytest.mark.parametrize("field,value", [("region", "eu-west-1"), ("cloud", "gcp")])
def test_invalid_deployment_settings_are_rejected(field, value):
    with pytest.raises(PineconeConfigurationError):
        PineconeKnowledgeClient(settings(**{field: value}), adapter=FakePineconeAdapter())


def test_injected_adapter_and_vector_store_classes_avoid_real_connections(monkeypatch):
    import pinecone
    import langchain_pinecone

    adapter = FakePineconeAdapter()
    client = PineconeKnowledgeClient(settings(), adapter=adapter)
    constructor_calls = []
    monkeypatch.setattr(
        pinecone,
        "Pinecone",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("SDK network client created")),
    )

    class FakeEmbeddings:
        def __init__(self, **kwargs):
            constructor_calls.append(("embeddings", kwargs))

    class FakeVectorStore:
        def __init__(self, **kwargs):
            constructor_calls.append(("vector_store", kwargs))
            self.kwargs = kwargs

    monkeypatch.setattr(langchain_pinecone, "PineconeEmbeddings", FakeEmbeddings)
    monkeypatch.setattr(langchain_pinecone, "PineconeVectorStore", FakeVectorStore)

    store = client.create_vector_store(namespace="glosario")

    assert isinstance(store, FakeVectorStore)
    assert constructor_calls[0][1] == {
        "model": "multilingual-e5-large",
        "dimension": 1024,
        "pinecone_api_key": TEST_API_KEY,
    }
    assert constructor_calls[1][1]["index"] is adapter.raw_index
    assert constructor_calls[1][1]["namespace"] == "glosario"


def test_index_contract_rejects_configuration_drift_without_exposing_values():
    bad_settings = PineconeSettings(api_key=TEST_API_KEY, embedding_model="other-model")

    with pytest.raises(PineconeConfigurationError) as error:
        PineconeKnowledgeClient(bad_settings, adapter=FakePineconeAdapter())

    assert "other-model" not in str(error.value)
    assert TEST_API_KEY not in str(error.value)
