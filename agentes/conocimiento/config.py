"""Configuración Pinecone cargada exclusivamente desde el entorno del backend."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .errors import PineconeConfigurationError


@dataclass(frozen=True)
class PineconeSettings:
    """Valores permitidos para el índice y la integración de embeddings.

    La clave se omite de ``repr``. ``from_environment`` consulta únicamente
    ``os.environ`` y nunca carga archivos dotenv.
    """

    api_key: str | None = field(default=None, repr=False)
    index_name: str = "historias-usuario"
    cloud: str = "aws"
    region: str = "us-east-1"
    dimension: int = 1024
    metric: str = "cosine"
    embedding_model: str = "multilingual-e5-large"

    @classmethod
    def from_environment(cls) -> "PineconeSettings":
        dimension_value = os.environ.get("PINECONE_DIMENSION", "1024")
        try:
            dimension = int(dimension_value)
        except (TypeError, ValueError):
            raise PineconeConfigurationError() from None

        settings = cls(
            api_key=os.environ.get("PINECONE_API_KEY") or None,
            index_name=os.environ.get("PINECONE_INDEX_NAME", "historias-usuario"),
            cloud=os.environ.get("PINECONE_CLOUD", "aws"),
            region=os.environ.get("PINECONE_REGION", "us-east-1"),
            dimension=dimension,
            metric=os.environ.get("PINECONE_METRIC", "cosine"),
            embedding_model=os.environ.get(
                "PINECONE_EMBEDDING_MODEL", "multilingual-e5-large"
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        expected = {
            "index_name": "historias-usuario",
            "cloud": "aws",
            "region": "us-east-1",
            "dimension": 1024,
            "metric": "cosine",
            "embedding_model": "multilingual-e5-large",
        }
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise PineconeConfigurationError()
        if self.api_key is not None and not self.api_key.strip():
            raise PineconeConfigurationError()

