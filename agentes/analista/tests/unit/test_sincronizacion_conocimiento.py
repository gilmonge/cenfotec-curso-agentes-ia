"""Carga automática de Pinecone: solo lo que cambió o está vacío, sin pasos manuales."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentes.analista.memory.repositorio import RepositorioHU
from agentes.conocimiento import estado_carga
from agentes.conocimiento.sincronizacion import FUENTE_ORDEN, SincronizadorConocimiento, _conteo_desde_estadistica

LLENO = {"glosario": 5, "estandares": 5, "checklist": 5, "codigo": 5, "hu_aprobadas": 5}


def _sincronizador(tmp_path: Path, *, conteo=None, falla: set[str] | None = None, habilitado=True):
    repositorio = RepositorioHU(tmp_path / "memoria.db")
    llamada: list[str] = []

    def ingestar(fuente):
        llamada.append(fuente)
        if falla and fuente in falla:
            return {"status": "partial_failure", "errors": [{"code": "UPSERT_FAILED"}]}
        return {"status": "success", "errors": []}

    sincronizador = SincronizadorConocimiento(
        repositorio=repositorio, ingestar=ingestar,
        contar_namespace=lambda: dict(conteo if conteo is not None else LLENO),
        preparar_codigo=lambda: None, habilitado=lambda: habilitado,
    )
    return sincronizador, repositorio, llamada


def test_first_run_loads_every_source_and_second_run_loads_nothing(tmp_path):
    sincronizador, _repositorio, llamada = _sincronizador(tmp_path)

    primero = sincronizador.sincronizar()
    llamada.clear()
    segundo = sincronizador.sincronizar()

    assert set(primero.values()) == {"cargada"}
    assert set(segundo.values()) == {"sin_cambios"}
    assert llamada == []


def test_an_empty_namespace_is_reloaded_even_if_the_fingerprint_matches(tmp_path):
    sincronizador, _repositorio, llamada = _sincronizador(tmp_path)
    sincronizador.sincronizar()
    llamada.clear()
    sincronizador._contar_namespace = lambda: {**LLENO, "glosario": 0}

    resultado = sincronizador.sincronizar()

    assert llamada == ["glosario"]
    assert resultado["glosario"] == "cargada"


def test_failed_load_keeps_old_fingerprint_so_it_retries_next_time(tmp_path):
    sincronizador, repositorio, llamada = _sincronizador(tmp_path, falla={"codigo"})

    assert sincronizador.sincronizar()["codigo"] == "fallida"
    assert repositorio.obtener_huella("codigo") is None
    llamada.clear()
    sincronizador.sincronizar()
    assert llamada == ["codigo"]


def test_approving_a_story_reloads_only_the_repository_source(tmp_path):
    sincronizador, repositorio, llamada = _sincronizador(tmp_path)
    sincronizador.sincronizar()
    llamada.clear()
    repositorio.al_cambiar_conocimiento = sincronizador.programar_repositorio

    repositorio.guardar_hu({
        "id": "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01", "codigo": "HU-CLI-DAT-001", "titulo": "Teléfono opcional",
        "tipo_informacion": "Minuta", "requerimiento": "El teléfono deja de ser obligatorio.",
        "historia": {"asA": "analista", "iWant": "guardar sin teléfono", "soThat": "registrar al cliente"},
        "criterios": [], "aclaraciones": [],
    })
    sincronizador.esperar(5)

    assert llamada == ["repositorio"]
    llamada.clear()
    assert sincronizador.sincronizar()["repositorio"] == "sin_cambios"


def test_without_pinecone_key_it_only_prepares_the_code_repository(tmp_path):
    preparado = []
    sincronizador, _repositorio, llamada = _sincronizador(tmp_path, habilitado=False)
    sincronizador._preparar_codigo = lambda: preparado.append(True)

    sincronizador.iniciar_en_segundo_plano()
    sincronizador.esperar(5)
    sincronizador.programar_repositorio()

    assert preparado == [True]
    assert llamada == []
    assert estado_carga.pinecone_disponible()


def test_retriever_uses_local_copy_while_the_initial_load_is_running():
    from agentes.analista.core.agent_registry import AgentId
    from agentes.conocimiento.retrieval import KnowledgeRetriever

    class NeverPinecone:
        def __call__(self):
            raise AssertionError("No debe consultar Pinecone durante la carga inicial.")

    estado_carga.marcar_carga_inicial(True)
    try:
        resultado = KnowledgeRetriever(client_factory=NeverPinecone()).search(
            agent_role=AgentId.ANALYST, query="vigencia de póliza", namespace="glosario", limit=3,
        )
    finally:
        estado_carga.marcar_carga_inicial(False)

    assert resultado.status == "degraded"
    assert resultado.error_code == "KNOWLEDGE_SYNC_IN_PROGRESS"


@pytest.mark.parametrize("estadistica", [
    {"namespaces": {"glosario": {"vector_count": 3}}},
    type("Stats", (), {"namespaces": {"glosario": type("NS", (), {"vector_count": 3})()}})(),
])
def test_namespace_counts_are_read_from_dicts_or_sdk_objects(estadistica):
    assert _conteo_desde_estadistica(estadistica) == {"glosario": 3}


def test_source_order_matches_ingestion_choices():
    from agentes.conocimiento.ingesta import SOURCE_CHOICES

    assert set(FUENTE_ORDEN) == set(SOURCE_CHOICES) - {"todas"}
