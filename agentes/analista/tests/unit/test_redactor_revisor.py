from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from agentes.equipo.redactor_revisor import redactor_revisor_service as redactor_revisor
from agentes.analista.core.agent_registry import AgentId
from agentes.analista.core.workflow_models import (
    BusinessAnswerSubmission,
    DraftStory,
    StoryDraftContent,
    StoryReviewOutput,
)


def test_story_contracts_reject_approval_and_invalid_gherkin():
    with pytest.raises(ValidationError):
        StoryDraftContent.model_validate({
            "como": "persona usuaria", "quiero": "consultar", "para": "conocer",
            "criterios": [{"dado": "", "cuando": "consulto", "entonces": "veo"}],
        })
    with pytest.raises(ValidationError):
        DraftStory.model_validate({
            "como": "persona usuaria", "quiero": "consultar", "para": "conocer",
            "criterios": [{"dado": "una cuenta", "cuando": "consulto", "entonces": "veo"}],
            "approved": True,
        })
    with pytest.raises(ValidationError):
        StoryReviewOutput.model_validate({"requires_correction": False, "approved": True})


def test_business_answer_contract_rejects_duplicates_and_unbounded_payloads():
    with pytest.raises(ValidationError):
        BusinessAnswerSubmission.model_validate({"answers": [
            {"question_id": "Q1", "answer": "14 días"},
            {"question_id": "Q1", "answer": "15 días"},
        ]})
    with pytest.raises(ValidationError):
        BusinessAnswerSubmission.model_validate({"answers": [
            {"question_id": "Q1", "answer": "x" * 1001},
        ]})


@pytest.mark.asyncio
async def test_redactor_uses_simulated_opencode_and_langchain_pydantic_parsers(monkeypatch):
    draft_plan = (
        '{"razonamiento":"Reviso estándares de redacción y HU parecidas.","consultas":['
        '{"herramienta":"consultar_estandares","consulta":"criterios de aceptación"},'
        '{"herramienta":"buscar_hu_similares","consulta":"consultar saldo"},'
        '{"herramienta":"leer_archivo_codigo","consulta":"modelos.py"}]}'
    )
    outputs = [
        draft_plan,
        "Aquí está la historia: como persona usuaria quiero consultar el saldo.",
        '{"como":"persona usuaria","quiero":"consultar saldo","para":"conocer el disponible",'
        '"criterios":[{"dado":"una cuenta activa","cuando":"consulto el saldo",'
        '"entonces":"veo el disponible"}]}',
        "sin plan válido",
        '{"requires_correction":false,"observations":[]}',
    ]
    calls = []

    class FakeOpenCodeClient:
        def __init__(self, *, prompt, agent_id):
            assert agent_id == AgentId.WRITER_REVIEWER
            assert "Redactor" in prompt.text
            self.settings = SimpleNamespace(turn_timeout_seconds=30)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def set_deadline(self, _deadline):
            pass

        async def server_info(self):
            return {"version": "2.0.27"}

        async def verify_agent(self, agent):
            assert agent == AgentId.WRITER_REVIEWER
            return {"id": "redactor_revisor"}

        async def select_model(self, _agent):
            return {"providerID": "opencode", "id": "fake-model"}

        @asynccontextmanager
        async def session(self, *, title, model):
            assert title.startswith("Redactor-Revisor")
            assert model["id"] == "fake-model"
            yield {"id": "session-test"}

        async def submit_prompt(self, _session_id, prompt):
            calls.append(prompt)
            return {"time": {"created": len(calls)}}

        async def wait_for_assistant(self, _session_id, *, deadline, after=None):
            assert deadline > 0
            return {"text": outputs.pop(0), "finish": "stop"}

    monkeypatch.setattr(redactor_revisor, "OpenCodeClient", FakeOpenCodeClient)
    service = redactor_revisor.RedactorRevisorService()
    draft = await service.draft(
        requirement="Consultar saldos de cuentas activas.",
        analyst_response={"analisis": {"conocida": ["Cuenta activa"]}},
    )
    review = await service.review(
        requirement="Consultar saldos de cuentas activas.",
        analyst_response={"analisis": {"conocida": ["Cuenta activa"]}},
        story=draft.model_dump(mode="json"),
    )

    assert draft.como == "persona usuaria"
    assert draft.criterios[0].dado == "una cuenta activa"
    assert review.requires_correction is False
    # Ronda de draft: plan del modelo → consultas MCP del Redactor → redacción con la evidencia.
    assert "FASE DE PLANIFICACIÓN" in calls[0]
    assert "consultar_glosario" not in calls[0]  # el Redactor no ve herramientas ajenas
    assert "format_instructions" not in calls[1]
    assert '"requerimiento"' in calls[1]
    assert '"herramienta":"consultar_estandares"' not in calls[1]
    assert '"nombre":"consultar_estandares"' in calls[1]
    assert '"nombre":"buscar_hu_similares"' in calls[1]
    assert "herramientas no permitidas" in calls[1]  # leer_archivo_codigo se descartó
    # La primera redacción no era JSON: se pidió una corrección en la misma sesión.
    assert "no cumplió el formato" in calls[2]
    # Ronda de review: plan inválido → plan predeterminado del backend, con constancia.
    assert "no entregó un plan válido" in calls[4]
    assert len(calls) == 5
