import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentes.analista.api.acceso import ConfiguracionAccesoError, credenciales_desde_entorno
from agentes.analista.api.estaticos import montar_frontend


@pytest.fixture()
def dist(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path.parent / "secreto.txt").write_text("no debe salir", encoding="utf-8")
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path))
    return tmp_path


def _app(_con_acceso: bool = False) -> FastAPI:
    app = FastAPI()

    @app.get("/api/analista/ping")
    async def ping():
        return {"ok": True}

    assert montar_frontend(app) is True
    return app


def test_healthz_responde(dist):
    cliente = TestClient(_app())
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
