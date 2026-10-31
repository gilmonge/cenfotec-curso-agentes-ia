import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentes.analista.api.acceso import (
    AccesoBasico,
    ConfiguracionAccesoError,
    credenciales_desde_entorno,
)
from agentes.analista.api.estaticos import montar_frontend


def _basic(usuario: str, clave: str) -> dict[str, str]:
    token = base64.b64encode(f"{usuario}:{clave}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture()
def dist(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path.parent / "secreto.txt").write_text("no debe salir", encoding="utf-8")
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path))
    return tmp_path


def _app(con_acceso: bool) -> FastAPI:
    app = FastAPI()

    @app.get("/api/analista/ping")
    async def ping():
        return {"ok": True}

    if con_acceso:
        app.add_middleware(AccesoBasico, usuario="equipo", clave="clave-larga")
    assert montar_frontend(app) is True
    return app


def test_sin_credenciales_la_ruta_privada_responde_401(dist):
    cliente = TestClient(_app(True))
    respuesta = cliente.get("/api/analista/ping")
    assert respuesta.status_code == 401
    assert "Basic" in respuesta.headers["www-authenticate"]
    assert cliente.get("/", headers=_basic("equipo", "mala")).status_code == 401
    assert cliente.get("/", headers={"Authorization": "Basic %%%"}).status_code == 401


def test_con_credenciales_correctas_pasa_api_y_interfaz(dist):
    cliente = TestClient(_app(True))
    encabezado = _basic("equipo", "clave-larga")
    assert cliente.get("/api/analista/ping", headers=encabezado).json() == {"ok": True}
    assert "app" in cliente.get("/", headers=encabezado).text
    assert cliente.get("/assets/app.js", headers=encabezado).status_code == 200


def test_healthz_no_pide_credenciales(dist):
    cliente = TestClient(_app(True))
    assert cliente.get("/healthz").json() == {"estado": "ok"}


def test_rutas_de_react_vuelven_a_la_pagina_principal_y_api_desconocida_da_404(dist):
    cliente = TestClient(_app(False))
    assert "app" in cliente.get("/historias/nueva").text
    assert cliente.get("/api/analista/no-existe").status_code == 404


def test_no_permite_salir_de_la_carpeta_compilada(dist):
    cliente = TestClient(_app(False))
    respuesta = cliente.get("/..%2Fsecreto.txt")
    assert "no debe salir" not in respuesta.text


def test_sin_carpeta_compilada_no_monta_nada(tmp_path, monkeypatch):
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path / "vacia"))
    assert montar_frontend(FastAPI()) is False


def test_credenciales_desde_entorno(monkeypatch):
    for nombre in ("ACCESO_USUARIO", "ACCESO_CLAVE", "ANALISTA_PUBLICO"):
        monkeypatch.delenv(nombre, raising=False)
    assert credenciales_desde_entorno() is None

    monkeypatch.setenv("ANALISTA_PUBLICO", "1")
    with pytest.raises(ConfiguracionAccesoError):
        credenciales_desde_entorno()

    monkeypatch.setenv("ACCESO_USUARIO", "equipo")
    monkeypatch.setenv("ACCESO_CLAVE", "clave-larga")
    assert credenciales_desde_entorno() == ("equipo", "clave-larga")
