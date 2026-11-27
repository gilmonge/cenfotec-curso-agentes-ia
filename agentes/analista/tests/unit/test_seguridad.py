"""Usuarios, roles, acciones, inicio de sesión y permisos por ruta."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from agentes.analista.api.errors import WorkflowApiError, install_error_handlers
from agentes.analista.api.routes import historias, seguridad
from agentes.analista.api.routes.workflows import _exigir_permiso_respuesta
from agentes.analista.core.workflow_models import POApprovalDecision
from agentes.analista.memory.base_datos import crear_motor
from agentes.seguridad.catalogo import ACCION, CODIGO_ACCION, LISTA_ACCION, LISTA_ROL_INICIAL
from agentes.seguridad.clave import FirmaSesion, cifrar_clave, verificar_clave
from agentes.seguridad.repositorio_seguridad import RepositorioSeguridad, SeguridadError


@pytest.fixture()
def repositorio(tmp_path):
    repo = RepositorioSeguridad(crear_motor(tmp_path / "seguridad.db"))
    repo.inicializar("admin", "clave-inicial-1")
    return repo


def _rol(repo, nombre):
    return next(r for r in repo.listar_rol() if r["nombre"] == nombre)


def test_catalogo_tiene_codigos_unicos_y_nombres_legibles():
    codigos = [a.codigo for a in LISTA_ACCION]
    assert len(codigos) == len(set(codigos))
    for accion in LISTA_ACCION:
        assert accion.nombre and accion.modulo
        assert "." not in accion.nombre, "el nombre es para la persona; el código queda en el programa"
    for _, _, lista in LISTA_ROL_INICIAL:
        assert set(lista) <= CODIGO_ACCION


def test_clave_y_token():
    guardada = cifrar_clave("secreta-123")
    assert verificar_clave("secreta-123", guardada) and not verificar_clave("otra", guardada)
    firma = FirmaSesion("semilla")
    token = firma.emitir("u-1", ahora=1000)
    assert firma.validar(token, ahora=1001) == "u-1"
    assert firma.validar(token + "x", ahora=1001) is None
    assert firma.validar(token, ahora=1000 + 13 * 3600) is None
    assert FirmaSesion("otra").validar(token, ahora=1001) is None


def test_arranque_crea_roles_y_administrador_una_sola_vez(repositorio):
    repositorio.inicializar("admin", "otra-clave-xx")
    assert {r["nombre"] for r in repositorio.listar_rol()} == {n for n, _, _ in LISTA_ROL_INICIAL}
    admin = repositorio.autenticar("admin", "clave-inicial-1")
    assert admin and set(admin["acciones"]) == CODIGO_ACCION
    assert repositorio.autenticar("admin", "otra-clave-xx") is None


def test_asignar_roles_a_usuarios_y_acciones_a_roles(repositorio):
    po = _rol(repositorio, "Product Owner")
    ana = repositorio.crear_usuario("ana.mora", "Ana Mora", "clave-ana-123", [po["id"]])
    assert ACCION.HISTORIA_APROBAR in ana["acciones"] and ACCION.HISTORIA_CREAR not in ana["acciones"]

    repositorio.actualizar_rol(po["id"], lista_accion=[*po["acciones"], ACCION.HISTORIA_CREAR])
    assert ACCION.HISTORIA_CREAR in repositorio.obtener_usuario(ana["id"])["acciones"]

    repositorio.actualizar_usuario(ana["id"], lista_rol_id=[])
    assert repositorio.obtener_usuario(ana["id"])["acciones"] == []
    assert [u["usuario"] for u in repositorio.listar_usuario("mora")] == ["ana.mora"]

    with pytest.raises(SeguridadError):
        repositorio.crear_usuario("ana.mora", "Otra", "clave-otra-123", [])
    with pytest.raises(SeguridadError):
        repositorio.actualizar_rol(po["id"], lista_accion=["accion.inventada"])


def test_no_deja_el_sistema_sin_administrador(repositorio):
    admin_rol = _rol(repositorio, "Administrador")
    admin = repositorio.autenticar("admin", "clave-inicial-1")
    with pytest.raises(SeguridadError):
        repositorio.actualizar_usuario(admin["id"], lista_rol_id=[])
    with pytest.raises(SeguridadError):
        repositorio.actualizar_rol(admin_rol["id"], lista_accion=[ACCION.HISTORIA_VER])
    with pytest.raises(SeguridadError):
        repositorio.eliminar_rol(admin_rol["id"])
    assert set(repositorio.obtener_usuario(admin["id"])["acciones"]) == CODIGO_ACCION


def _app(repositorio) -> TestClient:
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(seguridad.router, prefix="/api/analista")
    app.include_router(historias.router, prefix="/api/analista")
    app.state.seguridad = repositorio
    app.state.firma_sesion = FirmaSesion("semilla-prueba")
    app.state.repositorio = SimpleNamespace(listar_historias=lambda: [])
    return TestClient(app)


def _entrar(cliente, usuario, clave):
    respuesta = cliente.post("/api/analista/sesion", json={"usuario": usuario, "clave": clave})
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['token']}"}


def test_api_pide_sesion_y_respeta_acciones(repositorio):
    cliente = _app(repositorio)
    assert cliente.get("/api/analista/sesion").json() == {"seguridad": True, "usuario": None}
    assert cliente.get("/api/analista/historias").status_code == 401
    assert cliente.post("/api/analista/sesion", json={"usuario": "admin", "clave": "mala"}).status_code == 401

    admin = _entrar(cliente, "admin", "clave-inicial-1")
    consulta = _rol(repositorio, "Consulta")
    creado = cliente.post("/api/analista/mantenimiento/usuarios", headers=admin, json={
        "usuario": "luis", "nombre": "Luis Vega", "clave": "clave-luis-1", "roles": [consulta["id"]]})
    assert creado.status_code == 201, creado.text

    luis = _entrar(cliente, "luis", "clave-luis-1")
    assert cliente.get("/api/analista/sesion", headers=luis).json()["usuario"]["nombre"] == "Luis Vega"
    assert cliente.get("/api/analista/historias", headers=luis).status_code == 200
    negado = cliente.get("/api/analista/mantenimiento/usuarios", headers=luis)
    assert negado.status_code == 403
    assert "Acceder a Mantenimiento" in negado.json()["error"]["message"]

    acciones = cliente.get("/api/analista/mantenimiento/acciones", headers=admin).json()
    assert {a["codigo"] for a in acciones} == CODIGO_ACCION

    desactivar = cliente.put(f"/api/analista/mantenimiento/usuarios/{creado.json()['id']}", headers=admin,
                             json={"activo": False})
    assert desactivar.status_code == 200
    assert cliente.get("/api/analista/historias", headers=luis).status_code == 401


def _decision(decision):
    return SimpleNamespace(kind="po_approval", response=SimpleNamespace(decision=decision))


def test_aprobar_devolver_y_rechazar_son_acciones_separadas():
    po = {"id": "po-1", "acciones": [ACCION.HISTORIA_APROBAR, ACCION.HISTORIA_DEVOLVER]}
    _exigir_permiso_respuesta(_decision(POApprovalDecision.APPROVE), po)
    _exigir_permiso_respuesta(_decision(POApprovalDecision.RETURN_TO_WRITER), po)
    with pytest.raises(WorkflowApiError) as rechazo:
        _exigir_permiso_respuesta(_decision(POApprovalDecision.REJECT), po)
    assert rechazo.value.status_code == 403
    assert "Rechazar historia" in rechazo.value.message
    with pytest.raises(WorkflowApiError):
        _exigir_permiso_respuesta(SimpleNamespace(kind="business_answers", response=None), po)


def test_toda_ruta_de_la_api_declara_su_accion():
    """Baranda: una ruta nueva sin requiere_accion, requiere_sesion o ruta_publica hace fallar esta prueba."""
    from agentes.analista.api.main import app

    sin_declarar = []
    for ruta in app.routes:
        if not isinstance(ruta, APIRoute) or not ruta.path.startswith("/api"):
            continue
        declaradas = [d.call for d in ruta.dependant.dependencies]
        if not any(hasattr(f, "acciones") or getattr(f, "publica", False) for f in declaradas):
            sin_declarar.append(f"{sorted(ruta.methods)} {ruta.path}")
    assert sin_declarar == [], f"Rutas sin acción declarada (ver agentes/seguridad/catalogo.py): {sin_declarar}"


def test_el_catalogo_del_frontend_es_el_mismo_del_backend():
    import re
    from pathlib import Path

    archivo = Path(__file__).resolve().parents[4] / "src" / "config" / "acciones.js"
    codigos = set(re.findall(r":\s*'([a-z_]+\.[a-z_]+)'", archivo.read_text(encoding="utf-8")))
    assert codigos == CODIGO_ACCION, "src/config/acciones.js debe tener los mismos códigos que agentes/seguridad/catalogo.py"
