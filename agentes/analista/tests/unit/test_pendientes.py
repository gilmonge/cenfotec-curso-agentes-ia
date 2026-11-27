"""Pendientes por rol, avisos a quien creó la historia y mensaje de Teams al Product Owner."""
from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentes.analista.api.errors import install_error_handlers
from agentes.analista.api.routes import pendientes
from agentes.analista.api.routes.workflows import _avisar
from agentes.analista.core.workflow_models import POApprovalDecision
from agentes.analista.memory.repositorio import RepositorioHU
from agentes.notificaciones.teams_service import TeamsService, tarjeta_por_aprobar
from agentes.seguridad.catalogo import ACCION
from agentes.seguridad.clave import FirmaSesion

FLUJO_PO = {"id": "11111111-1111-1111-1111-111111111111", "titulo": "Fecha de nacimiento", "espera": "product_owner_approval",
            "modo": "pre_grooming", "creado_por": "Luis", "actualizado_en": "2026-11-26"}
FLUJO_NEGOCIO = {"id": "22222222-2222-2222-2222-222222222222", "titulo": "Teléfono", "espera": "business_answers",
                 "modo": "pre_grooming", "creado_por": "Luis", "actualizado_en": "2026-11-26"}


@pytest.fixture()
def repositorio(tmp_path):
    return RepositorioHU(tmp_path / "repo.db")


def _cliente(repositorio, usuario):
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(pendientes.router, prefix="/api/analista")
    app.state.repositorio = repositorio
    app.state.workflow_runtime = SimpleNamespace(listar=lambda: [dict(FLUJO_PO), dict(FLUJO_NEGOCIO)])
    app.state.seguridad = SimpleNamespace(obtener_usuario=lambda _id: usuario)
    app.state.firma_sesion = FirmaSesion("prueba")
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {app.state.firma_sesion.emitir(usuario['id'])}"
    return cliente


def test_el_po_ve_lo_que_espera_su_aprobacion_y_el_analista_no(repositorio):
    po = {"id": "po", "nombre": "Ana", "activo": True, "roles": [], "acciones": [ACCION.HISTORIA_APROBAR]}
    respuesta = _cliente(repositorio, po).get("/api/analista/pendientes").json()
    assert [(p["tipo"], p["titulo"]) for p in respuesta["por_decidir"]] == [("por_aprobar", "Fecha de nacimiento")]

    analista = {"id": "an", "nombre": "Luis", "activo": True, "roles": [], "acciones": [ACCION.HISTORIA_CREAR]}
    assert _cliente(repositorio, analista).get("/api/analista/pendientes").json()["por_decidir"] == []


def test_quien_creo_la_historia_recibe_el_aviso_de_devolucion_y_lo_marca_leido(repositorio):
    runtime = SimpleNamespace(
        metadatos=lambda _id: {"titulo": "Fecha de nacimiento", "creado_por": "Luis", "creado_por_usuario": "an"},
        pending_interrupt=lambda _id: None,
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(repositorio=repositorio, teams=TeamsService(""))))
    po = {"id": "po", "nombre": "Ana"}
    decision = SimpleNamespace(decision=POApprovalDecision.RETURN_TO_WRITER, reason="Falta el criterio de menores")
    _avisar(request, runtime, FLUJO_PO["id"], espera_previa="product_owner_approval", usuario=po, decision_po=decision)

    analista = {"id": "an", "nombre": "Luis", "activo": True, "roles": [], "acciones": [ACCION.HISTORIA_CREAR]}
    cliente = _cliente(repositorio, analista)
    avisos = cliente.get("/api/analista/pendientes").json()["avisos"]
    assert [(a["tipo"], a["detalle"], a["autor"]) for a in avisos] == [("devuelta", "Falta el criterio de menores", "Ana")]
    assert cliente.post(f"/api/analista/pendientes/avisos/{avisos[0]['id']}/leido").status_code == 204
    assert cliente.get("/api/analista/pendientes").json()["total"] == 0


def test_teams_recibe_una_tarjeta_cuando_la_historia_queda_por_aprobar(monkeypatch):
    enviados = []
    monkeypatch.setattr(httpx, "post", lambda url, json, timeout: enviados.append((url, json)) or httpx.Response(
        202, request=httpx.Request("POST", url)))
    monkeypatch.setenv("APP_URL", "https://app.ejemplo")
    teams = TeamsService("https://teams.ejemplo/flujo")
    runtime = SimpleNamespace(metadatos=lambda _id: {"titulo": "Fecha de nacimiento", "creado_por": "Luis"},
                              pending_interrupt=lambda _id: {"payload": {"kind": "product_owner_approval"}})
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(repositorio=None, teams=teams)))
    _avisar(request, runtime, FLUJO_PO["id"], espera_previa="business_answers", usuario={"id": "an", "nombre": "Luis"})
    # Si ya esperaba la aprobación, no se repite el mensaje.
    _avisar(request, runtime, FLUJO_PO["id"], espera_previa="product_owner_approval", usuario={"id": "an", "nombre": "Luis"})
    assert len(enviados) == 1
    texto = str(enviados[0][1])
    assert "Fecha de nacimiento" in texto and "https://app.ejemplo/historias/nueva?flujo=" in texto


def test_sin_url_de_teams_no_se_envia_nada():
    assert TeamsService("").enviar(tarjeta_por_aprobar("x", None, None)) is False
