"""Agente Asesor Técnico: encuentra todos los lugares del sistema que afecta un cambio."""
from agentes.equipo.contrato import DefinicionAgente, PropiedadAgente

DEFINICION = DefinicionAgente(
    id="asesor_tecnico",
    constante="TECHNICAL_ADVISOR",
    nombre="Asesor Técnico",
    orden=20,
    descripcion="Análisis técnico basado en evidencia recuperada de fuentes permitidas.",
    modo_opencode="subagent",
    propiedad=PropiedadAgente(
        autonomia="Decide qué buscar en el repositorio de código y qué archivos abrir (hasta tres rondas).",
        razonamiento="Identifica módulos, dependencias y riesgos, y los explica en lenguaje de negocio.",
        herramienta="Búsqueda en el código, lectura de archivos, estándares y HU similares por su servidor MCP.",
        memoria="Contexto de la HU consultada y Repositorio de HU.",
    ),
    herramienta={
        "consultar_estandares", "consultar_codigo_demo", "buscar_referencias_codigo",
        "leer_archivo_codigo", "buscar_hu_similares",
    },
    fuente={
        "estandares": {"simulated_fixture"},
        "codigo": {"simulated_code"},
        "hu_aprobadas": {"simulated_reference", "approved_history"},
    },
    maximo_ronda=3,
    # Herramientas propias del Asesor (código de solo lectura), además de las de conocimiento.
    herramienta_extra="agentes.analista.mcp.technical_tools:registrar_herramienta_codigo",
)
