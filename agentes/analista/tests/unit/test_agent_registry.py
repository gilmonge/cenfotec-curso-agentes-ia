import json
from pathlib import Path

import pytest

from agentes.analista.core.agent_registry import (
    AgentId,
    AgentPermissionError,
    KnowledgeNamespace,
    authorize_mcp_tool,
    get_agent_spec,
)


@pytest.mark.parametrize("agent_id", list(AgentId))
def test_each_agent_has_an_individual_versioned_prompt(agent_id):
    spec = get_agent_spec(agent_id)
    assert spec.agent_id == agent_id
    assert spec.prompt_path.is_file()
    assert spec.prompt.version


def test_unknown_agent_is_rejected_without_fallback():
    with pytest.raises(ValueError, match="agente"):
        get_agent_spec("unknown-agent")


def test_opencode_config_registers_all_agents_with_external_prompts_and_deny_all():
    root = Path(__file__).resolve().parents[4]
    config = json.loads((root / "opencode.jsonc").read_text(encoding="utf-8"))
    assert set(config["agents"]) == {agent.value for agent in AgentId}
    for agent_id, spec in ((agent_id, get_agent_spec(agent_id)) for agent_id in AgentId):
        agent = config["agents"][agent_id.value]
        assert agent["system"].endswith(spec.prompt_path.name + "}")
        assert {"action": "*", "resource": "*", "effect": "deny"} in agent["permissions"]


@pytest.mark.parametrize(
    ("agent_id", "tool_name"),
    [
        (AgentId.ANALYST, "consultar_glosario"),
        (AgentId.ANALYST, "buscar_hu_similares"),
        (AgentId.WRITER_REVIEWER, "consultar_estandares"),
        (AgentId.WRITER_REVIEWER, "aplicar_checklist_vacios"),
        (AgentId.WRITER_REVIEWER, "buscar_hu_similares"),
        (AgentId.TECHNICAL_ADVISOR, "consultar_estandares"),
        (AgentId.TECHNICAL_ADVISOR, "leer_archivo_codigo"),
        (AgentId.TECHNICAL_ADVISOR, "buscar_hu_similares"),
        (AgentId.CHANGE_MANAGER, "buscar_hu_similares"),
        (AgentId.CHANGE_MANAGER, "consultar_lecciones"),
        (AgentId.CHANGE_MANAGER, "aplicar_checklist_vacios"),
    ],
)
def test_backend_allows_only_read_only_tools_assigned_to_role(agent_id, tool_name):
    assert authorize_mcp_tool(agent_id, tool_name)


@pytest.mark.parametrize(
    ("agent_id", "tool_name"),
    [
        (AgentId.TECHNICAL_ADVISOR, "consultar_glosario"),
        (AgentId.WRITER_REVIEWER, "leer_archivo_codigo"),
        (AgentId.ANALYST, "consultar_codigo_demo"),
        (AgentId.CHANGE_MANAGER, "consultar_glosario"),
        (AgentId.CHANGE_MANAGER, "consultar_codigo_demo"),
        (AgentId.ANALYST, "filesystem.read"),
        (AgentId.ANALYST, "shell"),
        ("unknown-agent", "consultar_estandares"),
    ],
)
def test_backend_denies_unassigned_and_unknown_tools(agent_id, tool_name):
    with pytest.raises(AgentPermissionError):
        authorize_mcp_tool(agent_id, tool_name)


def test_backend_rejects_namespace_outside_agent_allowlist():
    assert authorize_mcp_tool(AgentId.TECHNICAL_ADVISOR, "consultar_estandares", KnowledgeNamespace.STANDARDS)
    with pytest.raises(AgentPermissionError):
        authorize_mcp_tool(AgentId.TECHNICAL_ADVISOR, "consultar_estandares", KnowledgeNamespace.APPROVED_STORIES)
    assert authorize_mcp_tool(AgentId.ANALYST, "buscar_hu_similares", KnowledgeNamespace.APPROVED_STORIES)
    with pytest.raises(AgentPermissionError):
        authorize_mcp_tool(AgentId.ANALYST, "buscar_hu_similares", KnowledgeNamespace.GLOSSARY)
    with pytest.raises(AgentPermissionError):
        authorize_mcp_tool(AgentId.WRITER_REVIEWER, "consultar_estandares", KnowledgeNamespace.LESSONS)


def test_only_the_change_manager_can_consult_the_advisor():
    from agentes.analista.core.agent_registry import puede_consultar_asesor

    # En la creación de una HU el Asesor ya actúa en el grafo, después del Analista.
    assert not puede_consultar_asesor(AgentId.ANALYST)
    assert puede_consultar_asesor(AgentId.CHANGE_MANAGER)
    assert not puede_consultar_asesor(AgentId.TECHNICAL_ADVISOR)
    assert not puede_consultar_asesor("desconocido")
