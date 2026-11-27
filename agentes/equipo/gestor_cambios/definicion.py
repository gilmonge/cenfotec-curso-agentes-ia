"""Agente Gestor de Cambios: compara una solicitud con la HU aprobada y recomienda; no decide."""
from agentes.equipo.contrato import DefinicionAgente, PropiedadAgente

DEFINICION = DefinicionAgente(
    id="gestor_cambios",
    constante="CHANGE_MANAGER",
    nombre="Gestor de Cambios",
    orden=40,
    descripcion="Clasificación y recomendación de cambios; nunca toma la decisión humana.",
    modo_opencode="subagent",
    propiedad=PropiedadAgente(
        autonomia="Decide qué consultar y si pide criterio técnico al Asesor.",
        razonamiento="Clasifica la solicitud como aclaración o cambio de alcance y busca la causa raíz.",
        herramienta="HU similares, lecciones y checklist por su servidor MCP, y consulta al Asesor Técnico.",
        memoria="HU aprobadas e historial de causas raíz (lecciones).",
    ),
    herramienta={"buscar_hu_similares", "consultar_lecciones", "aplicar_checklist_vacios"},
    fuente={
        "hu_aprobadas": {"approved_history"},
        "lecciones": {"approved_lesson"},
        "checklist": {"simulated_fixture"},
    },
    maximo_ronda=1,
    puede_consultar_asesor=True,
)
