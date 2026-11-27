"""Cliente lazy e inyectable para validar y aprovisionar el índice Pinecone."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .config import PineconeSettings
from .contract import DEFAULT_INDEX_CONTRACT, PineconeIndexContract
from .errors import (
    PineconeAuthenticationError,
    PineconeConfigurationError,
    PineconeCredentialsMissingError,
    PineconeIndexIncompatibleError,
    PineconeIndexNotFoundError,
    PineconeKnowledgeError,
    PineconeRateLimitError,
    PineconeServiceError,
    PineconeTimeoutError,
)


class PineconeControlPlane(Protocol):
    """Operaciones mínimas requeridas del cliente de control/data plane."""

    def list_indexes(self) -> Any: ...

    def describe_index(self, name: str) -> Any: ...

    def create_index(
        self,
        *,
        name: str,
        dimension: int,
        metric: str,
        cloud: str,
        region: str,
        vector_type: str,
    ) -> Any: ...

    def vector_index(self, name: str) -> Any: ...


class _PineconeSDKAdapter:
    """Adaptador fino sobre el SDK oficial; no expone operaciones destructivas."""

    def __init__(self, api_key: str) -> None:
        from pinecone import Pinecone

        self._client = Pinecone(api_key=api_key)

    def list_indexes(self) -> Any:
        return self._client.list_indexes()

    def describe_index(self, name: str) -> Any:
        return self._client.describe_index(name)

    def create_index(
        self,
        *,
        name: str,
        dimension: int,
        metric: str,
        cloud: str,
        region: str,
        vector_type: str,
    ) -> Any:
        from pinecone import ServerlessSpec

        return self._client.create_index(
            name=name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(cloud=cloud, region=region),
            vector_type=vector_type,
        )

    def vector_index(self, name: str) -> Any:
        return self._client.Index(name)


class PineconeKnowledgeClient:
    """Valida el índice por defecto y expone creación solo por llamada explícita.

    La instancia no conecta ni crea recursos durante su construcción. Las
    pruebas inyectan un adaptador; producción crea el SDK al primer uso, después
    de comprobar que la clave existe.
    """

    def __init__(
        self,
        settings: PineconeSettings | None = None,
        *,
        adapter: PineconeControlPlane | None = None,
        contract: PineconeIndexContract = DEFAULT_INDEX_CONTRACT,
    ) -> None:
        self.settings = settings or PineconeSettings.from_environment()
        self.contract = contract
        self.settings.validate()
        if self._contract_settings_mismatch():
            raise PineconeConfigurationError()
        self._adapter = adapter

    def validate_index(self) -> Any:
        """Valida el índice existente. Nunca crea, modifica ni elimina recursos."""

        adapter = self._get_adapter()
        names = self._call(adapter.list_indexes)
        if self.contract.name not in _index_names(names):
            raise PineconeIndexNotFoundError()
        description = self._call(adapter.describe_index, self.contract.name)
        self._validate_description(description)
        return description

    def create_index_if_missing(self) -> Any:
        """Operación administrativa explícita: crea solo cuando el nombre falta.

        Si el nombre ya existe, solo lo valida. Un índice incompatible se deja
        intacto y el error no dispara eliminación, recreación ni actualización.
        """

        adapter = self._get_adapter()
        names = self._call(adapter.list_indexes)
        if self.contract.name in _index_names(names):
            description = self._call(adapter.describe_index, self.contract.name)
            self._validate_description(description)
            return description

        self._call(
            adapter.create_index,
            name=self.contract.name,
            dimension=self.contract.dimension,
            metric=self.contract.metric,
            cloud=self.contract.cloud,
            region=self.contract.region,
            vector_type=self.contract.vector_type,
        )
        description = self._call(adapter.describe_index, self.contract.name)
        self._validate_description(description)
        return description

    def create_vector_store(self, *, namespace: str) -> Any:
        """Construye el vector store convencional después de validar el índice."""

        self.validate_index()
        adapter = self._get_adapter()
        api_key = self._api_key()
        try:
            from langchain_pinecone import PineconeEmbeddings, PineconeVectorStore

            embeddings = PineconeEmbeddings(
                model=self.contract.embedding_model,
                dimension=self.contract.dimension,
                pinecone_api_key=api_key,
            )
            return PineconeVectorStore(
                index=adapter.vector_index(self.contract.name),
                embedding=embeddings,
                namespace=namespace,
            )
        except PineconeKnowledgeError:
            raise
        except Exception as exc:
            raise _translate_error(exc) from None

    def get_vector_index(self) -> Any:
        """Return the conventional data-plane index after explicit contract validation."""
        self.validate_index()
        return self._get_adapter().vector_index(self.contract.name)

    def _get_adapter(self) -> PineconeControlPlane:
        api_key = self._api_key()
        if self._adapter is None:
            try:
                self._adapter = _PineconeSDKAdapter(api_key)
            except Exception as exc:
                raise _translate_error(exc) from None
        return self._adapter

    def _api_key(self) -> str:
        key = self.settings.api_key
        if not key or not key.strip():
            raise PineconeCredentialsMissingError()
        return key

    def _contract_settings_mismatch(self) -> bool:
        return any(
            getattr(self.settings, setting_name) != getattr(self.contract, contract_name)
            for setting_name, contract_name in (
                ("index_name", "name"),
                ("cloud", "cloud"),
                ("region", "region"),
                ("dimension", "dimension"),
                ("metric", "metric"),
                ("embedding_model", "embedding_model"),
            )
        )

    def _call(self, function: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except PineconeKnowledgeError:
            raise
        except Exception as exc:
            raise _translate_error(exc) from None

    def _validate_description(self, description: Any) -> None:
        serverless = _get(description, "spec", "serverless")
        actual = {
            "name": _get(description, "name"),
            "vector_type": _get(description, "vector_type") or "dense",
            "dimension": _get(description, "dimension"),
            "metric": _get(description, "metric"),
            "cloud": _get(serverless, "cloud"),
            "region": _get(serverless, "region"),
        }
        expected = {
            "name": self.contract.name,
            "vector_type": self.contract.vector_type,
            "dimension": self.contract.dimension,
            "metric": self.contract.metric,
            "cloud": self.contract.cloud,
            "region": self.contract.region,
        }
        if actual != expected:
            raise PineconeIndexIncompatibleError()


def _get(value: Any, key: str, nested_key: str | None = None) -> Any:
    if isinstance(value, Mapping):
        result = value.get(key)
    else:
        result = getattr(value, key, None)
    if nested_key is None or result is None:
        return result
    if isinstance(result, Mapping):
        return result.get(nested_key)
    return getattr(result, nested_key, None)


def _index_names(response: Any) -> set[str]:
    indexes = _get(response, "indexes")
    if indexes is None:
        indexes = response
    if isinstance(indexes, Mapping):
        indexes = indexes.values()
    names: set[str] = set()
    try:
        for item in indexes:
            name = _get(item, "name")
            if name is None and isinstance(item, str):
                name = item
            if isinstance(name, str):
                names.add(name)
    except TypeError:
        return set()
    return names


def _translate_error(error: Exception) -> PineconeKnowledgeError:
    status_code = getattr(error, "status", None) or getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    if status_code is None and response is not None:
        status_code = getattr(response, "status_code", None)
    name = type(error).__name__.lower()
    if status_code in (401, 403) or "unauthor" in name or "authentication" in name:
        return PineconeAuthenticationError()
    if status_code == 429 or "ratelimit" in name or "rate_limit" in name:
        return PineconeRateLimitError()
    if isinstance(error, TimeoutError) or "timeout" in name or "timedout" in name:
        return PineconeTimeoutError()
    return PineconeServiceError()
