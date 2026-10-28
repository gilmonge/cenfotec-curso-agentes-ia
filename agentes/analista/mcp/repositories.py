"""Read-only access to the small, fictitious MCP source fixtures."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "fuentes"
_FILES = {
    "glosario": "glosario.json",
    "historias": "hu_similares.json",
    "estandares": "estandares.json",
    "checklist": "checklist_vacios.json",
}


def _load_fixture(key: str) -> list[dict[str, Any]]:
    if key not in _FILES:
        raise ValueError("Fuente de datos no permitida")
    path = (_SOURCE_ROOT / _FILES[key]).resolve()
    if path.parent != _SOURCE_ROOT.resolve():
        raise RuntimeError("Ruta de fixture inválida")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("No se pudo cargar una fuente de referencia") from exc
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise RuntimeError("El fixture no cumple el formato esperado")
    return value


def load_sources() -> dict[str, list[dict[str, Any]]]:
    """Load only named local fixtures; user input is never treated as a path."""
    return {key: _load_fixture(key) for key in _FILES}
