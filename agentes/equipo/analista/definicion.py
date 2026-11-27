"""Agente Analista: descubre y aclara los vacíos del requerimiento con Negocio."""
from agentes.equipo.contrato import DefinicionAgente, PropiedadAgente

DEFINICION = DefinicionAgente(
    id="analista",
    constante="ANALYST",
    nombre="Agente Analista",
    orden=10,
    descripcion="Análisis de vacíos de requerimientos; conserva el contrato actual del Analista.",
    modo_opencode="primary",
    propiedad=PropiedadAgente(
        autonomia="Decide qué fuentes consultar y qué preguntar a Negocio.",
        razonamiento="Clasifica la información en conocida, faltante, supuesta y ambigua.",
        herramienta="Glosario, HU similares, estándares y checklist de vacíos por su servidor MCP.",
        memoria="Conversación del requerimiento, HU aprobadas y lecciones aprobadas.",
    ),
    herramienta={"consultar_glosario", "buscar_hu_similares", "consultar_estandares", "aplicar_checklist_vacios"},
    fuente={
        "glosario": {"simulated_fixture"},
        "estandares": {"simulated_fixture"},
        "checklist": {"simulated_fixture"},
        "hu_aprobadas": {"simulated_reference", "approved_history"},
        "lecciones": {"approved_lesson"},
    },
    maximo_ronda=1,
)
