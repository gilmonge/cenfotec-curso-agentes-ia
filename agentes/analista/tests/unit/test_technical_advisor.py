from __future__ import annotations

import json
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from agentes.analista.core.agent_registry import AgentId, KnowledgeNamespace
from agentes.analista.core.workflow_models import TechnicalAssessment


def test_demo_policy_application_is_allowlisted_and_read_as_static_text():
    expected = {
        "ejemplos/polizas_demo/modelos.py",
        "ejemplos/polizas_demo/servicios/primas.py",
        "ejemplos/polizas_demo/servicios/renovaciones.py",
        "ejemplos/polizas_demo/mapa_dependencias.md",
    }
    worker = """
import json, sys
from agentes.analista.mcp.technical_tools import consultar_codigo_demo
before = {name for name in sys.modules if name.startswith('ejemplos.polizas_demo')}
result = consultar_codigo_demo('póliza prima renovación pago cobertura', 12)
after = {name for name in sys.modules if name.startswith('ejemplos.polizas_demo')}
assert not after - before
assert all(source.contenido_no_confiable and source.contenido.strip() for source in result.fuentes)
assert consultar_codigo_demo('código que no existe', 12).fuentes == []
print(json.dumps(sorted(source.source_ref for source in result.fuentes)))
"""
    root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        [sys.executable, "-c", worker], cwd=root, check=True, capture_output=True, text=True, timeout=30
    )

    refs = set(json.loads(result.stdout))
    assert expected <= refs
    assert all(ref.startswith("ejemplos/polizas_demo/") and ref.endswith((".py", ".md")) for ref in refs)


def test_code_tool_has_no_user_supplied_path_and_advisor_role_is_read_only():
    from pydantic import ValidationError

    from agentes.analista.core.agent_registry import authorize_mcp_tool
    from agentes.analista.mcp.technical_tools import CodeSearchRequest

    with pytest.raises(ValidationError):
        CodeSearchRequest.model_validate({"consulta": "póliza", "ruta": "../../secret.txt"})
    assert authorize_mcp_tool(AgentId.TECHNICAL_ADVISOR, "consultar_codigo_demo", KnowledgeNamespace.CODE)
    with pytest.raises(PermissionError):
        authorize_mcp_tool(AgentId.ANALYST, "consultar_codigo_demo", KnowledgeNamespace.CODE)


class _FakeAdvisorOpenCode:
    """OpenCode simulado: devuelve en orden los textos de la cola (planes y evaluación final)."""

    queue: list[str] = []
    prompts: list[str] = []

    def __init__(self, *, prompt, agent_id):
        assert agent_id == AgentId.TECHNICAL_ADVISOR
        assert "Asesor Técnico" in prompt.text
        self.settings = SimpleNamespace(turn_timeout_seconds=10)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def set_deadline(self, _deadline):
        pass

    async def server_info(self):
        return {"version": "2.0.27"}

    async def verify_agent(self, agent):
        assert agent == AgentId.TECHNICAL_ADVISOR
        return {"id": agent.value}

    async def select_model(self, _agent):
        return {"providerID": "mock", "id": "mock-model"}

    @asynccontextmanager
    async def session(self, *, title, model):
        assert title.startswith("Asesor Técnico")
        yield {"id": "mock-session"}

    async def submit_prompt(self, _session_id, prompt):
        type(self).prompts.append(prompt)
        return {"time": {"created": len(type(self).prompts)}}

    async def wait_for_assistant(self, _session_id, *, deadline, after=None):
        return {"text": type(self).queue.pop(0), "finish": "stop"}


def _advisor_adapter(results, calls):
    class Tool:
        def __init__(self, name):
            self.name = name
            self.description = name
            self.args = {"leer_archivo_codigo": {"ruta": {}}, "buscar_referencias_codigo": {"termino": {}}}.get(
                name, {"consulta": {}, "limite": {}}
            )

        async def ainvoke(self, arguments):
            calls.append((self.name, arguments))
            return results[self.name]

    class Adapter:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def list_tools(self):
            return [Tool(name) for name in sorted(results)]

    return Adapter()


@pytest.mark.asyncio
async def test_advisor_plans_searches_repository_opens_a_file_and_cites_only_consulted_sources(monkeypatch):
    from agentes.analista.core import ejecutor_mcp
    from agentes.equipo.asesor_tecnico import asesor_tecnico_service as technical_advisor

    calls = []
    results = {
        "consultar_codigo_demo": {"fuentes": [{
            "source_id": "ejemplos/polizas_demo/servicios/primas.py",
            "source_ref": "ejemplos/polizas_demo/servicios/primas.py",
            "contenido": "def calcular_prima(): ...",
            "contenido_no_confiable": True,
        }], "total": 1, "origen": "simulado"},
        "consultar_estandares": {"estandares": [{
            "id": "STD-REF-001", "titulo": "Validaciones",
            "regla": "Validar el dato y su mensaje.", "referencia": "Estándar ficticio v1",
        }], "total": 1, "origen": "simulado", "contenido_no_confiable": True},
        "leer_archivo_codigo": {"encontrado": True, "archivo": {
            "source_id": "ejemplos/polizas_demo/mapa_dependencias.md",
            "source_ref": "ejemplos/polizas_demo/mapa_dependencias.md",
            "contenido": "primas afecta alta y renovación", "contenido_no_confiable": True,
        }},
        "buscar_hu_similares": {"historias": [], "total": 0, "origen": "simulado", "contenido_no_confiable": True},
        "buscar_referencias_codigo": {"termino": "prima", "coincidencias": [
            {"source_id": "ejemplos/polizas_demo/servicios/renovaciones.py",
             "source_ref": "ejemplos/polizas_demo/servicios/renovaciones.py", "linea": 3,
             "texto": "from ejemplos.polizas_demo.servicios.primas import calcular_prima", "contenido_no_confiable": True},
        ], "total": 1, "archivos": ["ejemplos/polizas_demo/servicios/renovaciones.py"]},
    }
    output = {
        "affected_modules": [{
            "source_id": "ejemplos/polizas_demo/servicios/primas.py",
            "source_ref": "ejemplos/polizas_demo/servicios/primas.py",
            "evidence": "El módulo calcula la prima base y aplica factores ficticios.",
        }],
        "dependencies": [{
            "source_id": "estandares:STD-REF-001",
            "source_ref": "agentes/analista/fuentes/estandares.json",
            "evidence": "El estándar consultado requiere validar los datos.",
        }],
        "risks": [{
            "source_id": "ejemplos/polizas_demo/mapa_dependencias.md",
            "source_ref": "ejemplos/polizas_demo/mapa_dependencias.md",
            "evidence": "Un cambio de prima afecta alta y renovación.",
        }],
        "critical_processes": [{
            "source_id": "ejemplos/polizas_demo/servicios/renovaciones.py",
            "source_ref": "ejemplos/polizas_demo/servicios/renovaciones.py",
            "evidence": "La renovación reutiliza el cálculo de prima.",
        }],
        "uncertainties": [],
    }
    _FakeAdvisorOpenCode.prompts = []
    _FakeAdvisorOpenCode.queue = [
        json.dumps({"razonamiento": "Busco el cálculo de prima y las reglas.", "consultas": [
            {"herramienta": "consultar_codigo_demo", "consulta": "cálculo de prima"},
            {"herramienta": "consultar_estandares", "consulta": "validaciones"},
        ]}),
        json.dumps({"razonamiento": "Busco otros lugares que usan la prima.", "consultas": [
            {"herramienta": "buscar_referencias_codigo", "consulta": "prima"},
        ]}),
        json.dumps({"razonamiento": "Confirmo dependencias en el mapa.", "consultas": [
            {"herramienta": "leer_archivo_codigo", "consulta": "mapa_dependencias.md"},
        ]}),
        json.dumps(output, ensure_ascii=False),
    ]
    monkeypatch.setattr(ejecutor_mcp, "MCPAdapter", lambda _server: _advisor_adapter(results, calls))
    monkeypatch.setattr(technical_advisor, "OpenCodeClient", _FakeAdvisorOpenCode)

    assessment = await technical_advisor.AsesorTecnicoService().assess(
        requirement="Ajustar el cálculo de prima de póliza.", story={"quiero": "calcular prima"}
    )

    assert assessment.affected_modules[0].source_ref == "ejemplos/polizas_demo/servicios/primas.py"
    assert assessment.dependencies[0].source_ref == "agentes/analista/fuentes/estandares.json"
    assert {item.source_ref for item in assessment.consulted_sources} == {
        "ejemplos/polizas_demo/servicios/primas.py",
        "ejemplos/polizas_demo/servicios/renovaciones.py",
        "ejemplos/polizas_demo/mapa_dependencias.md",
        "agentes/analista/fuentes/estandares.json",
    }
    assert [name for name, _ in calls] == [
        "consultar_codigo_demo", "consultar_estandares", "buscar_referencias_codigo", "leer_archivo_codigo",
    ]
    assert calls[2][1] == {"termino": "prima"}
    assert calls[-1][1] == {"ruta": "mapa_dependencias.md"}
    prompts = _FakeAdvisorOpenCode.prompts
    assert "ronda 1 de 3" in prompts[0] and "ronda 3 de 3" in prompts[2]
    assert "primas.py" in prompts[1]  # la segunda ronda ve los resultados de la primera
    assert "línea 3" in prompts[3] and "mapa_dependencias.md" in prompts[3]


@pytest.mark.asyncio
async def test_no_evidence_is_reported_as_uncertainty_without_claims(monkeypatch):
    from agentes.analista.core import ejecutor_mcp
    from agentes.equipo.asesor_tecnico import asesor_tecnico_service as technical_advisor

    results = {
        "consultar_codigo_demo": {"fuentes": [], "total": 0, "origen": "simulado"},
        "consultar_estandares": {"estandares": [], "total": 0, "origen": "simulado", "contenido_no_confiable": True},
        "leer_archivo_codigo": {"encontrado": False, "motivo": "no existe"},
        "buscar_referencias_codigo": {"termino": "x", "coincidencias": [], "total": 0, "archivos": []},
        "buscar_hu_similares": {"historias": [], "total": 0, "origen": "simulado", "contenido_no_confiable": True},
    }
    _FakeAdvisorOpenCode.prompts = []
    _FakeAdvisorOpenCode.queue = [
        "no es JSON",  # plan inválido → plan predeterminado (búsquedas del rol)
        json.dumps({"razonamiento": "Sin evidencia adicional.", "consultas": []}),
        json.dumps({"affected_modules": [], "risks": [], "critical_processes": [], "dependencies": [], "uncertainties": []}),
    ]
    calls = []
    monkeypatch.setattr(ejecutor_mcp, "MCPAdapter", lambda _server: _advisor_adapter(results, calls))
    monkeypatch.setattr(technical_advisor, "OpenCodeClient", _FakeAdvisorOpenCode)

    result = await technical_advisor.AsesorTecnicoService().assess(
        requirement="Consultar un módulo sin coincidencias.", story={}
    )

    assert not result.affected_modules
    assert not result.risks
    assert not result.critical_processes
    assert not result.consulted_sources
    assert result.uncertainties
    # El plan predeterminado usa solo herramientas de búsqueda (no abre archivos sin ruta).
    assert {name for name, _ in calls} == {"consultar_codigo_demo", "consultar_estandares", "buscar_hu_similares"}


@pytest.mark.asyncio
async def test_advisor_as_collaborator_runs_a_single_round(monkeypatch):
    from agentes.analista.core import ejecutor_mcp
    from agentes.equipo.asesor_tecnico import asesor_tecnico_service as technical_advisor

    results = {
        "consultar_codigo_demo": {"fuentes": [], "total": 0, "origen": "simulado"},
        "consultar_estandares": {"estandares": [], "total": 0, "origen": "simulado", "contenido_no_confiable": True},
        "leer_archivo_codigo": {"encontrado": False},
        "buscar_referencias_codigo": {"termino": "x", "coincidencias": [], "total": 0, "archivos": []},
        "buscar_hu_similares": {"historias": [], "total": 0, "origen": "simulado", "contenido_no_confiable": True},
    }
    _FakeAdvisorOpenCode.prompts = []
    _FakeAdvisorOpenCode.queue = [
        json.dumps({"consultas": [{"herramienta": "consultar_codigo_demo", "consulta": "pago"}]}),
        json.dumps({"affected_modules": [], "risks": [], "critical_processes": [], "dependencies": [], "uncertainties": ["Sin evidencia."]}),
    ]
    monkeypatch.setattr(ejecutor_mcp, "MCPAdapter", lambda _server: _advisor_adapter(results, []))
    monkeypatch.setattr(technical_advisor, "OpenCodeClient", _FakeAdvisorOpenCode)

    evaluacion = await technical_advisor.AsesorTecnicoService().consultar("¿Afecta el pago?", "contexto del Gestor")

    assert evaluacion["uncertainties"] == ["Sin evidencia."]
    assert "ronda 1 de 1" in _FakeAdvisorOpenCode.prompts[0]
    assert len(_FakeAdvisorOpenCode.prompts) == 2


@pytest.mark.asyncio
async def test_advisor_discards_model_citations_not_returned_by_mcp(monkeypatch):
    from agentes.equipo.asesor_tecnico import asesor_tecnico_service as technical_advisor

    class EmptyProvider:
        async def __call__(self, _query):
            return [], []

    class FakeOpenCode:
        def __init__(self, *, prompt, agent_id):
            self.settings = SimpleNamespace(turn_timeout_seconds=10)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def set_deadline(self, _deadline):
            pass

        async def server_info(self):
            return {"version": "2.0.27"}

        async def verify_agent(self, _agent):
            return {"id": "asesor_tecnico"}

        async def select_model(self, _agent):
            return {"id": "mock"}

        @asynccontextmanager
        async def session(self, *, title, model):
            yield {"id": "mock"}

        async def submit_prompt(self, *_args):
            return {"time": {"created": 1}}

        async def wait_for_assistant(self, *_args, **_kwargs):
            return {"text": json.dumps({
                "affected_modules": [{
                    "source_id": "inventado.py", "source_ref": "inventado.py", "evidence": "inventado",
                }], "dependencies": [], "risks": [], "critical_processes": [], "uncertainties": [],
            }), "finish": "stop"}

    monkeypatch.setattr(technical_advisor, "OpenCodeClient", FakeOpenCode)
    advisor = technical_advisor.AsesorTecnicoService(source_provider=EmptyProvider())

    assessment = await advisor.assess(requirement="consulta", story={})

    # Una cita inventada nunca llega al PO: se descarta y queda registrada como incertidumbre.
    assert assessment.affected_modules == []
    assert any("Se descartaron 1 hallazgos" in item for item in assessment.uncertainties)


def test_advisor_corrects_a_miscopied_id_of_a_consulted_source():
    from agentes.equipo.asesor_tecnico.asesor_tecnico_service import AsesorTecnicoService, _TechnicalAdviceDraft

    catalogo = {"ejemplos/polizas_demo/cargas/carga_cliente.py": {"source_ref": "ejemplos/polizas_demo/cargas/carga_cliente.py"}}
    draft = _TechnicalAdviceDraft.model_validate({"affected_modules": [{
        "source_id": "carga_cliente", "source_ref": "ejemplos/polizas_demo/cargas/carga_cliente.py",
        "evidence": "La columna TEL es obligatoria.",
    }]})

    AsesorTecnicoService._validate_citations(draft, catalogo)

    assert draft.affected_modules[0].source_id == "ejemplos/polizas_demo/cargas/carga_cliente.py"
    assert draft.uncertainties == []


@pytest.mark.asyncio
async def test_advisor_asks_once_for_a_correction_when_the_output_is_not_valid_json(monkeypatch):
    from agentes.equipo.asesor_tecnico import asesor_tecnico_service as technical_advisor

    class EmptyProvider:
        async def __call__(self, _query):
            return [], []

    respuesta = iter(["no es json", json.dumps({
        "affected_modules": [], "dependencies": [], "risks": [], "critical_processes": [],
        "uncertainties": ["Sin evidencia suficiente."],
    })])
    prompt = []

    class FakeOpenCode:
        def __init__(self, *, prompt, agent_id):
            self.settings = SimpleNamespace(turn_timeout_seconds=30)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def set_deadline(self, _deadline):
            pass

        async def server_info(self):
            return {"version": "2.0.27"}

        async def verify_agent(self, _agent):
            return {"id": "asesor_tecnico"}

        async def select_model(self, _agent):
            return {"id": "mock"}

        @asynccontextmanager
        async def session(self, *, title, model):
            yield {"id": "mock"}

        async def submit_prompt(self, _session, texto):
            prompt.append(texto)
            return {"time": {"created": 1}}

        async def wait_for_assistant(self, *_args, **_kwargs):
            return {"text": next(respuesta), "finish": "stop"}

    monkeypatch.setattr(technical_advisor, "OpenCodeClient", FakeOpenCode)
    advisor = technical_advisor.AsesorTecnicoService(source_provider=EmptyProvider())

    assessment = await advisor.assess(requirement="consulta", story={})

    assert assessment.uncertainties == ["Sin evidencia suficiente."]
    assert len(prompt) == 2 and "no cumplió el formato" in prompt[1]


def test_assessment_contract_forbids_scope_decisions():
    from pydantic import ValidationError

    assessment = TechnicalAssessment.model_validate({
        "affected_modules": [], "dependencies": [], "risks": [], "critical_processes": [],
        "consulted_sources": [], "uncertainties": ["Evidencia insuficiente."],
    })
    assert assessment.uncertainties == ["Evidencia insuficiente."]
    with pytest.raises(ValidationError):
        TechnicalAssessment.model_validate({
            "affected_modules": [], "dependencies": [], "risks": [], "critical_processes": [],
            "consulted_sources": [], "uncertainties": [], "approved_scope": True,
        })
    with pytest.raises(ValidationError):
        TechnicalAssessment.model_validate({
            "affected_modules": [{
                "source_id": "outside.py", "source_ref": "outside.py", "evidence": "No consultado.",
            }],
            "dependencies": [], "risks": [], "critical_processes": [],
            "consulted_sources": [], "uncertainties": [],
        })
