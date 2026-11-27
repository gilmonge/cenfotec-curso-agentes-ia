"""Lectura y validación de las únicas fuentes autorizadas para conocimiento RAG."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from agentes.analista.memory.repositorio import RepositorioHU, detect_personal_data
from agentes.conocimiento.repositorio_codigo import raiz_codigo_relativa


logger = logging.getLogger(__name__)

AUTHORIZED_NAMESPACES = frozenset(
    {"glosario", "estandares", "checklist", "hu_aprobadas", "lecciones", "codigo"}
)


class SourceError(ValueError):
    """Error seguro para fuentes no permitidas o con estructura inválida."""


@dataclass(frozen=True)
class SourceRecord:
    namespace: str
    source_id: str
    source_kind: str
    source_ref: str
    origin: str
    text: str
    approval_status: str | None = None

    def __post_init__(self) -> None:
        validate_namespace(self.namespace)
        if not all(isinstance(value, str) and value.strip() for value in (self.source_id, self.source_ref, self.origin, self.text, self.source_kind)):
            raise SourceError("El registro de fuente está incompleto.")
        if self.source_kind in {"approved_history", "approved_lesson"} and self.approval_status != "aprobada":
            raise SourceError("El contenido del repositorio requiere aprobación explícita.")
        if self.source_kind == "simulated_reference" and self.approval_status is not None:
            raise SourceError("Una referencia simulada no puede llevar estado de aprobación.")


def validate_namespace(namespace: str) -> str:
    if not isinstance(namespace, str) or namespace not in AUTHORIZED_NAMESPACES:
        raise SourceError("Namespace de conocimiento no autorizado.")
    return namespace


def _stable_json_id(record: dict[str, Any]) -> str:
    canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


_JSON_SOURCES: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...]]] = {
    "glosario": (
        "glosario.json", "glosario", ("termino", "definicion", "fuente", "terminos"), (),
    ),
    "estandares": (
        "estandares.json", "estandares", ("id", "titulo", "regla", "referencia", "terminos"), (),
    ),
    "checklist": (
        "checklist_vacios.json", "checklist", ("id", "categoria", "descripcion", "terminos"), (),
    ),
    # Estas HU son ejemplos ficticios. Comparten el espacio de HU aprobadas
    # por compatibilidad de namespaces, pero nunca se etiquetan como aprobadas.
    "hu_similares": (
        "hu_similares.json", "hu_aprobadas", ("id", "titulo", "resumen", "aclaraciones", "similitud", "terminos"), (),
    ),
}


def _validate_json_record(name: str, item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise SourceError("El archivo JSON no cumple el esquema autorizado.")
    filename, _, required, optional = _JSON_SOURCES[name]
    if any(key not in item for key in required) or set(item) != set(required):
        raise SourceError("El archivo JSON no cumple el esquema autorizado.")
    text_fields = set(required) - {"terminos", "aclaraciones", "similitud"}
    if any(not isinstance(item[key], str) or not item[key].strip() for key in text_fields):
        raise SourceError("El archivo JSON no cumple el esquema autorizado.")
    if not isinstance(item["terminos"], list) or any(not isinstance(x, str) for x in item["terminos"]):
        raise SourceError("El archivo JSON no cumple el esquema autorizado.")
    if name == "hu_similares":
        if not isinstance(item["aclaraciones"], list) or any(not isinstance(x, str) for x in item["aclaraciones"]):
            raise SourceError("El archivo JSON no cumple el esquema autorizado.")
        if isinstance(item["similitud"], bool) or not isinstance(item["similitud"], (int, float)) or not 0 <= item["similitud"] <= 1:
            raise SourceError("El archivo JSON no cumple el esquema autorizado.")
    for key in optional:
        if key in item and not isinstance(item[key], list):
            raise SourceError("El archivo JSON no cumple el esquema autorizado.")
    return item


class AuthorizedSourceLoader:
    """Carga fuentes explícitamente permitidas; el texto resultante siempre es dato no confiable."""

    def __init__(self, project_root: str | Path | None = None, *, code_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root or Path(__file__).resolve().parents[2]).resolve()
        self.code_root = (
            Path(code_root).resolve() if code_root
            else (self.project_root / raiz_codigo_relativa(self.project_root)).resolve()
        )
        if not self._is_within(self.code_root, self.project_root):
            raise SourceError("La raíz de código debe estar dentro del proyecto autorizado.")

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def load_json_sources(self, *, fuentes_root: str | Path | None = None) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        for name in _JSON_SOURCES:
            records.extend(self.load_json_source(name, fuentes_root=fuentes_root))
        return records

    def load_json_source(self, name: str, *, fuentes_root: str | Path | None = None) -> list[SourceRecord]:
        """Carga un archivo de la allowlist; la identidad se recibe como clave lógica, nunca como ruta."""
        if name not in _JSON_SOURCES:
            raise SourceError("Fuente JSON no autorizada.")
        root = Path(fuentes_root).resolve() if fuentes_root else (self.project_root / "agentes" / "analista" / "fuentes").resolve()
        if not self._is_within(root, self.project_root):
            raise SourceError("La raíz JSON debe estar dentro del proyecto autorizado.")
        filename, namespace, _, _ = _JSON_SOURCES[name]
        path = root / filename
        if path.is_symlink() or not self._is_within(path.resolve(), root):
            raise SourceError("La ruta JSON no está autorizada.")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise SourceError("No fue posible leer una fuente JSON autorizada.") from None
        if not isinstance(data, list):
            raise SourceError("El archivo JSON no cumple el esquema autorizado.")
        records: list[SourceRecord] = []
        for item in data:
            item = _validate_json_record(name, item)
            source_id = str(item.get("id") or _stable_json_id(item))
            text = json.dumps(item, ensure_ascii=False, sort_keys=True)
            records.append(SourceRecord(
                namespace=namespace,
                source_id=source_id,
                source_kind="simulated_reference" if name == "hu_similares" else "simulated_fixture",
                source_ref=f"agentes/analista/fuentes/{filename}#{source_id}",
                origin=f"JSON ficticio: {filename}",
                text=text,
            ))
        return records

    def load_approved_repository(self, repository: RepositorioHU) -> list[SourceRecord]:
        """Usa métodos públicos y normaliza HU/lecciones aprobadas al contrato MCP."""
        records: list[SourceRecord] = []
        try:
            for summary in repository.listar_hu():
                hu = repository.obtener_hu(str(summary["id"]))
                raw_content = _repository_text(hu)
                _reject_personal_data(raw_content)
                payload = _approved_history_payload(hu)
                records.append(SourceRecord(
                    namespace="hu_aprobadas", source_id=str(hu["id"]),
                    source_kind="approved_history", source_ref=f"RepositorioHU:hu_aprobada/{hu['id']}",
                    origin="RepositorioHU (registro aprobado)",
                    text=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    approval_status="aprobada",
                ))
            for lesson in repository.listar_lecciones(estado="aprobada"):
                if lesson.get("estado") != "aprobada":
                    continue
                raw_content = _repository_text(lesson)
                _reject_personal_data(raw_content)
                payload = _approved_lesson_payload(lesson)
                records.append(SourceRecord(
                    namespace="lecciones", source_id=str(lesson["id"]),
                    source_kind="approved_lesson", source_ref=f"RepositorioHU:leccion/{lesson['id']}",
                    origin="RepositorioHU (lección aprobada)",
                    text=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    approval_status="aprobada",
                ))
        except SourceError:
            raise
        except Exception:
            # No propagar SQL, URLs, filas ni mensajes que puedan incluir datos sensibles.
            raise SourceError("No fue posible consultar el RepositorioHU de forma segura.") from None
        return records
    def load_demo_code(self) -> list[SourceRecord]:
        """Lee estáticamente solo archivos .py/.md, sin importarlos ni ejecutarlos."""
        if not self.code_root.is_dir():
            raise SourceError("La raíz de código ficticio no está disponible.")
        records: list[SourceRecord] = []
        def fail_walk(_error: OSError) -> None:
            raise SourceError("No fue posible recorrer la raíz de código ficticio.") from None

        for current, directories, files in os.walk(self.code_root, followlinks=False, onerror=fail_walk):
            current_path = Path(current)
            directories[:] = sorted(
                d for d in directories
                if not (current_path / d).is_symlink()
                and self._is_within((current_path / d).resolve(), self.code_root)
            )
            for filename in sorted(files):
                candidate = current_path / filename
                if candidate.suffix not in {".py", ".md"} or candidate.is_symlink():
                    continue
                resolved = candidate.resolve()
                if not self._is_within(resolved, self.code_root) or not resolved.is_file():
                    continue
                relative = resolved.relative_to(self.project_root).as_posix()
                try:
                    if not resolved.read_text(encoding="utf-8").strip():
                        continue  # un archivo vacío (p. ej. __init__.py) no aporta evidencia
                except (OSError, UnicodeError):
                    logger.warning("codigo_archivo_ilegible", extra={"event": "codigo_archivo_ilegible", "ruta": relative})
                    continue
                records.append(self.read_code_file(relative))
        return records

    def read_code_file(self, relative_path: str) -> SourceRecord:
        """Lee una ruta canónica relativa; rechaza traversal, absolutos, enlaces y extensiones ajenas."""
        if (
            not isinstance(relative_path, str) or "\\" in relative_path
            or "\0" in relative_path or ":" in relative_path
            or PureWindowsPath(relative_path).is_absolute() or PureWindowsPath(relative_path).drive
        ):
            raise SourceError("Ruta de código no autorizada.")
        path_parts = PurePosixPath(relative_path).parts
        if not path_parts or relative_path.startswith("/") or any(part in {"", ".", ".."} for part in path_parts):
            raise SourceError("Ruta de código no autorizada.")
        candidate = self.project_root.joinpath(*path_parts)
        if candidate.suffix not in {".py", ".md"} or candidate.is_symlink():
            raise SourceError("Ruta de código no autorizada.")
        parent = candidate.parent
        while parent != self.project_root and parent != parent.parent:
            if parent.is_symlink():
                raise SourceError("Ruta de código no autorizada.")
            parent = parent.parent
        if parent.is_symlink():
            raise SourceError("Ruta de código no autorizada.")
        try:
            resolved = candidate.resolve(strict=True)
            if not self._is_within(resolved, self.code_root) or not resolved.is_file():
                raise SourceError("Ruta de código no autorizada.")
            text = resolved.read_text(encoding="utf-8")
        except SourceError:
            raise
        except (OSError, UnicodeError, RuntimeError):
            raise SourceError("No fue posible leer el archivo de código autorizado.") from None
        rel = PurePosixPath(relative_path).as_posix()
        return SourceRecord(
            namespace="codigo", source_id=rel, source_kind="simulated_code", source_ref=rel,
            origin="Repositorio de código leído estáticamente (solo lectura); contenido no confiable", text=text,
        )


def _decode_repository_json(
    record: dict[str, Any], field: str, default: Any, expected_type: type,
) -> Any:
    value = record.get(field, default)
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            raise SourceError("El registro del RepositorioHU no cumple el esquema esperado.") from None
    if not isinstance(value, expected_type):
        raise SourceError("El registro del RepositorioHU no cumple el esquema esperado.")
    return value


def _approved_history_payload(hu: dict[str, Any]) -> dict[str, Any]:
    history = _decode_repository_json(hu, "historia", {}, dict)
    criteria = _decode_repository_json(hu, "criterios", [], list)
    clarifications = _decode_repository_json(hu, "aclaraciones", [], list)
    if any(not isinstance(item, dict) for item in clarifications):
        raise SourceError("El registro del RepositorioHU no cumple el esquema esperado.")
    title = str(hu.get("titulo") or "HU aprobada")[:200]
    requirement = str(hu.get("requerimiento") or "")
    summary = (
        f"HU aprobada por el Product Owner. Como {history.get('asA', '')}, "
        f"quiero {history.get('iWant', '')}, para {history.get('soThat', '')}"
    )[:1000]
    terms = [
        term.casefold() for term in re.findall(r"[^\W_]+", f"{title} {requirement}", flags=re.UNICODE)
        if len(term) > 2
    ][:30]
    return {
        "id": str(hu.get("codigo") or hu.get("id") or ""),
        "titulo": title,
        "resumen": summary,
        "aclaraciones": [
            f"{str(item.get('pregunta', '')).strip()} → {str(item.get('respuesta', '')).strip()}"[:400]
            for item in clarifications[:5]
        ],
        "similitud": 0.6,
        "terminos": terms,
        "tipo_informacion": str(hu.get("tipo_informacion") or ""),
        "requerimiento": requirement,
        "historia": history,
        "criterios": criteria,
        "aprobada_en": str(hu.get("aprobada_en") or ""),
    }


def _approved_lesson_payload(lesson: dict[str, Any]) -> dict[str, Any]:
    terms = lesson.get("terminos", [])
    if isinstance(terms, str):
        try:
            terms = json.loads(terms)
        except json.JSONDecodeError:
            raise SourceError("La lección aprobada no cumple el esquema esperado.") from None
    if not isinstance(terms, list) or any(not isinstance(term, str) for term in terms):
        raise SourceError("La lección aprobada no cumple el esquema esperado.")
    return {
        "id": str(lesson.get("id") or ""),
        "categoria": str(lesson.get("categoria") or "Datos requeridos"),
        "descripcion": str(lesson.get("pregunta_sugerida") or "")[:500],
        "terminos": terms,
        "evidencia": (
            "Lección aprendida aprobada tras un cambio posterior al grooming de una HU del Repositorio; "
            "requiere validación humana."
        ),
    }


def _repository_text(record: dict[str, Any]) -> str:
    # Esquema canónico ordenado para que IDs/contenido no dependan del orden de columnas SQL.
    return json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)


def _reject_personal_data(text: str) -> None:
    if detect_personal_data(text):
        raise SourceError("Se excluyó contenido del repositorio por posible dato personal.")

