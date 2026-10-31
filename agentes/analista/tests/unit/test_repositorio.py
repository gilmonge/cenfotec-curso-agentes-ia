"""Repositorio de HU (base de datos SQLAlchemy; SQLite en pruebas): aprobación humana, lecciones y lectura por el agente."""
from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from agentes.analista.api import errors
from agentes.analista.api.routes import historias, repositorio
from agentes.analista.mcp import tools
from agentes.analista.memory.repositorio import RepositorioHU, detect_personal_data, es_guid, load_memory_entries

G0 = "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c99"
HU = {
    "id": "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01",
    "titulo": "Modificar vigencia de cobertura adicional",
    "tipo_informacion": "Minuta",
    "requerimiento": "Negocio pide ajustar la vigencia de la cobertura adicional en renovaciones.",
    "historia": {"asA": "analista de pólizas", "iWant": "ajustar la vigencia", "soThat": "la renovación sea consistente"},
    "criterios": [{"text": "La vigencia se valida al guardar", "given": "", "when": "", "then": ""}],
    "aclaraciones": [{"pregunta": "¿Desde cuándo aplica?", "respuesta": "Desde la próxima renovación"}],
    "confirmo_anonimizada": True,
}


@pytest_asyncio.fixture
async def client(tmp_path):
    app = FastAPI()
    errors.install_error_handlers(app)
    app.include_router(repositorio.router, prefix="/api/analista")
    app.include_router(historias.router, prefix="/api/analista")
    app.state.repositorio = RepositorioHU(tmp_path / "repo.db")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http, app


@pytest.mark.asyncio
async def test_approved_hu_is_saved_and_listed(client):
    http, _ = client
    saved = await http.post("/api/analista/repositorio/historias", json=HU)
    assert saved.status_code == 201
    listed = await http.get("/api/analista/repositorio/historias")
    assert [item["id"] for item in listed.json()] == ["0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01"]


@pytest.mark.asyncio
async def test_anonymization_confirmation_and_pii_are_enforced(client):
    http, _ = client
    missing = await http.post("/api/analista/repositorio/historias", json={**HU, "confirmo_anonimizada": False})
    assert missing.status_code == 422
    with_pii = {**HU, "requerimiento": "Escribir a cliente@ejemplo.com sobre la póliza"}
    rejected = await http.post("/api/analista/repositorio/historias", json=with_pii)
    assert rejected.status_code == 422
    assert "datos personales" in rejected.json()["error"]["message"]


def test_pii_detector_ignores_formatted_amounts():
    assert detect_personal_data("Monto 1.250.000,50 y 4 decimales") == []
    assert detect_personal_data("Cédula 123456789")
    assert detect_personal_data("1-2345-6789")


@pytest.mark.asyncio
async def test_change_request_creates_proposed_lesson_that_needs_approval(client):
    http, app = client
    await http.post("/api/analista/repositorio/historias", json=HU)
    change = {
        "hu_id": "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01", "solicitud": "Negocio pide también aplicar a endosos",
        "clasificacion": "cambio_alcance", "causa_raiz": "Reglas de negocio",
        "pregunta_sugerida": "¿Aplica también a los endosos de la cobertura?", "terminos": ["endoso"],
    }
    created = await http.post("/api/analista/repositorio/cambios", json=change)
    assert created.status_code == 201 and created.json()["estado"] == "propuesta"
    # Una lección propuesta todavía no entra en el checklist del agente.
    assert load_memory_entries(app.state.repositorio.fuente)[1] == []
    lesson_id = created.json()["leccion_id"]
    decided = await http.post(f"/api/analista/repositorio/lecciones/{lesson_id}/decision", json={"decision": "aprobar"})
    assert decided.json()["estado"] == "aprobada"
    stories, checklist = load_memory_entries(app.state.repositorio.fuente)
    assert stories[0]["id"] == "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01"
    assert checklist[0]["id"] == lesson_id and es_guid(lesson_id)
    assert checklist[0]["categoria"] == "Reglas de negocio"


@pytest.mark.asyncio
async def test_change_on_unknown_hu_and_invalid_decision_fail(client):
    http, _ = client
    change = {
        "hu_id": "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c00", "solicitud": "x", "clasificacion": "aclaracion", "causa_raiz": "Validaciones",
        "pregunta_sugerida": "¿Qué validación aplica?",
    }
    missing = await http.post("/api/analista/repositorio/cambios", json=change)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "REPOSITORY_NOT_FOUND"
    bad = await http.post(f"/api/analista/repositorio/lecciones/{G0}/decision", json={"decision": "otra"})
    assert bad.status_code == 422


def test_agent_tools_read_approved_memory(tmp_path, monkeypatch):
    repo = RepositorioHU(tmp_path / "memoria.db")
    repo.guardar_hu({k: v for k, v in HU.items() if k != "confirmo_anonimizada"})
    result = repo.registrar_cambio(
        hu_id="0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01", solicitud="Cambio posterior", clasificacion="aclaracion", causa_raiz="Datos requeridos",
        pregunta_sugerida="¿Cuál es el formato exacto del campo de vigencia?", terminos=["vigencia"],
    )
    repo.decidir_leccion(result["leccion_id"], "aprobar")
    monkeypatch.setenv("ANALISTA_REPO_DB", str(repo.fuente))
    monkeypatch.setattr(tools, "_SOURCES", tools.load_sources())
    stories = tools.buscar_hu_similares("vigencia cobertura adicional renovación", 5)
    assert "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01" in {story.id for story in stories.historias}
    checklist = tools.aplicar_checklist_vacios("formato del campo de vigencia", 5)
    ids = {item.id for category in checklist.categorias for item in category.items}
    assert result['leccion_id'] in ids


def test_missing_database_returns_empty_memory(tmp_path):
    assert load_memory_entries(tmp_path / "no-existe.db") == ([], [])


@pytest.mark.asyncio
async def test_deleting_a_hu_removes_its_changes_lessons_and_agent_memory(client):
    http, app = client
    await http.post("/api/analista/repositorio/historias", json=HU)
    change = await http.post("/api/analista/repositorio/cambios", json={
        "hu_id": "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01", "solicitud": "Aplicar la vigencia también a endosos", "clasificacion": "cambio_alcance",
        "causa_raiz": "Reglas de negocio", "pregunta_sugerida": "¿La vigencia aplica a endosos?", "terminos": ["vigencia"],
    })
    await http.post(f"/api/analista/repositorio/lecciones/{change.json()['leccion_id']}/decision", json={"decision": "aprobar"})
    assert load_memory_entries(app.state.repositorio.fuente)[0]

    deleted = await http.delete("/api/analista/repositorio/historias/0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01")
    assert deleted.status_code == 204
    assert (await http.get("/api/analista/repositorio/historias")).json() == []
    assert (await http.get("/api/analista/repositorio/cambios?hu_id=0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01")).json() == []
    assert (await http.get("/api/analista/repositorio/lecciones")).json() == []
    assert load_memory_entries(app.state.repositorio.fuente) == ([], [])


@pytest.mark.asyncio
async def test_deleting_an_unknown_hu_is_not_found_and_ids_are_validated(client):
    http, _ = client
    missing = await http.delete("/api/analista/repositorio/historias/0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c04")
    assert missing.status_code == 404
    invalid = await http.delete("/api/analista/repositorio/historias/x%20y")
    assert invalid.status_code in (404, 422)


@pytest.mark.asyncio
async def test_work_stories_are_shared_through_the_database(client, tmp_path):
    http, app = client
    story = {"id": "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c77", "title": "Historia de trabajo", "status": "borrador", "questions": []}
    assert (await http.get("/api/analista/historias")).json() == []
    saved = await http.put("/api/analista/historias/0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c77", json=story)
    assert saved.status_code == 200
    changed = await http.put("/api/analista/historias/0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c77", json={**story, "status": "revisada"})
    assert changed.json()["status"] == "revisada"
    # Otro dispositivo (nueva instancia sobre la misma base) ve los mismos datos.
    otra = RepositorioHU(app.state.repositorio.fuente)
    assert [item["status"] for item in otra.listar_historias()] == ["revisada"]
    assert (await http.delete("/api/analista/historias/0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c77")).status_code == 204
    assert (await http.get("/api/analista/historias")).json() == []


@pytest.mark.asyncio
async def test_work_story_id_must_match_the_route(client):
    http, _ = client
    mismatch = await http.put("/api/analista/historias/0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c11", json={"id": "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c22"})
    assert mismatch.status_code == 422
    oversized = await http.put("/api/analista/historias/0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c03", json={"id": "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c03", "texto": "x" * 250_000})
    assert oversized.status_code == 422


def test_mysql_urls_are_normalized_with_a_short_connection_lifetime():
    from agentes.analista.memory.base_datos import crear_motor, normalizar_url

    assert normalizar_url("mysql://u:p@host:4000/db").drivername == "mysql+pymysql"
    motor = crear_motor("mysql://u:p@127.0.0.1:1/db")
    assert motor.pool._recycle == 240


@pytest.mark.asyncio
async def test_every_key_and_relation_is_a_guid_and_non_guid_ids_are_rejected(client):
    http, app = client
    await http.post("/api/analista/repositorio/historias", json=HU)
    created = await http.post("/api/analista/repositorio/cambios", json={
        "hu_id": HU["id"], "solicitud": "Cambio", "clasificacion": "aclaracion", "causa_raiz": "Validaciones",
        "pregunta_sugerida": "¿Qué validación aplica?",
    })
    assert es_guid(created.json()["solicitud_id"]) and es_guid(created.json()["leccion_id"])
    lesson = (await http.get("/api/analista/repositorio/lecciones")).json()[0]
    change = (await http.get(f"/api/analista/repositorio/cambios?hu_id={HU['id']}")).json()[0]
    assert lesson["solicitud_id"] == change["id"] and lesson["hu_id"] == HU["id"]
    assert (await http.post("/api/analista/repositorio/historias", json={**HU, "id": "HU-901"})).status_code == 422
    assert (await http.put("/api/analista/historias/HU-901", json={"id": "HU-901"})).status_code == 422


def test_work_story_keeps_the_readable_code_in_its_own_column(tmp_path):
    repo = RepositorioHU(tmp_path / "codigo.db")
    repo.guardar_historia(G0, {"id": G0, "number": "HU-ABC-001", "title": "Prueba"})
    from sqlalchemy import text
    with repo.motor.connect() as conexion:
        assert conexion.execute(text("SELECT codigo FROM historia")).scalar() == "HU-ABC-001"


def test_a_database_with_the_old_numeric_schema_stops_startup_with_a_clear_message(tmp_path):
    from sqlalchemy import create_engine, text
    ruta = tmp_path / "antigua.db"
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    with motor.begin() as conexion:
        conexion.execute(text("CREATE TABLE leccion (id INTEGER PRIMARY KEY AUTOINCREMENT, hu_id TEXT)"))
    motor.dispose()
    with pytest.raises(RuntimeError, match="esquema anterior"):
        RepositorioHU(ruta)


@pytest.mark.asyncio
async def test_codes_are_separate_from_ids(client):
    http, _ = client
    await http.post("/api/analista/repositorio/historias", json={**HU, "codigo": "HU-PRU-001"})
    for texto in ("Primer cambio", "Segundo cambio"):
        await http.post("/api/analista/repositorio/cambios", json={
            "hu_id": HU["id"], "solicitud": texto, "clasificacion": "aclaracion", "causa_raiz": "Validaciones",
            "pregunta_sugerida": "¿Qué validación aplica?",
        })
    lecciones = (await http.get("/api/analista/repositorio/lecciones")).json()
    assert sorted(item["codigo"] for item in lecciones) == ["LEC-001", "LEC-002"]
    assert {item["hu_codigo"] for item in lecciones} == {"HU-PRU-001"}
    assert all(item["id"] != item["codigo"] for item in lecciones)


@pytest.mark.asyncio
async def test_reapproving_the_same_hu_replaces_the_current_revision_without_duplicating_it(client):
    http, app = client
    assert (await http.post("/api/analista/repositorio/historias", json=HU)).status_code == 201
    revisada = {**HU, "historia": {**HU["historia"], "iWant": "ajustar la vigencia también en endosos"}}
    assert (await http.post("/api/analista/repositorio/historias", json=revisada)).status_code == 201

    listed = await http.get("/api/analista/repositorio/historias")
    assert [item["id"] for item in listed.json()] == [HU["id"]]
    vigente = app.state.repositorio.obtener_hu(HU["id"])
    historia = vigente["historia"]
    historia = json.loads(historia) if isinstance(historia, str) else historia
    assert historia["iWant"] == "ajustar la vigencia también en endosos"


@pytest.mark.asyncio
async def test_a_lesson_is_created_only_when_the_suggested_question_is_given(client):
    http, _ = client
    await http.post("/api/analista/repositorio/historias", json=HU)
    base = {"hu_id": "0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01"}
    correccion = await http.post("/api/analista/repositorio/cambios", json={
        **base, "solicitud": "El rol se llama Ejecutivo de Servicio", "clasificacion": "correccion",
    })
    assert correccion.status_code == 201 and correccion.json()["leccion_id"] is None
    nota = await http.post("/api/analista/repositorio/cambios", json={
        **base, "solicitud": "El campo es opcional", "clasificacion": "aclaracion",
    })
    assert nota.status_code == 201 and nota.json()["leccion_id"] is None
    # Negocio cambió de decisión: no hubo vacío del análisis, así que no hay lección.
    sin_leccion = await http.post("/api/analista/repositorio/cambios", json={
        **base, "solicitud": "Aplicar a endosos", "clasificacion": "cambio_alcance",
    })
    assert sin_leccion.status_code == 201 and sin_leccion.json()["leccion_id"] is None
    listado = await http.get(f"/api/analista/repositorio/cambios?hu_id={base['hu_id']}")
    assert {c["clasificacion"] for c in listado.json()} == {"correccion", "aclaracion", "cambio_alcance"}
    assert (await http.get("/api/analista/repositorio/lecciones")).json() == []
