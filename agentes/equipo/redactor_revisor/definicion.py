"""Agente Redactor-Revisor: redacta la HU con lo aclarado y la revisa antes del Product Owner."""
from agentes.equipo.contrato import DefinicionAgente, PropiedadAgente

DEFINICION = DefinicionAgente(
    id="redactor_revisor",
    constante="WRITER_REVIEWER",
    nombre="Redactor-Revisor",
    orden=30,
    descripcion="Redacción y revisión acotada de historias de usuario; nunca aprueba.",
    modo_opencode="subagent",
    propiedad=PropiedadAgente(
        autonomia="Decide qué estándares y HU similares consultar y si la historia requiere corrección.",
        razonamiento="Evalúa la historia contra los estándares y el checklist de calidad.",
        herramienta="Estándares, checklist y HU similares por su servidor MCP.",
        memoria="Análisis aclarado, historia anterior, observaciones de la ronda previa y Repositorio de HU.",
    ),
    herramienta={"consultar_estandares", "aplicar_checklist_vacios", "buscar_hu_similares"},
    fuente={
        "estandares": {"simulated_fixture"},
        "checklist": {"simulated_fixture"},
        "hu_aprobadas": {"simulated_reference", "approved_history"},
    },
    maximo_ronda=1,
)
