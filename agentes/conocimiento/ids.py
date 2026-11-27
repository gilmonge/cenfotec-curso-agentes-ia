"""Identificadores deterministas del almacén vectorial."""
from __future__ import annotations

import hashlib

from .sources import validate_namespace


def stable_document_id(namespace: str, source_ref: str, source_id: str, chunk: int) -> str:
    validate_namespace(namespace)
    if not source_ref or not source_id or isinstance(chunk, bool) or chunk < 0:
        raise ValueError("La identidad de documento no es válida.")
    identity = f"{namespace}\0{source_ref}\0{source_id}\0{chunk}".encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()
    return f"{namespace}:{digest}"

