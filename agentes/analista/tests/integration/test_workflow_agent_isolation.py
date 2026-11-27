from agentes.analista.core.agent_registry import AgentId, allowed_mcp_tools
from agentes.analista.core.workflow_graph import WorkflowRuntime
from agentes.analista.core.workflow_models import FlowMode, WorkflowCreateRequest


def test_checkpoints_route_each_flow_without_sharing_private_inputs():
    runtime = WorkflowRuntime()
    analyst = runtime.start(
        WorkflowCreateRequest(mode=FlowMode.PRE_GROOMING, requirement="Información del Analista")
    )
    change = runtime.start(
        WorkflowCreateRequest(
            mode=FlowMode.POST_GROOMING,
            approved_story_id="HU-314",
            change_request="Información del Gestor",
        )
    )

    analyst_checkpoint = runtime.get(analyst.workflow_id)
    change_checkpoint = runtime.get(change.workflow_id)
    assert analyst_checkpoint.active_agent == AgentId.ANALYST
    assert change_checkpoint.active_agent == AgentId.CHANGE_MANAGER
    assert "Información del Gestor" not in analyst_checkpoint.model_dump_json()
    assert "Información del Analista" not in change_checkpoint.model_dump_json()
    # Cada rol tiene su propio servidor MCP con su propio conjunto de herramientas; aunque compartan
    # un nombre (buscar_hu_similares), la recuperación filtra por rol (el Gestor solo ve HU aprobadas).
    from agentes.analista.core.ejecutor_mcp import servidor_del_rol
    from agentes.conocimiento.retrieval import _ROLE_ALLOWED_KINDS

    analyst_tools = allowed_mcp_tools(analyst_checkpoint.active_agent)
    change_tools = allowed_mcp_tools(change_checkpoint.active_agent)
    assert servidor_del_rol(analyst_checkpoint.active_agent) != servidor_del_rol(change_checkpoint.active_agent)
    assert "consultar_lecciones" not in analyst_tools and "consultar_glosario" not in change_tools
    assert _ROLE_ALLOWED_KINDS[change_checkpoint.active_agent]["hu_aprobadas"] == frozenset({"approved_history"})
