# Arquitectura del proyecto

Este documento explica cómo está organizado el sistema y cómo se hace cada tipo de cambio sin romper la estructura. Lo leen las personas y también las herramientas de IA que trabajan en el repositorio (ver las skills en `.agents/skills` y `.claude/skills`).

## Principios

1. **Lo que cambia seguido se declara; el código genérico lo lee.** Agentes, pantallas e intervenciones humanas se agregan con una declaración en un registro, no editando código repartido en varios archivos.
2. **Una carpeta por agente.** Todo lo de un agente (definición, prompt, servidor MCP e implementación) vive junto.
3. **Capas con responsabilidades separadas.** Interfaz, orquestación, agentes, herramientas y datos no se mezclan.
4. **Contratos tipados.** Toda entrada y salida entre capas y agentes es un modelo Pydantic (backend) o un objeto validado (frontend). Un agente no puede devolver algo que no cumpla su contrato.
5. **Barandas automáticas.** Las pruebas de `agentes/analista/tests/unit/test_estructura_proyecto.py` verifican que la estructura se cumpla. Si fallan, se completa lo que falta; no se relajan.
6. **Mínimo privilegio.** Cada agente solo ve sus herramientas MCP y sus namespaces de conocimiento; ningún agente aprueba historias.

## Capas

```
Interfaz (React)            src/
  └─ registro de pantallas  src/config/rutas.jsx
  └─ intervenciones humanas src/flujo/interrupciones.jsx
        │ HTTP (FastAPI)
API                          agentes/analista/api/
        │
Orquestación (LangGraph)     agentes/analista/core/workflow_graph.py (flujo como tabla de pasos)
                             agentes/analista/core/flujo.py (arma y valida el grafo)
        │
Equipo de agentes            agentes/equipo/<agente>/
  └─ clase base              agentes/equipo/agente_opencode_service.py
        │ MCP (solo lectura)
Herramientas                 agentes/analista/mcp/
        │
Conocimiento y datos         agentes/conocimiento/ (RAG, Pinecone)
                             agentes/analista/memory/ (base de datos)
```

## Backend: el equipo de agentes

```
agentes/equipo/
  contrato.py                     DefinicionAgente: la declaración de un agente
  __init__.py                     descubre las carpetas del equipo (no se edita)
  agente_opencode_service.py      clase base con el ciclo OpenCode + MCP + corrección (Template Method)
  <agente>/
    definicion.py                 DEFINICION = DefinicionAgente(...)
    prompt.md                     instrucciones del agente, con «**Versión editorial:** X.Y.Z»
    servidor_mcp.py               igual en todas las carpetas; no se edita
    <agente>_service.py           implementación: clase <Nombre>Service
```

De la definición salen solos: el identificador `AgentId`, las herramientas MCP permitidas, los namespaces y tipos de fuente que puede leer, las rondas de consulta, si puede consultar al Asesor, su servidor MCP y la verificación de `opencode.jsonc`.

La clase base `AgenteOpenCodeService` hace el ciclo común: abre OpenCode, verifica versión y agente, planifica y consulta por MCP, envía el mensaje final, interpreta la salida y pide una corrección si no cumple el contrato. Cada servicio solo aporta su tarea, su contexto, cómo armar el mensaje y cómo interpretar la salida.

## Orquestación: el flujo como tabla

El grafo de LangGraph no se arma con llamadas sueltas: se declara como una lista de `Paso(nombre, nodo, siguiente, descripción)`, donde `siguiente` es un paso fijo, `FIN` o una `Ruta` que decide según el estado. `construir_flujo` (en `agentes/analista/core/flujo.py`) valida la tabla antes de compilar: pasos repetidos, destinos inexistentes o pasos a los que nunca se llega detienen el arranque con un mensaje claro.

**Analista y Asesor en equipo.** Después del primer análisis del Analista, el Asesor Técnico revisa el sistema (con los temas que el Analista le pasa en `para_asesor`) y sus decisiones se suman a las preguntas del Analista en una sola ronda para Negocio (`business_wait`). Lo que solo se sabe revisando el código nunca se le pregunta a Negocio.

## Frontend

```
src/
  config/rutas.jsx                registro único de pantallas: ruta + componente + menú
  flujo/interrupciones.jsx        tipo de intervención humana → formulario y respuesta
  components/HistoriaUsuario/crear/
    useCrearHistoria.js           controlador del asistente: estado, efectos y acciones
    AsistenteHistoriaContext.js   comparte el controlador con las vistas
    pasosAsistente.js             registro de pasos: indicador de pasos + vista de cada uno
    Paso<Nombre>Component.jsx     una vista por paso, sin estado propio del flujo
  components/<Funcionalidad>/     componentes por funcionalidad
  hooks/                          estado y lógica reutilizable
  services/                       llamadas a la API
  utils/                          lógica pura (sin React), probada por separado
  data/                           textos de la Ayuda
```

## Cómo se hace cada cambio

| Cambio | Qué se toca |
|---|---|
| Pantalla nueva | Su componente + una entrada en `src/config/rutas.jsx` (con `menu` si va en el menú). |
| Agente nuevo | Carpeta `agentes/equipo/<id>/` con sus cuatro archivos, entrada en `opencode.jsonc`, su `Paso` en la tabla del flujo (`workflow_graph.py`) y su descripción en la Ayuda. Si pide una decisión humana, una entrada en `src/flujo/interrupciones.jsx`. |
| Paso nuevo en el asistente | Su vista `Paso<Nombre>Component.jsx` en `crear/`, una entrada en `pasosAsistente.js` y su valor en `PASO`; la lógica va en `useCrearHistoria.js`. |
| Herramienta MCP para un agente existente | Agregarla a `herramienta` (y su namespace a `fuente`) en la definición del agente. |
| Cambiar lo que dice un agente | Su `prompt.md`, subiendo la versión editorial. |
| Acción nueva (permiso) | Una línea en `agentes/seguridad/catalogo.py` (código, nombre y módulo) y su código en `src/config/acciones.js`; la ruta de la API declara `requiere_accion(ACCION.X)` y la pantalla o el botón lleva `accion`. Aparece sola en Mantenimiento. |
| Regla de negocio de un paso | El modelo Pydantic del contrato y el nodo del grafo; nunca en el prompt solamente. |

Las listas paso a paso están en las skills `agregar-agente` y `agregar-ruta`.

## Pensado para producción

- **Persistencia y reanudación:** cada pausa del flujo guarda un punto de control en la base de datos; se puede retomar otro día o tras un reinicio del servidor.
- **Observabilidad:** trazas por turno y por etapa (Langfuse) y registros estructurados sin contenido del modelo ni datos personales.
- **Seguridad:** inicio de sesión por usuario; usuarios con roles y roles con acciones (pestaña Mantenimiento), validados en cada ruta de la API; agentes sin permisos en OpenCode, herramientas MCP de solo lectura por rol, entradas tratadas como no confiables y aprobación siempre humana.
- **Configuración por entorno:** claves y URLs por variables de entorno; despliegue en contenedor (ver `DESPLIEGUE.md`).
- **Diseño:** marca «Ciruela corporativa» documentada en `docs/marca.md`; colores solo como variables de tema, dos familias tipográficas y una estructura que se adapta a web, tablet y móvil. Pruebas de estructura la protegen.
- **Calidad:** pruebas de backend, frontend y extremo a extremo en la integración continua, más las pruebas de estructura.

## Convenciones

- Nombres en español y en singular (`listaAgente`, no `agentes`).
- Las clases de servicio terminan en `Service` (archivo y clase).
- Ningún `catch`/`except` vacío: al menos se registra un log.
- Confirmaciones con el modal de la aplicación (`useConfirmacion`), nunca con los cuadros nativos del navegador.
- El backend nunca registra el contenido que genera el modelo; solo el tipo de error.
