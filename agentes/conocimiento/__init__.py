"""Integración segura con el índice vectorial Pinecone del backend."""

from .client import PineconeKnowledgeClient
from .config import PineconeSettings
from .contract import DEFAULT_INDEX_CONTRACT, PineconeIndexContract
from .errors import (
    PineconeAuthenticationError,
    PineconeConfigurationError,
    PineconeCredentialsMissingError,
    PineconeIndexIncompatibleError,
    PineconeIndexNotFoundError,
    PineconeRateLimitError,
    PineconeServiceError,
    PineconeTimeoutError,
)
from .retrieval import KnowledgeRetriever, KnowledgeSource, RetrievalResult

__all__ = [
    "DEFAULT_INDEX_CONTRACT",
    "PineconeAuthenticationError",
    "PineconeConfigurationError",
    "PineconeCredentialsMissingError",
    "PineconeIndexContract",
    "PineconeIndexIncompatibleError",
    "PineconeIndexNotFoundError",
    "PineconeRateLimitError",
    "PineconeKnowledgeClient",
    "PineconeServiceError",
    "PineconeSettings",
    "PineconeTimeoutError",
    "KnowledgeRetriever",
    "KnowledgeSource",
    "RetrievalResult",
]
