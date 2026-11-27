"""Contrato fijo del índice vectorial convencional."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PineconeIndexContract:
    name: str = "historias-usuario"
    vector_type: str = "dense"
    cloud: str = "aws"
    region: str = "us-east-1"
    dimension: int = 1024
    metric: str = "cosine"
    embedding_model: str = "multilingual-e5-large"


DEFAULT_INDEX_CONTRACT = PineconeIndexContract()
