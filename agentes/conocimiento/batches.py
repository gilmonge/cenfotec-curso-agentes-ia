"""Lotes validados y reconciliación limitada a una sola fuente/namespace."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from langchain_core.documents import Document

from .chunking import TokenCounter, chunk_documents
from .documents import source_to_document, validate_document_metadata
from .sources import SourceRecord, validate_namespace


@dataclass(frozen=True)
class PreparedBatch:
    namespace: str
    source_id: str
    source_ref: str
    documents: tuple[Document, ...]

    def __post_init__(self) -> None:
        validate_namespace(self.namespace)
        if not all(isinstance(value, str) and value for value in (self.source_id, self.source_ref)):
            raise ValueError("La identidad de fuente del lote está incompleta.")
        for document in self.documents:
            validate_document_metadata(document.metadata)
            if not isinstance(document.id, str) or not document.id:
                raise ValueError("El lote contiene un documento sin ID estable.")
            if (document.metadata["namespace"], document.metadata["source_id"], document.metadata["source_ref"]) != (
                self.namespace, self.source_id, self.source_ref,
            ):
                raise ValueError("El lote contiene un documento de otra fuente.")
        ids = [document.id for document in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("El lote contiene IDs duplicados.")


def prepare_batches(
    sources: Iterable[SourceRecord], *, token_counter: TokenCounter | None = None,
) -> list[PreparedBatch]:
    groups: dict[tuple[str, str, str], list[SourceRecord]] = {}
    for source in sources:
        groups.setdefault((source.namespace, source.source_id, source.source_ref), []).append(source)
    batches: list[PreparedBatch] = []
    for (namespace, source_id, source_ref), records in sorted(groups.items()):
        initial = [source_to_document(record) for record in records]
        chunks = chunk_documents(initial, **({"token_counter": token_counter} if token_counter else {}))
        batches.append(PreparedBatch(namespace, source_id, source_ref, tuple(chunks)))
    return batches


def obsolete_ids(existing_documents: Iterable[Document], batch: PreparedBatch) -> set[str]:
    """Calcula IDs antiguos solo entre vectores cuya fuente y namespace coinciden exactamente."""
    current_ids = {document.id for document in batch.documents}
    stale: set[str] = set()
    for existing in existing_documents:
        metadata = existing.metadata
        if (
            metadata.get("namespace") == batch.namespace
            and metadata.get("source_id") == batch.source_id
            and metadata.get("source_ref") == batch.source_ref
            and isinstance(existing.id, str)
            and existing.id not in current_ids
        ):
            stale.add(existing.id)
    return stale

