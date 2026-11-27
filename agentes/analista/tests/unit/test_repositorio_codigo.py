"""El Asesor revisa un repositorio de código aparte, descargado en solo lectura."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from agentes.conocimiento import repositorio_codigo
from agentes.conocimiento.repositorio_codigo import (
    RAIZ_PREDETERMINADA,
    RAIZ_SINCRONIZADA,
    RepositorioCodigoError,
    es_ruta_codigo,
    origen_repositorio,
    raiz_codigo_relativa,
    sincronizar,
    sincronizar_desde_entorno,
)
from agentes.conocimiento.sources import AuthorizedSourceLoader

FIXTURE = Path(__file__).resolve().parents[4] / "ejemplos" / "polizas_demo"


def _proyecto(tmp_path: Path) -> Path:
    raiz = tmp_path / "proyecto"
    shutil.copytree(FIXTURE, raiz / RAIZ_PREDETERMINADA)
    return raiz


def _git_simulado(monkeypatch, origen: Path, *, falla: bool = False):
    """Simula git: el «clon» copia una carpeta e incluye archivos que deben depurarse."""
    llamada = []

    def ejecutar(argumento, *, cwd=None):
        llamada.append(argumento)
        if falla:
            raise RepositorioCodigoError("git no pudo descargar el repositorio (revise URL, rama y visibilidad).")
        if "clone" in argumento:
            destino = Path(argumento[-1])
            shutil.copytree(origen, destino)
            (destino / ".git").mkdir()
            (destino / ".git" / "config").write_text("[core]", encoding="utf-8")
            (destino / "secreto.env").write_text("TOKEN=x", encoding="utf-8")
            (destino / "binario.bin").write_bytes(b"\x00\x01")
            (destino / "enlace.py").symlink_to("/etc/passwd")
            (destino / "vacio.py").write_text("", encoding="utf-8")
            (destino / "solo_espacio.md").write_text("  \n", encoding="utf-8")
            return ""
        return "a" * 40

    monkeypatch.setattr(repositorio_codigo, "_ejecutar_git", ejecutar)
    return llamada


def test_without_configuration_the_advisor_uses_the_bundled_example(tmp_path, monkeypatch):
    raiz = _proyecto(tmp_path)
    monkeypatch.delenv("ASESOR_REPOSITORIO_URL", raising=False)

    resultado = sincronizar_desde_entorno(raiz)

    assert resultado.sincronizado is False
    assert raiz_codigo_relativa(raiz) == RAIZ_PREDETERMINADA
    assert origen_repositorio(raiz)["tipo"] == "ejemplo_incluido"


def test_sync_keeps_only_code_text_removes_history_and_records_origin(tmp_path, monkeypatch):
    raiz = _proyecto(tmp_path)
    llamada = _git_simulado(monkeypatch, FIXTURE)

    resultado = sincronizar("https://github.com/organizacion/codigo-ejemplo-polizas.git", "main", project_root=raiz)

    destino = raiz / RAIZ_SINCRONIZADA
    assert resultado.sincronizado and resultado.commit == "a" * 40
    assert raiz_codigo_relativa(raiz) == RAIZ_SINCRONIZADA
    assert not (destino / ".git").exists()
    assert not (destino / "secreto.env").exists() and not (destino / "binario.bin").exists()
    assert not (destino / "enlace.py").exists()
    assert not (destino / "vacio.py").exists() and not (destino / "solo_espacio.md").exists()
    assert (destino / "servicios" / "primas.py").is_file()
    marca = json.loads((destino / repositorio_codigo.MARCA_ORIGEN).read_text(encoding="utf-8"))
    assert marca["repositorio"] == "github.com/organizacion/codigo-ejemplo-polizas"
    assert "--depth" in llamada[0] and "core.symlinks=false" in llamada[0]
    # El cargador RAG y las citas usan la nueva raíz.
    registro = AuthorizedSourceLoader(raiz).load_demo_code()
    assert registro and all(item.source_ref.startswith(RAIZ_SINCRONIZADA + "/") for item in registro)
    assert es_ruta_codigo(f"{RAIZ_SINCRONIZADA}/servicios/primas.py", raiz)
    assert not es_ruta_codigo(f"{RAIZ_PREDETERMINADA}/servicios/primas.py", raiz)


def test_failed_sync_keeps_service_running_with_previous_code(tmp_path, monkeypatch):
    raiz = _proyecto(tmp_path)
    _git_simulado(monkeypatch, FIXTURE, falla=True)
    monkeypatch.setenv("ASESOR_REPOSITORIO_URL", "https://github.com/organizacion/codigo-ejemplo-polizas.git")

    resultado = sincronizar_desde_entorno(raiz)

    assert resultado.sincronizado is False
    assert "No se sincronizó" in resultado.detalle
    assert raiz_codigo_relativa(raiz) == RAIZ_PREDETERMINADA


@pytest.mark.parametrize("url", [
    "http://github.com/organizacion/repo.git",
    "https://usuario:token@github.com/organizacion/repo.git",
    "https://github.com/organizacion/repo.git?token=x",
    "file:///etc",
    "",
])
def test_unsafe_repository_urls_are_rejected(tmp_path, url):
    with pytest.raises(RepositorioCodigoError):
        sincronizar(url, "main", project_root=_proyecto(tmp_path))


@pytest.mark.parametrize("rama", ["--upload-pack=x", "../main", "rama con espacio", ""])
def test_unsafe_branch_names_are_rejected(tmp_path, rama):
    with pytest.raises(RepositorioCodigoError):
        sincronizar("https://github.com/organizacion/repo.git", rama, project_root=_proyecto(tmp_path))


@pytest.mark.parametrize("ruta", [
    "ejemplos/polizas_demo/../../agentes/analista/core/workflow_graph.py",
    "/ejemplos/polizas_demo/modelos.py",
    "ejemplos/polizas_demo/modelos.txt",
    "agentes/analista/core/workflow_graph.py",
    "C:\\ejemplos\\polizas_demo\\modelos.py",
])
def test_code_references_outside_the_repository_are_not_citable(ruta):
    assert not es_ruta_codigo(ruta)


def test_loader_skips_empty_code_files_instead_of_failing(tmp_path):
    raiz = _proyecto(tmp_path)
    (raiz / RAIZ_PREDETERMINADA / "vacio.py").write_text("", encoding="utf-8")

    registro = AuthorizedSourceLoader(raiz).load_demo_code()

    assert registro
    assert all(not item.source_ref.endswith("vacio.py") for item in registro)
