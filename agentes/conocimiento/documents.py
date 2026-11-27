"""Transformación validada de fuentes autorizadas a documentos LangChain."""
from __future__ import annotations

import json
from typing import Any

from langchain_core.documents import Document

from .ids import stable_document_id
from .sources import SourceError, SourceRecord, validate_namespace


APPROVED_KINDS = frozenset({"approved_history", "approved_lesson"})
SIMULATED_KINDS = frozenset({"simulated_reference", "simulated_fixture", "simulated_code"})
MAX_STRUCTURED_PAYLOAD_BYTES = 30_000


def validate_document_metadata(metadata: dict[str, Any]) -> None:
    required = {"namespace", "source_id", "source_kind", "source_ref", "chunk", "origin", "content_untrusted"}
    if not isinstance(metadata, dict) or not required.issubset(metadata):
        raise SourceError("La metadata del documento está incompleta.")
    if not isinstance(metadata["namespace"], str):
        raise SourceError("La metadata del documento no es válida.")
    validate_namespace(metadata["namespace"])
    if not all(isinstance(metadata[key], str) and metadata[key] for key in ("source_id", "source_kind", "source_ref", "origin")):
        raise SourceError("La metadata del documento no es válida.")
    if metadata["source_kind"] not in APPROVED_KINDS | SIMULATED_KINDS:
        raise SourceError("El tipo de fuente no está autorizado.")
    if isinstance(metadata["chunk"], bool) or not isinstance(metadata["chunk"], int) or metadata["chunk"] < 0:
        raise SourceError("El índice de fragmento no es válido.")
    if metadata["content_untrusted"] is not True:
        raise SourceError("El contenido debe marcarse como no confiable.")
    if metadata["source_kind"] in APPROVED_KINDS:
        if metadata.get("approval_status") != "aprobada":
            raise SourceError("La fuente del repositorio debe estar aprobada.")
    elif metadata.get("approval_status") is not None:
        raise SourceError("Una fuente simulada no puede marcarse como aprobada.")
    if "source_payload" in metadata:
        payload = metadata["source_payload"]
        if metadata["source_kind"] == "simulated_code":
            raise SourceError("El código recuperado no puede incluir un payload estructurado.")
        if not isinstance(payload, str) or not payload or len(payload.encode("utf-8")) > MAX_STRUCTURED_PAYLOAD_BYTES:
            raise SourceError("El payload estructurado excede el límite permitido.")
        try:
            parsed_payload = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            raise SourceError("El payload estructurado no es JSON válido.") from None
        if not isinstance(parsed_payload, dict):
            raise SourceError("El payload estructurado debe ser un objeto JSON.")


def source_to_document(source: SourceRecord, *, chunk: int = 0) -> Document:
    metadata: dict[str, Any] = {
        "namespace": source.namespace,
        "source_id": source.source_id,
        "source_kind": source.source_kind,
        "source_ref": source.source_ref,
        "chunk": chunk,
        "origin": source.origin,
        "content_untrusted": True,
    }
    if source.approval_status is not None:
        metadata["approval_status"] = source.approval_status
    validate_document_metadata(metadata)
    return Document(
        id=stable_document_id(source.namespace, source.source_ref, source.source_id, chunk),
        page_content=source.text,
        metadata=metadata,
    )


def split_approval_classes(documents: list[Document]) -> tuple[list[Document], list[Document]]:
    """Devuelve (aprobados, simulados); las referencias nunca pasan al grupo aprobado."""
    approved: list[Document] = []
    simulated: list[Document] = []
    for doc in documents:
        validate_document_metadata(doc.metadata)
        if doc.metadata["source_kind"] in APPROVED_KINDS:
            approved.append(doc)
        else:
            simulated.append(doc)
    return approved, simulated

