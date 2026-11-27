"""Keep automated tests isolated from credentials stored in env or the local .env file."""
from __future__ import annotations

import pytest
import os

_EXTERNAL_CREDENTIALS = (
    "OPENCODE_API_KEY",
    "OPENCODE_SERVER_PASSWORD",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "PINECONE_API_KEY",
    "DATABASE_URL",
    "ANALISTA_REPO_DB",
)


def pytest_sessionstart(session):
    # Empty env vars take precedence over BaseSettings' local .env file.
    for name in _EXTERNAL_CREDENTIALS:
        os.environ[name] = ""
    # Las pruebas usan MCP en memoria (mismo protocolo, sin subprocesos); los contratos stdio
    # se prueban aparte en tests/contract. El repositorio del Asesor usa el ejemplo incluido.
    os.environ["ANALISTA_MCP_TRANSPORTE"] = "memoria"
    os.environ["ASESOR_REPOSITORIO_URL"] = ""


@pytest.fixture(autouse=True)
def _disable_external_service_credentials(monkeypatch):
    for name in _EXTERNAL_CREDENTIALS:
        monkeypatch.setenv(name, "")
    monkeypatch.setenv("ANALISTA_MCP_TRANSPORTE", "memoria")


@pytest.fixture(autouse=True)
def _restore_knowledge_retriever():
    """Una prueba puede instalar un recuperador detrás de los servidores MCP; se restaura siempre."""
    from agentes.conocimiento import retrieval

    previous = retrieval._default_retriever
    yield
    retrieval._default_retriever = previous
