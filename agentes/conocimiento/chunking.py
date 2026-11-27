"""Fragmentación determinista con límite de entrada del embedding Pinecone configurado."""
from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from copy import deepcopy

from langchain_core.documents import Document

from .documents import MAX_STRUCTURED_PAYLOAD_BYTES, validate_document_metadata
from .ids import stable_document_id


# Pinecone documenta 507 tokens máximos para multilingual-e5-large. El conteo
# local usa bytes UTF-8 como cota superior conservadora para SentencePiece: cada
# pieza consume al menos un byte del texto. Se reservan dos posiciones para los
# tokens especiales de inicio y fin que agrega el tokenizer del modelo.
MAX_EMBEDDING_INPUT_TOKENS = 507
RESERVED_SPECIAL_TOKENS = 2
DEFAULT_CHUNK_CHAR_LIMIT = 480
TokenCounter = Callable[[str], int]


def _conservative_token_count(text: str) -> int:
    """Cota superior conservadora en bytes para el tokenizer SentencePiece XLM-R."""
    return len(text.encode("utf-8"))


def _fit_chunk(text: str, start: int, max_end: int, token_counter: TokenCounter, token_limit: int) -> int:
    """Encuentra el prefijo más largo dentro del presupuesto sin cambiar su contenido."""
    low, high = start + 1, max_end
    best = start
    while low <= high:
        middle = (low + high) // 2
        if token_counter(text[start:middle]) <= token_limit:
            best = middle
            low = middle + 1
        else:
            high = middle - 1
    if best == start:
        raise ValueError("Un carácter excede el límite del modelo de embeddings.")
    return best


def chunk_documents(
    documents: Iterable[Document], *, token_counter: TokenCounter = _conservative_token_count,
    token_limit: int = MAX_EMBEDDING_INPUT_TOKENS, char_limit: int = DEFAULT_CHUNK_CHAR_LIMIT,
) -> list[Document]:
    if isinstance(token_limit, bool) or not isinstance(token_limit, int) or not 1 <= token_limit <= MAX_EMBEDDING_INPUT_TOKENS:
        raise ValueError("El límite de tokens debe estar entre 1 y el máximo del modelo.")
    if isinstance(char_limit, bool) or not isinstance(char_limit, int) or char_limit < 1:
        raise ValueError("El límite de caracteres debe ser positivo.")
    # La cota también deja espacio para <s> y </s> que el tokenizer de XLM-R
    # agrega alrededor de cada entrada.
    safe_content_limit = min(token_limit, MAX_EMBEDDING_INPUT_TOKENS - RESERVED_SPECIAL_TOKENS)
    output: list[Document] = []
    for document in documents:
        validate_document_metadata(document.metadata)
        text = document.page_content
        if not text.strip():
            continue
        pieces: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + char_limit, len(text))
            if token_counter(text[start:end]) > safe_content_limit:
                end = _fit_chunk(text, start, end, token_counter, safe_content_limit)
            pieces.append(text[start:end])
            start = end
        structured_payload: str | None = None
        if len(pieces) > 1 and document.metadata.get("source_kind") != "simulated_code":
            try:
                parsed = json.loads(text)
            except (TypeError, json.JSONDecodeError):
                parsed = None
            if isinstance(parsed, dict):
                if len(text.encode("utf-8")) > MAX_STRUCTURED_PAYLOAD_BYTES:
                    raise ValueError("El registro JSON excede el límite de metadata permitido.")
                structured_payload = text
        for index, piece in enumerate(pieces):
            metadata = deepcopy(document.metadata)
            metadata["chunk"] = index
            if structured_payload is not None:
                metadata["source_payload"] = structured_payload
            validate_document_metadata(metadata)
            source_ref = metadata["source_ref"]
            source_id = metadata["source_id"]
            namespace = metadata["namespace"]
            output.append(Document(
                id=stable_document_id(namespace, source_ref, source_id, index),
                page_content=piece,
                metadata=metadata,
            ))
    return output

