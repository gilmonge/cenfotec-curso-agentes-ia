"""Load and identify the analyst system prompt without exposing its contents."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


class PromptLoadError(RuntimeError):
    """Raised when the configured system prompt cannot be trusted."""


@dataclass(frozen=True, slots=True)
class PromptSnapshot:
    text: str
    version: str
    sha256: str
    path: Path


_VERSION = re.compile(r"^\*\*Versión editorial:\*\*\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", re.MULTILINE)
DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "sistema.md"


def load_prompt(path: str | Path = DEFAULT_PROMPT_PATH) -> PromptSnapshot:
    """Read a non-empty prompt and return only a digest/version for diagnostics."""
    prompt_path = Path(path).resolve()
    try:
        text = prompt_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise PromptLoadError("No se pudo cargar el prompt del agente.") from exc
    if not text:
        raise PromptLoadError("El prompt del agente está vacío.")
    match = _VERSION.search(text)
    if match is None:
        raise PromptLoadError("El prompt no declara una versión editorial válida.")
    return PromptSnapshot(
        text=text,
        version=match.group(1),
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        path=prompt_path,
    )


def verify_loaded_prompt(snapshot: PromptSnapshot, server_prompt: str | None) -> bool:
    """Verify prompt content regardless of Windows/Unix line endings."""
    if not isinstance(server_prompt, str) or not server_prompt.strip():
        return False

    def normalize(text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n").strip()

    return normalize(server_prompt) == normalize(snapshot.text)
