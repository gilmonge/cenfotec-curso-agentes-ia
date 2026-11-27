"""Carga automática del conocimiento en Pinecone, sin pasos manuales.

- Al arrancar (en segundo plano): descarga el repositorio del Asesor y, si hay clave de
  Pinecone, crea el índice si falta y carga solo las fuentes que cambiaron o que están
  vacías en el índice.
- Al aprobar, editar o eliminar una HU, o al aprobar una lección: recarga la fuente
  ``repositorio`` para que el agente la encuentre enseguida.

Para saber qué cambió se guarda una huella por fuente en la base de datos (tabla
``sincronizacion_conocimiento``): el hash de cada JSON, el resumen de HU y lecciones
aprobadas y el commit del repositorio del Asesor. Si algo falla, el servicio sigue con
la copia local y se registra en el log; la próxima ejecución lo vuelve a intentar.
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from .config import PineconeSettings
from .estado_carga import marcar_carga_inicial
from .repositorio_codigo import PROJECT_ROOT, origen_repositorio, raiz_codigo_relativa, sincronizar_desde_entorno

logger = logging.getLogger(__name__)

FUENTE_ORDEN: tuple[str, ...] = ("glosario", "estandares", "checklist", "hu_similares", "repositorio", "codigo")
ARCHIVO_JSON: Mapping[str, str] = {
    "glosario": "glosario.json",
    "estandares": "estandares.json",
    "checklist": "checklist_vacios.json",
    "hu_similares": "hu_similares.json",
}
# Fuentes que llenan un namespace propio: si el namespace está vacío, se recargan aunque la huella coincida.
NAMESPACE_PROPIO: Mapping[str, str] = {
    "glosario": "glosario", "estandares": "estandares", "checklist": "checklist", "codigo": "codigo",
}

Ingestor = Callable[[str], Mapping[str, Any]]
ContadorNamespace = Callable[[], Mapping[str, int]]


def sincronizacion_habilitada() -> bool:
    """Requiere clave de Pinecone; se puede apagar con PINECONE_SINCRONIZACION_AUTOMATICA=0."""
    apagada = os.environ.get("PINECONE_SINCRONIZACION_AUTOMATICA", "1").strip().casefold() in {"0", "false", "no"}
    return not apagada and bool(PineconeSettings.from_environment().api_key)


def _conteo_desde_estadistica(estadistica: Any) -> dict[str, int]:
    namespaces = getattr(estadistica, "namespaces", None)
    if namespaces is None and isinstance(estadistica, Mapping):
        namespaces = estadistica.get("namespaces")
    salida: dict[str, int] = {}
    for nombre, resumen in (namespaces or {}).items():
        cantidad = getattr(resumen, "vector_count", None)
        if cantidad is None and isinstance(resumen, Mapping):
            cantidad = resumen.get("vector_count", 0)
        salida[str(nombre)] = int(cantidad or 0)
    return salida


def _contar_en_pinecone() -> dict[str, int]:
    from .client import PineconeKnowledgeClient

    cliente = PineconeKnowledgeClient()
    cliente.create_index_if_missing()
    return _conteo_desde_estadistica(cliente.get_vector_index().describe_index_stats())


def _hash(texto: str | bytes) -> str:
    return hashlib.sha256(texto if isinstance(texto, bytes) else texto.encode("utf-8")).hexdigest()


class SincronizadorConocimiento:
    """Coordina la carga en segundo plano; un solo hilo a la vez y reintento si llegan cambios durante una carga."""

    def __init__(
        self,
        *,
        repositorio: Any | None = None,
        ingestar: Ingestor | None = None,
        contar_namespace: ContadorNamespace | None = None,
        preparar_codigo: Callable[[], Any] | None = None,
        habilitado: Callable[[], bool] | None = None,
        project_root: Path | None = None,
    ) -> None:
        self._repositorio = repositorio
        self._ingestar = ingestar or self._ingestar_con_cli
        self._contar_namespace = contar_namespace or _contar_en_pinecone
        self._preparar_codigo = preparar_codigo or sincronizar_desde_entorno
        self._habilitado = habilitado or sincronizacion_habilitada
        self._root = (project_root or PROJECT_ROOT).resolve()
        self._lock = threading.Lock()
        self._pendiente: set[str] = set()
        self._hilo: threading.Thread | None = None
        self.ultimo_resultado: dict[str, str] = {}

    # --- Huellas ---------------------------------------------------------
    def huella(self, fuente: str) -> str | None:
        if fuente in ARCHIVO_JSON:
            ruta = self._root / "agentes" / "analista" / "fuentes" / ARCHIVO_JSON[fuente]
            return _hash(ruta.read_bytes())
        if fuente == "repositorio":
            return self._repositorio.huella_repositorio() if self._repositorio is not None else None
        if fuente == "codigo":
            origen = origen_repositorio(self._root)
            if origen.get("tipo") == "repositorio":
                return _hash(f"{origen.get('repositorio')}@{origen.get('commit')}")
            raiz = self._root / raiz_codigo_relativa(self._root)
            partes = [
                f"{ruta.relative_to(self._root).as_posix()}:{_hash(ruta.read_bytes())}"
                for ruta in sorted(raiz.rglob("*")) if ruta.is_file() and ruta.suffix in {".py", ".md"}
            ]
            return _hash("\n".join(partes))
        raise ValueError("Fuente de conocimiento no autorizada.")

    def _huella_guardada(self, fuente: str) -> str | None:
        if self._repositorio is None:
            return None
        try:
            return self._repositorio.obtener_huella(fuente)
        except Exception as exc:
            logger.warning("huella_no_disponible", extra={"event": "huella_no_disponible", "fuente": fuente, "error": type(exc).__name__})
            return None

    def _guardar_huella(self, fuente: str, huella: str | None) -> None:
        if self._repositorio is None or huella is None:
            return
        try:
            self._repositorio.guardar_huella(fuente, huella)
        except Exception as exc:
            logger.warning("huella_no_guardada", extra={"event": "huella_no_guardada", "fuente": fuente, "error": type(exc).__name__})

    def _ingestar_con_cli(self, fuente: str) -> Mapping[str, Any]:
        from .ingesta import run_ingestion

        fabrica = (lambda: self._repositorio) if self._repositorio is not None else None
        return run_ingestion(fuente=fuente, crear_indice=True, repository_factory=fabrica)

    # --- Carga -------------------------------------------------------------
    def sincronizar(self, lista_fuente: Iterable[str] = FUENTE_ORDEN) -> dict[str, str]:
        """Carga lo que cambió o está vacío; devuelve el resultado por fuente (cargada, sin_cambios, fallida)."""
        resultado: dict[str, str] = {}
        try:
            conteo = dict(self._contar_namespace())
        except Exception as exc:
            logger.warning("pinecone_no_disponible_para_carga", extra={"event": "pinecone_no_disponible_para_carga", "error": type(exc).__name__})
            return {fuente: "fallida" for fuente in lista_fuente}
        for fuente in lista_fuente:
            try:
                huella = self.huella(fuente)
            except (OSError, ValueError) as exc:
                logger.warning("huella_no_calculada", extra={"event": "huella_no_calculada", "fuente": fuente, "error": type(exc).__name__})
                huella = None
            namespace = NAMESPACE_PROPIO.get(fuente)
            vacio = namespace is not None and conteo.get(namespace, 0) == 0
            if huella is not None and huella == self._huella_guardada(fuente) and not vacio:
                resultado[fuente] = "sin_cambios"
                continue
            try:
                salida = self._ingestar(fuente)
            except Exception as exc:
                logger.warning("carga_conocimiento_fallida", extra={"event": "carga_conocimiento_fallida", "fuente": fuente, "error": type(exc).__name__})
                resultado[fuente] = "fallida"
                continue
            if salida.get("status") == "success":
                self._guardar_huella(fuente, huella)
                resultado[fuente] = "cargada"
            else:
                codigo = [str(item.get("code")) for item in salida.get("errors", []) if isinstance(item, Mapping)][:5]
                logger.warning("carga_conocimiento_parcial", extra={"event": "carga_conocimiento_parcial", "fuente": fuente, "codigo": codigo})
                resultado[fuente] = "fallida"
        self.ultimo_resultado.update(resultado)
        logger.info("carga_conocimiento", extra={"event": "carga_conocimiento", "resultado": resultado})
        print(f"Conocimiento (Pinecone): {resultado}", flush=True)
        return resultado

    def _arranque(self) -> None:
        try:
            preparado = self._preparar_codigo()
            detalle = getattr(preparado, "detalle", None)
            if detalle:
                print(f"Repositorio del Asesor Técnico: raíz {getattr(preparado, 'raiz', '?')}. {detalle}", flush=True)
        except Exception as exc:
            logger.warning("repositorio_codigo_no_preparado", extra={"event": "repositorio_codigo_no_preparado", "error": type(exc).__name__})
        try:
            if self._habilitado():
                self.sincronizar()
        finally:
            marcar_carga_inicial(False)
            self._procesar_pendiente()

    def iniciar_en_segundo_plano(self) -> threading.Thread:
        """Al arrancar la aplicación: no bloquea el puerto ni las peticiones."""
        if self._habilitado():
            marcar_carga_inicial(True)
        with self._lock:
            return self._lanzar(self._arranque)

    def programar_repositorio(self) -> None:
        """Al aprobar/editar/eliminar una HU o aprobar una lección: recarga la fuente repositorio."""
        if not self._habilitado():
            return
        with self._lock:
            self._pendiente.add("repositorio")
            if self._hilo is None:
                self._lanzar(self._procesar_pendiente)

    def esperar(self, segundo: float | None = None) -> None:
        """Espera a que termine la carga en curso (pruebas y diagnóstico)."""
        with self._lock:
            hilo = self._hilo
        if hilo is not None:
            hilo.join(segundo)

    def _procesar_pendiente(self) -> None:
        while True:
            with self._lock:
                lista = [fuente for fuente in FUENTE_ORDEN if fuente in self._pendiente]
                self._pendiente.clear()
                if not lista:
                    self._hilo = None
                    return
            self.sincronizar(lista)

    def _lanzar(self, objetivo: Callable[[], None]) -> threading.Thread:
        """Debe llamarse con ``self._lock`` tomado: así nunca hay dos hilos de carga a la vez."""
        hilo = threading.Thread(target=objetivo, name="carga-conocimiento", daemon=True)
        self._hilo = hilo
        hilo.start()
        return hilo
