"""Recuperación read-only por rol, con citas verificadas y fallback local."""
from __future__ import annotations

import json
import logging
import math
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.documents import Document
from pydantic import BaseModel, ConfigDict, Field

from agentes.analista.core.agent_registry import AGENT_NAMESPACE_ALLOWLIST, AgentId
from agentes.equipo import listar_definicion
from agentes.analista.memory.repositorio import detect_personal_data, load_memory_entries

from .client import PineconeKnowledgeClient
from .documents import APPROVED_KINDS, validate_document_metadata
from .estado_carga import pinecone_disponible
from .repositorio_codigo import es_ruta_codigo
from .sources import AuthorizedSourceLoader, SourceRecord, validate_namespace

logger = logging.getLogger(__name__)


class KnowledgeSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    source_kind: str
    source_ref: str
    namespace: str
    chunk: int = Field(ge=0)
    score: float
    backend: Literal["pinecone", "local"]
    citation: str
    text: str
    content_untrusted: Literal[True] = True


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["ok", "degraded"]
    backend: Literal["pinecone", "local", "none"]
    namespace: str
    sources: list[KnowledgeSource]
    error_code: str | None = None


LocalSourceProvider = Callable[[], Iterable[SourceRecord | Document]]
PineconeClientFactory = Callable[[], PineconeKnowledgeClient]

# Tipos de fuente que cada agente puede leer por namespace: salen de su definición (agentes/equipo/<id>).
_ROLE_ALLOWED_KINDS: dict[AgentId, dict[str, frozenset[str]]] = {
    AgentId(definicion.id): dict(definicion.fuente) for definicion in listar_definicion()
}

_STOPWORDS = frozenset(
    "a al algo ante aqui asi bajo como con contra cual cuando codigo existe de del desde donde durante e el ella en entre era es esa ese eso esta este esto estos fue ha han hasta hay la las le les lo los mas me mi muy ni no nos o para pero por que se segun ser si sin sobre son su sus te tiene todo tras un una uno unos y ya".split()
)


def _resolve_role(role: AgentId | str) -> AgentId:
    try:
        resolved = role if isinstance(role, AgentId) else AgentId(role)
    except (TypeError, ValueError):
        raise ValueError("Rol de agente no autorizado para conocimiento.") from None
    return resolved


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    folded = "".join(char for char in normalized if not unicodedata.combining(char))
    words = set(re.findall(r"[^\W_]+", folded, flags=re.UNICODE)) - _STOPWORDS
    stems = {
        word[:-2] if word.endswith("es") and len(word) > 6 else
        word[:-1] if word.endswith("s") and len(word) > 4 else word
        for word in words
    }
    return stems - _STOPWORDS


def _local_sources() -> list[SourceRecord]:
    """Read allowlisted fixtures and approved repository entries without executing code."""
    loader = AuthorizedSourceLoader()
    records = loader.load_json_sources()
    records.extend(loader.load_demo_code())
    try:
        histories, lessons = load_memory_entries()
    except Exception as exc:
        # The existing local repository reader fails closed and may be absent.
        logger.info("knowledge_repository_unavailable", extra={"event": "knowledge_repository_unavailable", "error": type(exc).__name__})
        histories, lessons = [], []
    for item in histories:
        if not isinstance(item, Mapping):
            continue
        source_id = str(item.get("id", ""))
        text = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if not source_id or detect_personal_data(text):
            continue
        records.append(SourceRecord(
            namespace="hu_aprobadas", source_id=source_id, source_kind="approved_history",
            source_ref=f"RepositorioHU:hu_aprobada/{source_id}",
            origin="RepositorioHU (registro aprobado)", text=text, approval_status="aprobada",
        ))
    for item in lessons:
        if not isinstance(item, Mapping):
            continue
        source_id = str(item.get("id", ""))
        text = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if not source_id or detect_personal_data(text):
            continue
        records.append(SourceRecord(
            namespace="lecciones", source_id=source_id, source_kind="approved_lesson",
            source_ref=f"RepositorioHU:leccion/{source_id}",
            origin="RepositorioHU (lección aprobada)", text=text, approval_status="aprobada",
        ))
    return records


@dataclass(frozen=True)
class _Candidate:
    document: Document
    score: float


class KnowledgeRetriever:
    """Resolve one authorized namespace per request and mark fallback provenance."""

    def __init__(
        self,
        *,
        client_factory: PineconeClientFactory | None = None,
        local_source_provider: LocalSourceProvider | None = None,
    ) -> None:
        self._client_factory = client_factory or PineconeKnowledgeClient
        self._local_source_provider = local_source_provider or _local_sources

    def search(
        self,
        *,
        agent_role: AgentId | str,
        query: str,
        namespace: str,
        limit: int = 5,
    ) -> RetrievalResult:
        role = _resolve_role(agent_role)
        namespace = validate_namespace(namespace)
        if namespace not in AGENT_NAMESPACE_ALLOWLIST[role] or namespace not in _ROLE_ALLOWED_KINDS[role]:
            raise ValueError("Namespace no permitido para el rol de agente.")
        if not isinstance(query, str) or not query.strip() or len(query) > 4000:
            raise ValueError("La consulta debe contener entre 1 y 4.000 caracteres no vacíos.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 25:
            raise ValueError("El límite de resultados no es válido.")

        if not pinecone_disponible():
            # Carga inicial en curso: el índice puede estar vacío o a medias.
            sources = self._search_local(role, query, namespace, limit)
            return RetrievalResult(
                status="degraded", backend="local" if sources else "none", namespace=namespace,
                sources=sources, error_code="KNOWLEDGE_SYNC_IN_PROGRESS",
            )
        try:
            matches = self._search_pinecone(role, query, namespace, limit)
        except Exception as exc:
            code = _safe_backend_error_code(exc)
            sources = self._search_local(role, query, namespace, limit)
            return RetrievalResult(
                status="degraded", backend="local" if sources else "none", namespace=namespace,
                sources=sources, error_code=code,
            )
        sources = [self._to_source(match.document, match.score, namespace, "pinecone") for match in matches]
        return RetrievalResult(status="ok", backend="pinecone", namespace=namespace, sources=sources)

    def _search_pinecone(self, role: AgentId, query: str, namespace: str, limit: int) -> list[_Candidate]:
        store = self._client_factory().create_vector_store(namespace=namespace)
        filters = _metadata_filter(role, namespace)
        try:
            raw = store.similarity_search_with_score(query, k=limit, filter=filters)
        except TypeError:
            # Older supported LangChain adapter versions accept no filter kwarg.
            if filters:
                raw = store.similarity_search_with_score(query, k=limit)
            else:
                raise
        output: list[_Candidate] = []
        for item in raw:
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            document, score = item
            if not isinstance(document, Document) or not _eligible_document(document, role, namespace):
                continue
            try:
                numeric_score = float(score)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(numeric_score):
                continue
            output.append(_Candidate(document, numeric_score))
        return output[:limit]

    def _search_local(self, role: AgentId, query: str, namespace: str, limit: int) -> list[KnowledgeSource]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        candidates: list[_Candidate] = []
        try:
            records = list(self._local_source_provider())
        except Exception as exc:
            logger.warning("knowledge_local_sources_unavailable", extra={"event": "knowledge_local_sources_unavailable", "error": type(exc).__name__})
            return []
        for item in records:
            if isinstance(item, SourceRecord):
                from .documents import source_to_document

                document = source_to_document(item)
            elif isinstance(item, Document):
                document = item
            else:
                continue
            if not _eligible_document(document, role, namespace):
                continue
            searchable = " ".join((document.page_content, str(document.metadata.get("source_ref", ""))))
            overlap = query_tokens & _tokens(searchable)
            if overlap:
                score = len(overlap) / max(len(query_tokens), 1)
                candidates.append(_Candidate(document, score))
        candidates.sort(key=lambda item: (-item.score, str(item.document.metadata["source_ref"]), item.document.metadata["chunk"]))
        output: list[KnowledgeSource] = []
        for match in candidates[:limit]:
            try:
                output.append(self._to_source(match.document, match.score, namespace, "local"))
            except ValueError:
                continue
        return output

    def _to_source(self, document: Document, score: float, namespace: str, backend: Literal["pinecone", "local"]) -> KnowledgeSource:
        validate_document_metadata(document.metadata)
        metadata = document.metadata
        if metadata.get("namespace") != namespace or not _valid_source_ref(metadata):
            raise ValueError("La metadata de la fuente recuperada no es válida.")
        citation = str(metadata["source_ref"])
        source_text = metadata.get("source_payload", document.page_content)
        return KnowledgeSource(
            source_id=metadata["source_id"], source_kind=metadata["source_kind"],
            source_ref=citation, namespace=namespace, chunk=metadata["chunk"],
            score=score, backend=backend, citation=citation,
            text=source_text, content_untrusted=True,
        )


def _metadata_filter(role: AgentId, namespace: str) -> dict[str, Any]:
    if role == AgentId.CHANGE_MANAGER and namespace == "hu_aprobadas":
        return {"source_kind": {"$eq": "approved_history"}, "approval_status": {"$eq": "aprobada"}}
    if role == AgentId.CHANGE_MANAGER and namespace == "lecciones":
        return {"source_kind": {"$eq": "approved_lesson"}, "approval_status": {"$eq": "aprobada"}}
    return {}


def _safe_backend_error_code(error: BaseException) -> str:
    code = getattr(error, "code", None)
    if isinstance(code, str) and re.fullmatch(r"[A-Z0-9_]{1,64}", code):
        return code
    response = getattr(error, "response", None)
    status = getattr(error, "status", None) or getattr(error, "status_code", None)
    if status is None and response is not None:
        status = getattr(response, "status_code", None)
    name = type(error).__name__.casefold()
    if status in (401, 403) or "unauthor" in name or "authentication" in name:
        return "PINECONE_AUTHENTICATION_FAILED"
    if status == 404:
        return "PINECONE_INDEX_NOT_FOUND"
    if status == 429 or "ratelimit" in name or "rate_limit" in name:
        return "PINECONE_RATE_LIMITED"
    if isinstance(error, TimeoutError) or "timeout" in name or "timedout" in name:
        return "PINECONE_TIMEOUT"
    return "KNOWLEDGE_BACKEND_UNAVAILABLE"


def _eligible_document(document: Document, role: AgentId, namespace: str) -> bool:
    try:
        validate_document_metadata(document.metadata)
    except Exception:
        return False
    metadata = document.metadata
    if metadata.get("namespace") != namespace:
        return False
    if metadata.get("source_kind") not in _ROLE_ALLOWED_KINDS[role].get(namespace, frozenset()):
        return False
    if role == AgentId.CHANGE_MANAGER and namespace in {"hu_aprobadas", "lecciones"}:
        if metadata.get("source_kind") not in APPROVED_KINDS or metadata.get("approval_status") != "aprobada":
            return False
    return _valid_source_ref(metadata)


def _valid_source_ref(metadata: Mapping[str, Any]) -> bool:
    ref = metadata.get("source_ref")
    kind = metadata.get("source_kind")
    namespace = metadata.get("namespace")
    if not isinstance(ref, str) or not ref or "\\" in ref or ".." in ref:
        return False
    if namespace == "codigo":
        if kind != "simulated_code" or metadata.get("source_id") != ref:
            return False
        try:
            AuthorizedSourceLoader().read_code_file(ref)
        except Exception:
            return False
        return es_ruta_codigo(ref)
    if kind in APPROVED_KINDS:
        prefix = "RepositorioHU:hu_aprobada/" if kind == "approved_history" else "RepositorioHU:leccion/"
        return (
            ref == prefix + str(metadata.get("source_id"))
            and metadata.get("approval_status") == "aprobada"
        )
    fixture_names = {
        "glosario": "glosario.json",
        "estandares": "estandares.json",
        "checklist": "checklist_vacios.json",
        "hu_aprobadas": "hu_similares.json",
    }
    filename = fixture_names.get(str(namespace))
    return bool(
        filename
        and kind in {"simulated_fixture", "simulated_reference"}
        and ref == f"agentes/analista/fuentes/{filename}#{metadata.get('source_id')}"
    )


_default_retriever: KnowledgeRetriever | None = None


def establecer_recuperador(retriever: Any | None) -> None:
    """Sustituye el recuperador que usan las herramientas MCP (pruebas y diagnóstico; None restaura)."""
    global _default_retriever
    _default_retriever = retriever


def get_knowledge_retriever() -> KnowledgeRetriever:
    """Create only a local Python object; Pinecone is contacted only by search()."""
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = KnowledgeRetriever()
    return _default_retriever
