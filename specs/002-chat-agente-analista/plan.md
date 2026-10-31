# Implementation Plan: Chat flotante con Agente Analista de Requerimientos

**Branch**: `feat/chat-agente-analista` | **Date**: 2026-10-26 | **Spec**: [spec.md](./spec.md)

**Input**: Especificación completada con Clarify en `specs/002-chat-agente-analista/spec.md` y Constitución v1.0.0 en `.specify/memory/constitution.md`. La especificación conserva `Status: Draft`; este plan no cambia ese estado.

**Estado**: plan aprobado para implementación incremental; T001–T008 tienen implementación/evidencia en curso y la aceptación final sigue pendiente.

**Artefactos de investigación**:

- [research.md](./research.md) — decisiones, APIs verificadas, versiones y alternativas.
- [data-model.md](./data-model.md) — entidades, estados, invariantes, concurrencia y datos PEAS.
- [contracts/rest-api.yaml](./contracts/rest-api.yaml) — contrato REST.
- [contracts/mcp-tools.yaml](./contracts/mcp-tools.yaml) — contrato de las cuatro herramientas MCP.
- [contracts/opencode-v2.md](./contracts/opencode-v2.md) — contrato verificado con OpenCode 2.0.27 (API v2).
- [quickstart.md](./quickstart.md) — instalación y ejecución en Windows PowerShell.

## Summary

Se añadirá un chat flotante global a Historias de Usuario sin sustituir ninguna pantalla, ruta, simulación o estilo existente. El botón se monta una sola vez en `EnvolturaPaginaComponent`; el panel conserva su historial al cerrarse, **Nuevo chat** limpia el contexto y mantiene el panel abierto, **Eliminar** confirma, borra el contexto y cierra el panel, y **Cancelar** aborta solo el turno activo conservando el historial y el contexto anteriores. Recargar la página inicia un chat vacío: no hay recuperación desde el navegador.

El chat usa una cadena real React → `/api/analista` → FastAPI → LangChain/MCP → OpenCode Server v2 → provider/model configurados, con cuatro herramientas MCP de solo lectura ejecutadas por el backend. El provider predeterminado es `opencode`; `OPENCODE_PROVIDER_ID` y `OPENCODE_MODEL_ID` permiten elegir explícitamente otra combinación que OpenCode anuncie y habilite. FastAPI no conecta directamente a proveedores de IA.

La cancelación, el timeout total de 90 s, el reinicio y la eliminación invalidan por identidad y generación antes de abortar. El backend no incorpora al contexto un turno cancelado, expirado, fallido o descartado; el frontend además ignora respuestas tardías por `requestEpoch` y `request_id`. Langfuse v5 recibe trazas correlacionadas y enmascaradas; si no está disponible, el chat sigue funcionando y el health/UI muestran diagnóstico degradado.

La implementación incluye pruebas focalizadas de API, concurrencia, reset/cancelación, Markdown seguro y flujo del agente, además de la prueba manual end-to-end. Las cinco métricas PEAS son criterios de aceptación obligatorios según Clarify; sus resultados siguen sin medirse. Una evaluación `NOT_MEASURED` o `PARTIAL` es transparente, pero no satisface la puerta de aceptación. La muestra inicial será de 3–5 requerimientos según Clarify; SC-005 conserva el requisito explícito de 10 y solo podrá declararse cumplido con N ≥ 10.

### Trazabilidad de las cinco decisiones de Clarify

| Decisión | Diseño que la implementa |
|---|---|
| **Nuevo chat vs. Eliminar** | Nuevo chat invalida y reemplaza la conversación, limpia el historial visible y mantiene el panel abierto. Eliminar confirma, borra el contexto en el backend y cierra el panel. |
| **Cancelar durante un turno** | Cancela solo el turno activo, lo excluye del contexto y conserva el historial/contexto anterior. |
| **Recarga de página** | Inicia conversación vacía; no persiste mensajes ni identificadores en almacenamiento del navegador. |
| **Timeout de 90 s** | Deadline total y configurable por mensaje; al vencer, el backend invalida y aborta y descarta cualquier resultado posterior. |
| **Cinco métricas PEAS** | Umbrales obligatorios: vacíos ≥80 %, preguntas útiles ≥70 %, tiempo −50 %, satisfacción ≥4/5 y cero invenciones. Se reportan solo con evidencia; SC-005 requiere N=10 aunque la muestra inicial aclarada sea 3–5. |

## Technical Context

**Language/Version**: Python `3.12.10` verificado localmente; JavaScript ES2022 + JSX; SCSS; sin TypeScript.

**Primary Dependencies**:
- Backend: FastAPI `0.162.0`, Uvicorn `0.54.0`, httpx `0.28.1`, Pydantic `2.14.1`, pydantic-settings `2.16.1`, LangChain `1.4.7`, FastMCP `4.1.4`, MCP `2.3.0`, Langfuse `5.0.4`.
- Frontend de producción: React 18.2, Vite 5.1.6, React Router 6.22, `lucide-react`, `react-markdown@10.1.0`, `remark-gfm@4.0.1`. No se instala `rehype-raw`.
- Pruebas: pytest `9.1.1`, pytest-asyncio `1.4.1`, Vitest `3.2.7`, jsdom `26.1.0`, React Testing Library `16.3.3`, user-event `14.6.8`, jest-dom `6.9.1`, `@testing-library/dom` `10.4.2`.

**Storage**: Estado de conversaciones en memoria del proceso (sin base de datos); fuentes ficticias/anonimizadas en JSON bajo `agentes/analista/fuentes/`; sin persistencia del chat en el navegador. TTL inicial 30 min y tope de 32 conversaciones.

**Testing**: pytest + pytest-asyncio con `httpx.MockTransport` para el cliente OpenCode; Vitest + jsdom + RTL para UI, estados, accesibilidad y XSS; prueba manual end-to-end con OpenCode, MCP y Langfuse reales; evaluación PEAS separada con corpus y evaluadores humanos.

**Target Platform**: Windows 10/11 con PowerShell 5.1 o 7; servicios en `127.0.0.1`; navegadores actuales; una sola instancia local, sin multiusuario.

**Project Type**: Aplicación web existente + servicio Python local + servidor MCP por stdio. Funcionalidad aditiva.

**Performance Goals**:
- El botón debe estar disponible en todas las rutas y el panel abrir en menos de 0,5 s (SC-001).
- El indicador de procesamiento debe aparecer en menos de 2 s (SC-003) y nunca quedar indefinido.
- El deadline total por mensaje es 90 s configurables; incluye MCP, OpenCode, parseo y reparación (FR-032).
- El cierre de cancelación/eliminación y la liberación de la conversación deben ser inmediatos desde la UI, sin esperar al modelo.
- Estas son metas de diseño; no se reportan como medidas hasta ejecutar la evaluación correspondiente.

**Constraints**:
- No TypeScript, Bootstrap, Material UI, Tailwind, Chakra, Ant Design, Redux, MobX, Zustand ni otro framework/gestor de estado.
- No `rehype-raw`; no HTML crudo; no imágenes remotas; enlaces saneados.
- Una sola solicitud en vuelo por conversación; sin cola; sin respuestas simuladas.
- Mensaje inicial máximo 4.000 caracteres; cuatro herramientas MCP como máximo.
- Sin secretos en navegador, bundle, URLs, almacenamiento, logs, respuestas ni trazas.
- Sin CORS abierto; sin `0.0.0.0`; sin contacto del navegador con OpenCode/Langfuse.
- Sin persistencia de chat en el navegador; recarga inicia vacío.
- No se modifican pantallas, rutas, Stepper, Accordion, datos mock ni simulaciones existentes.
- La rama de trabajo es `feat/chat-agente-analista`; no se escribe en `main`.

**Scale/Scope**:
- Un usuario local, una conversación por pestaña; dos pestañas son independientes.
- Hasta 32 conversaciones en memoria; hasta 2 turnos concurrentes globales como límite de concurrencia del servicio OpenCode; una por conversación.
- Cuatro consultas MCP por turno, en paralelo, con timeout de 5 s por herramienta.
- Sin streaming, adjuntos, voz, multiusuario, base de datos ni integraciones productivas.

**Version gates**: T001 verificó históricamente el servidor existente `2.0.27` y API v2; la generación del proveedor autorizado `opencode` sigue pendiente por 429. T002 probó LangChain, MCP/FastMCP y Langfuse en un entorno desechable, independientemente de esa cuota. Cualquier schema incompatible bloquea readiness.

## Constitution Check

### Pre-research gate

| Principio | Cumplimiento del diseño | Evidencia / condición |
|---|---|---|
| I. Ramas y PR | PASS | Trabajo en `feat/chat-agente-analista`; sin commits a `main`; PR humana pendiente al final |
| II. Spec Kit | PASS | `spec.md` completada con Clarify, este `plan.md`, `research.md`, contratos y quickstart; `/speckit.tasks` es el siguiente paso |
| III. React + JS + SCSS | PASS | Sin TypeScript ni framework UI; solo `react-markdown`, `remark-gfm` y devDependencies de prueba justificadas |
| IV. Agentes en `./agentes/analista` | PASS | Estructura `api/`, `core/`, `mcp/`, `fuentes/`, `prompts/`, `tests/`, requirements y README; prompt externo |
| V. Cero secretos | PASS por diseño | `.env` ignorado; credenciales solo backend/OpenCode; masking Langfuse; sin secretos en bundle/API |
| VI. Rol Analista / PEAS | PASS por diseño; evidencia pendiente | Prompt, esquema, validación de readiness y pruebas adversariales; criterios PEAS obligatorios aún no medidos |
| VII. Integraciones honestas | PASS condicionado a integración final | OpenCode `2.0.27`/API v2 y la compuerta T002 están comprobados; la prueba integrada completa sigue pendiente |
| VIII. Read-only / mínimo privilegio | PASS | Permisos deny en OpenCode, allowlist MCP, loopback, sin shell/archivos/red, timeouts, 409 y aborto |
| IX. No regresión | PASS por diseño | Cambios aditivos en `EnvolturaPaginaComponent`, SCSS, proxy y dependencias; no se tocan pantallas/simulaciones |
| X. Pruebas focalizadas | PASS por diseño | Cinco frentes + contrato REST/MCP/OpenCode + prueba manual end-to-end |
| XI. PowerShell | PASS por diseño | `quickstart.md` con instalación, arranque, health, pruebas y troubleshooting |

### Post-design gate

No se detectan violaciones constitucionales. Quedan dos condiciones de evidencia, no excepciones:

1. **Compuertas previas**: T001 valida OpenCode con configuración temporal; T002 instala y prueba contratos mínimos de LangChain, MCP/FastMCP y Langfuse antes de código dependiente. Una versión candidata o dry-run por sí solo no satisface las compuertas.
2. **Evaluación PEAS**: las metas numéricas no están medidas. La PR no puede declarar SC-005, SC-006, SC-016 ni SC-021 cumplidos sin el informe correspondiente. Si no se ejecuta, se reporta `NOT_MEASURED`.

### Quality gates

| Puerta | Cómo se cumple | Estado |
|---|---|---|
| G1 — Consistencia Spec Kit | Spec, plan, research, data model, contratos y quickstart enlazados; tareas después | **Completada para PLAN** |
| G2 — Build | `npm run build` sin TypeScript; build de Vite | Pendiente de implementación |
| G3 — Pruebas | pytest y Vitest focalizados + prueba manual end-to-end | Pendiente de implementación |
| G4 — Secretos/datos | `.env` fuera de Git; búsqueda en bundle, logs, respuestas y trazas; masking | Pendiente de verificación |
| G5 — No regresión | Recorrido de rutas, Stepper, Accordion y `localStorage` | Pendiente de verificación |
| G6 — Documentación | `quickstart.md` y README del agente | Pendiente de sincronizar con código |
| G7 — Revisión | PR revisada por otra persona; sin merge automático | Pendiente al final |

## Project Structure

### Documentation

```text
specs/002-chat-agente-analista/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── rest-api.yaml
│   ├── mcp-tools.yaml
│   └── opencode-v2.md
└── checklists/
    └── requirements.md
```

### Source code (futuro; este plan no lo crea)

```text
agentes/
├── __init__.py
└── analista/
    ├── __init__.py
    ├── api/
    │   ├── main.py
    │   ├── dependencies.py
    │   ├── errors.py
    │   └── routes/
    │       ├── health.py
    │       └── conversations.py
    ├── core/
    │   ├── config.py
    │   ├── logging.py
    │   ├── prompt_loader.py
    │   ├── health.py
    │   ├── conversation_store.py
    │   ├── context_builder.py
    │   ├── orchestrator.py
    │   ├── output_parser.py
    │   ├── opencode_client.py
    │   └── observability.py
    ├── mcp/
    │   ├── server.py
    │   ├── tools.py
    │   └── repositories.py
    ├── fuentes/
    │   ├── glosario.json
    │   ├── hu_similares.json
    │   ├── estandares.json
    │   └── checklist_vacios.json
    ├── prompts/
    │   └── sistema.md
    ├── opencode/
    │   └── opencode.analista.json
    ├── tests/
    │   ├── unit/
    │   ├── contract/
    │   ├── integration/
    │   └── fixtures/
    ├── requirements.txt
    ├── requirements.lock.txt
    ├── .env.example
    └── README.md

src/
├── components/AsistenteAnalista/
│   ├── AsistenteAnalistaComponent.jsx
│   ├── LanzadorAsistenteComponent.jsx
│   ├── PanelAsistenteComponent.jsx      # mensajes, análisis, preguntas, fuentes, composer y estado de salud
│   ├── DialogoEliminarConversacionComponent.jsx
│   ├── MarkdownAsistenteComponent.jsx
│   └── __tests__/
├── hooks/
│   └── useAsistenteAnalista.js
├── services/
│   └── analystApi.js
├── utils/
│   └── analystErrors.js
├── styles/
│   └── _analyst-chat.scss
└── test/
    └── setup.js

vitest.config.js
```

### Existing files modified (additive)

| Archivo | Cambio | Riesgo controlado |
|---|---|---|
| `src/components/EnvolturaPagina/EnvolturaPaginaComponent.jsx` | Montar `<AsistenteAnalistaComponent />` una vez | No cambia rutas ni layout existente |
| `src/styles/main.scss` | Importar `_analyst-chat.scss` | Solo estilos nuevos; variables/mixins existentes |
| `vite.config.js` | Añadir proxy `/api/analista` → `127.0.0.1:8000` | Conserva puerto 3000 y `open: true` |
| `package.json` / lockfile | Dependencias de Markdown, pruebas y scripts | Sin frameworks UI prohibidos |
| `.gitignore` | `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`, cobertura | No ignora artefactos requeridos |
| `agentes/analista/.env.example` | Añadir límites de TTL, mensajes, MCP y concurrencia | Solo marcadores, sin secretos |
| `agentes/analista/prompts/sistema.md` | Ajustar la nota operativa final para exigir reinicio de OpenCode y backend | No cambia rol, misión ni JSON de salida |
| `agentes/analista/README.md` | Crear guía del agente | Documentación |

No se modifican `src/components/HistoriaUsuario/CrearHistoriaUsuarioComponent.jsx`, `src/utils/storage.js`, las rutas, el Stepper, el Accordion, los datos mock ni las simulaciones existentes.

## Architecture and Integration

### Component flow

```text
Navegador (React 18)
  │  /api/analista/*  (Vite proxy; loopback)
  ▼
FastAPI (Python 3.12, 1 worker)
  ├── ConversationStore (memoria, locks, TTL, generaciones)
  ├── LangChain
  │     ├── contexto + prompt de usuario
  │     ├── RunnableParallel → 4 herramientas MCP
  │     ├── PydanticOutputParser + una reparación
  │     └── adaptador HTTP a OpenCode
  ├── OpenCode Server 2.0.27 / API v2 (127.0.0.1:4096, Basic Auth)
  │     └── agente `analista`, prompt externo, permisos deny
  ├── MCP stdio (FastMCP 4.1.4 / MCP 2.3.0)
  │     └── 4 fuentes JSON de solo lectura
  └── Langfuse v5 (opcional; trazas enmascaradas)

Navegador nunca contacta OpenCode, MCP ni Langfuse.
```

### Turn lifecycle

1. La UI crea una conversación (`POST /conversaciones`) y guarda el ID solo en memoria de React.
2. El usuario envía un mensaje con `request_id` UUID; la UI muestra el mensaje y el indicador de inmediato.
3. FastAPI valida tamaño, identidad y que no haya otro turno activo; un lock de conversación crea el turno.
4. LangChain construye el contexto canónico y ejecuta en paralelo las cuatro herramientas MCP.
5. El backend crea una sesión OpenCode v2 efímera con título opaco, `Model.Ref {providerID,id}` y permisos deny-all.
6. Envía el texto por `POST /api/session/{id}/prompt`, aplica el deadline total y sondea `GET /api/session/{id}/message`; el system prompt se configura una sola vez en el agente.
7. Valida un mensaje assistant v2 directo de `data[]`, requiere `time.completed`, `finish` no-error y contenido textual, y parsea con Pydantic.
8. Si el JSON es inválido, envía un segundo mensaje de reparación en la misma sesión efímera, con el deadline compartido. Si sigue inválido, devuelve `502 AGENT_OUTPUT_INVALID`.
9. Bajo lock, comprueba generación, turno activo y deadline; si sigue vigente, actualiza análisis, preguntas, fuentes y readiness.
10. Elimina la sesión OpenCode en `finally` y responde. La UI inserta la respuesta solo si la época y `request_id` siguen vigentes.

### OpenCode integration decisions

- Sesión nueva por turno para evitar contaminación por turnos cancelados o respuestas tardías.
- El contexto canónico vive en Python; el prompt enviado es el prompt de usuario con estado, mensaje, resultados y limitaciones.
- El agente v2 usa `agents.<nombre>.system`, sustitución `{file:...}` y permisos deny-all; la carga del prompt y los permisos se comprobaron históricamente y la configuración actual sigue esos controles. El contrato no envía un override de sistema por mensaje.
- El servidor ya activo detecta los cambios en `opencode.jsonc` y el agente de proyecto; no se inicia un segundo servidor.
- El backend lee el prompt para validar, versionar y hashear; si falta o está vacío, health `unavailable`; si el hash cambió, `restart_required` y envíos bloqueados.
- El pin observado es OpenCode `2.0.27` (API v2). La compuerta valida las rutas/cuerpos con `GET /api/info` y el OpenAPI oficial v2; `/global/health` y `/doc` devolvieron HTML y no son contratos locales.
- `GET /api/agent` verifica el agente y el backend compara el system cargado sin registrar ni devolver el prompt.
- El modelo/proveedor se configura en OpenCode; si no hay modelo, el health lo indica y no se finge una respuesta.

### MCP integration decisions

- Cuatro herramientas exactas: `consultar_glosario`, `buscar_hu_similares`, `consultar_estandares`, `aplicar_checklist_vacios`.
- La allowlist se aplica en Python y en OpenCode; el prompt no es la única defensa.
- El fan-out es determinista: siempre las cuatro, en paralelo, con timeout de 5 s y error aislado.
- `fuentes_consultadas` se deriva solo de ejecuciones `ok`; cero resultados sigue siendo una fuente consultada.
- Fallos individuales producen `limitaciones`; si el servidor MCP no arranca, health `unavailable` y envío `503 MCP_UNAVAILABLE`.
- Datos ficticios/anonimizados y etiquetados como no confiables; sin escritura, red, shell ni archivos.
- El subpaquete `agentes.analista.mcp` se ejecuta desde la raíz con `python -m agentes.analista.mcp.server` para no sombrear el SDK oficial `mcp`.

### LangChain integration decisions

- `ChatPromptTemplate` construye el prompt de usuario; el system prompt permanece en OpenCode.
- `RunnableParallel` orquesta las cuatro herramientas MCP.
- `PydanticOutputParser` valida `AgentOutput` con campos extra prohibidos.
- `RunnableLambda`/adaptador llama a OpenCode por HTTP; no hay chat model falso.
- Una sola reparación con el error de validación y la salida inválida acotada, como segundo prompt en la misma sesión y con el deadline total compartido.
- `MCPAdapter` de `langchain.mcp` es beta; se aísla detrás de un adaptador propio y se cubre con pruebas de contrato.
- No se usa `create_agent`; el valor está en construcción de prompt, fan-out, timeouts, parseo y reparación.

### Langfuse integration decisions

- Inicialización solo con claves; sin claves, modo deshabilitado y health `degraded`.
- `CallbackHandler` + `propagate_attributes` con `conversation_id`, `request_id`, `turn_id` y metadatos no sensibles.
- Spans de turno, herramienta y OpenCode con duración/estado/error code; tokens/coste solo si el proveedor los reporta.
- `mask_otel_spans` elimina input/output/prompt/completion y contenido de herramientas; conserva IDs, modelo, duración, estado y errores.
- Un fallo de exportación no bloquea el chat; se registra sin contenido y se muestra aviso de diagnóstico degradado.
- El navegador no recibe claves, endpoint OTLP, trace ID ni prompt.

### REST surface

| Método | Ruta | Éxito | Errores relevantes |
|---|---|---|---|
| GET | `/api/analista/health` | 200 `HealthResponse` | 500 |
| POST | `/api/analista/conversaciones` | 201 `CreateConversationResponse` | 503 capacidad |
| POST | `/api/analista/conversaciones/{id}/mensajes` | 200 `AgentTurnResponse` | 404, 409, 422, 502, 503, 504 |
| POST | `/api/analista/conversaciones/{id}/cancelar` | 200 `CancelResponse` | 404, 422 |
| POST | `/api/analista/conversaciones/{id}/reiniciar` | 200 `ResetResponse` | 404, 500 |
| DELETE | `/api/analista/conversaciones/{id}` | 204 | 500 |

Reglas:

- `request_id` UUID obligatorio en el cuerpo de mensaje; idempotencia por solicitud y hash del texto.
- Una sola solicitud en vuelo; segundo envío `409 TURN_IN_PROGRESS`.
- `POST /cancelar` es idempotente: `canceled:false` con `NO_ACTIVE_TURN` si no hay turno; no borra historial.
- `POST /reiniciar` devuelve un ID nuevo y el panel sigue abierto; el ID anterior deja de existir.
- `DELETE` es idempotente y devuelve 204; el frontend cierra el panel.
- Todos los errores usan un sobre estable, sin stack, rutas, secretos ni IDs de sesión OpenCode.
- No hay CORS abierto; el frontend usa el proxy Vite.

## State, Concurrency, Cancellation and Timeout

### Canonical state

- `Conversation`: ID opaco, generación, estado, `active_turn`, turnos completados, análisis, preguntas, fuentes, prompt/hash y TTL.
- `Turn`: `request_id`, `turn_id`, estado, tiempos, resultados de herramientas, reparación, error y sesión OpenCode interna.
- Solo turnos `completado` entran al contexto; `cancelado`, `expirado`, `fallido` y `descartado` no.
- El navegador mantiene la vista de su pestaña; no hay sincronización entre pestañas ni persistencia.

### Concurrency

- Lock por conversación para crear/cerrar turnos, cancelar, reiniciar y eliminar.
- Una sola solicitud en vuelo; sin cola. El segundo envío no crea turno.
- Límite global de turnos concurrentes (2); al superarlo, 503 recuperable.
- El commit final comprueba `generation`, `active_turn`, `turn_id` y deadline bajo lock.
- La cancelación **gana** si marca el turno antes del commit; si el commit ya ocurrió, cancelar devuelve un no-op y la UI descarta la respuesta si ya marcó la época.

### Cancel

- **Cancelar** está disponible solo durante el procesamiento.
- Invalida el turno, limpia `active_turn` y luego llama a `/api/session/{id}/interrupt` y elimina la sesión v2.
- Conserva los mensajes y el contexto anteriores; excluye el turno cancelado.
- No borra la conversación ni inicia una sesión nueva.
- El `POST /mensajes` original devuelve `409 TURN_CANCELLED`; la UI lo ignora si ya canceló.

### Timeout

- Es un deadline **total por mensaje** de 90 s configurables, desde el inicio del turno.
- Cubre MCP, OpenCode, parseo y reparación; no es un timeout por llamada que reinicie el reloj.
- Al vencer: marca expirado/timeout, invalida, interrumpe y elimina la sesión; devuelve `504 TURN_TIMEOUT`.
- La UI tiene su propio timer basado en `timeout_seconds` del health, con margen; al vencer llama a cancelar y no espera.
- Cualquier respuesta posterior se descarta por identidad y generación; el turno no entra al contexto.

### Nuevo chat, Eliminar y recarga

- **Nuevo chat**: limpia el historial visible de inmediato, invalida el turno, crea una conversación nueva y **mantiene el panel abierto**. Si había un turno, lo aborta; su respuesta se descarta.
- **Eliminar**: pide confirmación; invalida/aborta, elimina el contexto y **cierra el panel**. Al reabrir, estado vacío. `DELETE` es idempotente.
- **Cerrar panel**: no cancela, no borra y mantiene el contexto; al reabrir se conserva el historial.
- **Recargar**: el cliente pierde ID e historial y no los recupera de ningún storage. El registro anterior queda temporalmente huérfano solo en memoria del backend, inaccesible para la pestaña nueva, hasta eliminación, TTL de 30 min desde última actividad, expulsión por capacidad o apagado/reinicio. Al límite de 32, se expulsa el registro sin turno activo menos recientemente usado; si todos están ocupados, creación responde `503 CAPACITY_EXCEEDED`. El aborto por descarga es de mejor esfuerzo; TTL e invalidación de identidad garantizan limpieza sin persistencia en navegador.
- **Sesión expirada/404**: se limpia el ID inutilizable, se deshabilita el envío y se ofrece nuevo chat sin recargar.

### Idempotency and late responses

- El cliente reutiliza `request_id` si el fallo es de red o la respuesta es incierta.
- El servidor devuelve la respuesta cacheada si el turno ya se completó con el mismo texto; devuelve 409 si está activo, el texto cambió o el turno fue invalidado.
- La UI usa `requestEpoch` + `activeRequestId` + `AbortController`; al cancelar/reiniciar/eliminar incrementa la época y descarta cualquier `fetch` que llegue después.
- El descarte es por identidad (`conversation_id`, `turn_id`, generación), no por tiempo.

## Frontend Design

### Mount and UX

- Un único `AsistenteAnalistaComponent` al final de `EnvolturaPaginaComponent`; launcher fijo abajo a la derecha, `aria-expanded`/`aria-controls`.
- El panel se mantiene montado al cerrarse; cerrar no desmonta el historial.
- Ancho máximo en escritorio, ancho disponible en móvil; altura limitada para no cubrir el header/navegación; `safe-area-inset-bottom`.
- No hay overflow horizontal a 360 px.
- Launcher con `MessageCircle`/`X` de `lucide-react`; sin nuevos iconos de otra librería.

### State machine

| Estado | Origen | Acciones permitidas |
|---|---|---|
| `idle` | Inicio, respuesta, cancelación terminada, error | Enviar, Nuevo, Eliminar, Cerrar |
| `sending` | Enviar | Cancelar, Cerrar; Nuevo/Eliminar con invalidación |
| `cancelling` | Cancelar | Esperar ack/corto timeout; Cerrar |
| `error` | Error terminal/recuperable | Reintentar, Nuevo, Eliminar, Cerrar |
| `confirm-delete` | Eliminar | Confirmar/Cancelar diálogo |
| `deleting` | Confirmar eliminación | Esperar cierre |
| `resetting` | Nuevo chat | Esperar nueva conversación |

El estado de salud es independiente del estado del turno.

### Controls and semantics

- **Enviar**: deshabilitado si vacío, solo espacios, >4.000 caracteres, salud `unavailable`, turno en curso o confirmación abierta.
- **Cancelar**: visible solo durante procesamiento; aborta el turno y preserva historial/contexto.
- **Nuevo chat**: limpia y mantiene abierto; no pide confirmación (la confirmación es para Eliminar).
- **Eliminar**: diálogo de confirmación; al confirmar, limpia, elimina en el servicio y cierra.
- **Cerrar**: conserva historial y contexto; no cancela.
- **Reintentar**: visible en errores; reutiliza identidad si el fallo es incierto, nueva identidad si es terminal.
- **Ir al último mensaje**: visible si el usuario se desplazó hacia arriba.

### Message and analysis rendering

- Burbuja de usuario en texto plano; respuesta del agente en Markdown seguro.
- Renderiza las cuatro categorías, preguntas con categoría/estado, fuentes con número de resultados y readiness.
- Muestra duración real (`duracion_ms`) y `prompt_version`; no inventa tokens/coste.
- Estado vacío explicativo; no muestra “en línea” sin health.
- `listo_para_redactor` se muestra como “Listo para el Redactor-Revisor”, nunca como “HU aprobada”.
- Banner discreto: “Fuentes simuladas/anonimizadas con fines académicos”.
- Advertencia de datos personales cuando el agente la incluya.

### Safe Markdown

- `react-markdown` + `remark-gfm`; `skipHtml`; `allowedElements` limitada a encabezados, párrafos, listas, tablas, énfasis, código, blockquote, enlaces y separadores.
- Sin `img`, `iframe`, `script`, `style`, `form` ni elementos interactivos. Si GFM genera un `input` de task list, se renderiza como checkbox deshabilitado, sin eventos ni edición.
- `urlTransform` solo permite `http:`, `https:` y anclas `#`; neutraliza `javascript:`, `data:`, `blob:`, `file:` y esquemas desconocidos.
- Enlaces externos con `rel="noopener noreferrer"`; no se cargan imágenes remotas.
- Pruebas con HTML, eventos, esquemas ofuscados y GFM válido; cero ejecución.

### Accessibility

- `role="dialog"` no modal con `aria-labelledby`; foco al abrir y retorno al launcher al cerrar.
- Escape cierra el panel; no hay focus trap que impida usar la página.
- `aria-live="polite"` para estado/mensajes nuevos; `role="alert"` para errores.
- Labels en botones, composer y campos; contraste suficiente; `prefers-reduced-motion`.
- Anuncio de “Procesando…”, “Respuesta lista”, “Turno cancelado”, “Tiempo agotado” y errores.
- Navegación completa por teclado, incluida la confirmación de eliminación.

### Health and errors

- Al montar, consulta `/health`; muestra `Comprobando…`, `Listo`, `Degradado` o `No disponible`.
- Si `unavailable`, deshabilita el envío y ofrece reintentar health/nuevo chat.
- Si `degraded` por Langfuse, el chat funciona y muestra “Diagnóstico limitado”.
- Errores mapeados a mensajes comprensibles con acciones; sin stack ni IDs internos.
- `404` limpia el ID y deshabilita el envío; ofrece nuevo chat.
- Un error no borra el historial previo; el usuario puede reintentar o iniciar nuevo chat.
- Límite de 4.000: muestra contador; conserva el texto y no envía.

## Security and Privacy

- Loopback exclusivo; sin CORS abierto; proxy Vite para desarrollo.
- Basic Auth de OpenCode solo en backend; Langfuse solo en backend; `.env` ignorado.
- Sin secretos en React, bundle, URLs, almacenamiento, logs, respuestas ni trazas.
- Sin shell, archivos, internet, correo, repositorios, bases productivas ni tools de OpenCode.
- Allowlist MCP en Python y permisos deny en OpenCode; el prompt no es la única defensa.
- Entrada validada: UUID, tamaño, campos extra, JSON; mensajes vacíos y demasiado largos rechazados.
- Timeout total, una solicitud en vuelo, aborto, reset y errores controlados.
- Markdown sin HTML crudo, sin scripts, sin imágenes remotas y con URLs saneadas.
- Datos de fuentes ficticios/anonimizados; sin datos reales de asegurados, pólizas o siniestros.
- Logs sin contenido, credenciales ni datos personales; trazas enmascaradas.
- El navegador no contacta OpenCode, MCP ni Langfuse.
- No se presenta la demo como solución productiva.

## Testing and Acceptance

### Strategy

La verificación cubre los cinco frentes de la Constitución X:

1. API, contratos y errores.
2. Reset/cancelación durante generación y descarte tardío.
3. Concurrencia y duplicados.
4. Markdown seguro/XSS.
5. Flujo del agente, allowlist, no invención y salida estructurada.

Además: contrato OpenCode, contrato MCP, health, observabilidad, secretos, no persistencia y regresión. Los dobles de OpenCode/MCP solo existen en pruebas; el runtime no tiene respuestas simuladas.

### Backend tests

| ID | Prueba | Resultado esperado |
|---|---|---|
| B-01 | Crear conversación y validar esquema | 201, UUID, límites |
| B-02 | Mensaje vacío/solo espacios | 422 `MESSAGE_EMPTY`; no crea turno |
| B-03 | Mensaje >4.000 | 422 `MESSAGE_TOO_LONG`; conserva texto en UI |
| B-04 | `request_id` ausente/inválido | 422 `INVALID_REQUEST` |
| B-05 | Envío válido con OpenCode mock | 200, esquema completo, duración |
| B-06 | Doble envío concurrente | Uno 200; otro 409 `TURN_IN_PROGRESS`; un solo turno |
| B-07 | Idempotencia mismo `request_id` + mismo texto completado | 200 cacheado, sin segundo turno |
| B-08 | Mismo `request_id` + texto distinto | 409 `REQUEST_ID_CONFLICT` |
| B-09 | Cancelar durante generación | 409 `TURN_CANCELLED`; sin commit; contexto previo intacto |
| B-10 | Cancelar sin turno | 200 `canceled:false`, `NO_ACTIVE_TURN` |
| B-11 | Reiniciar durante generación | ID nuevo; respuesta vieja descartada; panel lógico abierto |
| B-12 | Eliminar durante generación | 204; respuesta vieja descartada; repetir 204 |
| B-13 | Timeout total con deadline corto | 504 `TURN_TIMEOUT`; interrupt/delete invocados; sin commit |
| B-14 | Carrera cancelación/commit | Cancelación gana si marca antes; si gana el commit, cancel es no-op |
| B-15 | Salida inválida y reparación exitosa | Una reparación; 200 si válida |
| B-16 | Salida inválida tras reparación | 502 `AGENT_OUTPUT_INVALID`; sin JSON crudo |
| B-17 | Readiness incoherente | Rechazo/reparación; no se presenta como listo |
| B-18 | Categoría/estado de pregunta inválido | Rechazo de esquema |
| B-19 | Preguntas duplicadas/omitidas | Fusión conserva IDs y respondidas; no desaparecen pendientes |
| B-20 | MCP: cuatro tools exactas | Listado correcto; sin tools extra |
| B-21 | MCP: fallo/timeout de una tool | Limitación; las demás continúan; fuentes solo de ok |
| B-22 | MCP: resultado vacío | Fuente consultada con 0 resultados |
| B-23 | MCP: intento de ruta/shell/URL | Sin efecto; error de validación |
| B-24 | OpenCode 2.0.27: info/create/prompt/message/interrupt/delete | Rutas y schemas de API v2 comprobados con instancia real y OpenAPI oficial |
| B-25 | OpenCode v2: assistant `content` y `time.completed` | Texto assistant concatenado; salida no textual/incompleta rechazada |
| B-26 | OpenCode: `GET /api/agent` | Se valida prompt cargado sin registrar ni devolver su contenido |
| B-27 | OpenCode: auth/versión/agente ausente | 503 con código correcto |
| B-28 | Prompt ausente/vacío | Health `unavailable`; envío `PROMPT_INVALID` |
| B-29 | Prompt cambiado sin reiniciar | `restart_required`; envío `PROMPT_RESTART_REQUIRED` |
| B-30 | Health ready/degraded/unavailable | Estados coherentes; nunca “ready” sin comprobar |
| B-31 | Langfuse masking | Sin input/output/prompt; IDs/duración/estado presentes |
| B-32 | Langfuse caído/deshabilitado | Chat responde; health degraded; aviso UI |
| B-33 | Logs/respuestas sin secretos | Búsqueda de claves/headers/stack sin hallazgos |
| B-34 | Contexto incluye solo completados | Cancelados/fallidos/expirados no aparecen |
| B-35 | Recarga/404 simulado | Nuevo chat; sin reutilizar contexto |

### Frontend tests

| ID | Prueba | Resultado esperado |
|---|---|---|
| F-01 | Montaje en rutas | Launcher visible en todas; no cambia ruta |
| F-02 | Abrir/cerrar | Historial se conserva; cierre no cancela |
| F-03 | Nuevo chat | Limpia, panel abierto, llamada de reset |
| F-04 | Eliminar | Confirmación, limpieza, cierre |
| F-05 | Envío y respuesta | Indicador inmediato; mensaje, análisis, preguntas, fuentes, readiness |
| F-06 | Cancelar | Control solo en proceso; historial previo; turno marcado cancelado |
| F-07 | Timeout | Timer, cancelación, error recuperable, sin spinner |
| F-08 | Doble clic/Enter | Un solo envío/turno |
| F-09 | Respuesta tardía | Ignorada tras reset/cancelar por época/ID |
| F-10 | Recarga | Chat vacío; sin lecturas/escrituras de storage del chat |
| F-11 | Error de red/409/404/502/503/504 | Mensaje comprensible y acción |
| F-12 | Markdown/XSS | Tabla GFM visible; sin script/img/HTML/URLs peligrosas |
| F-13 | Estructura inválida | Error controlado; no JSON crudo |
| F-14 | Accesibilidad | Roles, labels, foco, Escape, aria-live |
| F-15 | Auto-scroll | No fuerza si el usuario está arriba; botón de último mensaje |
| F-16 | Health | ready/degraded/unavailable; no “en línea” sin health |
| F-17 | Responsive | 360 px/768 px/escritorio sin overflow horizontal |
| F-18 | Sin secretos/persistencia | Bundle/DOM sin claves ni chat en storage |

F-15 implementa FR-013 con el umbral verificable de 80 px: si el usuario está a esa distancia o
menos del final, un mensaje nuevo desplaza al final; si está más arriba, se conserva la posición y
aparece «Ir al último mensaje». Activar el control desplaza al final y lo oculta. La escritura y
los cambios que no agregan mensajes no cambian el scroll. T014 cubre estos casos con pruebas.

### Contract and integration tests

- Validar `rest-api.yaml` contra respuestas y errores del backend.
- Validar `mcp-tools.yaml` con listado real y esquemas de entrada/salida.
- Probar OpenCode v2 con `GET /api/info`, creación, admisión, sondeo de mensaje assistant, interrupt y eliminación; contrastar con OpenAPI v2 oficial. Un 429/503 real se trata como indisponibilidad.
- Probar la cadena completa React → FastAPI → LangChain → OpenCode → MCP → respuesta en el navegador.
- Verificar trazas Langfuse con masking y modo deshabilitado.
- Verificar que el navegador no hace llamadas a `:4096` ni a Langfuse.
- Verificar que un fallo de observabilidad no bloquea la respuesta.

### Error and recovery matrix

| Error | HTTP | UI | Contexto | Reintento |
|---|---:|---|---|---|
| Servicio/modelo no disponible | 503 | No disponible; no respuesta falsa | Sin cambios | Reintentar |
| Timeout | 504 | Timeout, sin spinner | Turno no entra | Reintentar/nuevo |
| Salida inválida | 502 | Error controlado | Turno no entra | Reintentar/nuevo |
| Solicitud en curso | 409 | “Turno en proceso” | Sin duplicado | Esperar/cancelar |
| Sesión expirada/404 | 404 | Nuevo chat | ID limpiado | Nuevo chat |
| Reinicio en proceso | — | Limpia de inmediato | Invalidado | Nuevo |
| Fuente no disponible | — | Limitación visible | Continúa con disponibles | Reintentar fuente/turno |
| Auth/config | 503 | Accionable sin secretos | Sin cambios | Corregir y reintentar |
| Observabilidad caída | — | Aviso degradado | Respuesta normal | No aplica |
| Red incierta | — | Error; reutiliza identidad | Sin duplicado | Reintentar mismo `request_id` |
| Markdown malicioso | — | Neutralizado; resto legible | Sin efecto | No aplica |
| Respuesta tardía tras eliminar | — | Descartada | Sin efecto | No aplica |
| Cancelación | 409 | Turno cancelado | Contexto previo conservado | Enviar otro |

### Success criteria verification

| SC | Verificación | Estado inicial |
|---|---|---|
| SC-001 | Manual/performance: rutas y apertura | Pendiente |
| SC-002 | Prueba de usabilidad: 3 interacciones | Pendiente |
| SC-003 | UI timer + backend deadline | Pendiente |
| SC-004 | Integración real; 0 respuestas simuladas | Pendiente |
| SC-005 | Evaluación M1/M5; N=10 para cumplir; N<10=`PARTIAL` | **NOT_MEASURED** |
| SC-006 | Evaluación M2 | **NOT_MEASURED** |
| SC-007 | 20 ensayos de reset | Pendiente |
| SC-008 | 20 ensayos de doble envío | Pendiente |
| SC-009 | Pruebas de estructura | Pendiente |
| SC-010 | 10 cargas maliciosas | Pendiente |
| SC-011 | Fallos inducidos | Pendiente |
| SC-012 | Trazas + observabilidad caída | Pendiente |
| SC-013 | Regresión + build | Pendiente |
| SC-014 | Fuentes reales | Pendiente |
| SC-015 | Storage/bundle/logs | Pendiente |
| SC-016 | 5 usuarios; satisfacción ≥4/5 | **NOT_MEASURED** |
| SC-017 | Rol/inyección/invención | Pendiente |
| SC-018 | 20 ensayos de cancelación | Pendiente |
| SC-019 | 20 recargas | Pendiente |
| SC-020 | 20 timeouts | Pendiente |
| SC-021 | Evaluación M3 | **NOT_MEASURED** |

SC-005, SC-006, SC-016 y SC-021 son criterios de aceptación obligatorios. En esta planificación están `NOT_MEASURED`; no se declaran cumplidos. La evaluación inicial de 3–5 casos permite reportar progreso PEAS; SC-005 (M1 y M5) solo se cumple con N=10. Con N<10 se reporta `PARTIAL`, que no satisface aceptación.

### FR coverage map

Cada uno de los 47 requisitos tiene una tarea y una evidencia verificable asignadas. SC-IDs y
evidencias son resultados pendientes hasta que se ejecuten las tareas.

| Requisito | Tareas y verificación |
|---|---|
| FR-001 | T014, T016, T044: launcher visible en todas las rutas y no cubre navegación/controles. |
| FR-002 | T014, T016: abrir/cerrar sin navegación ni recarga. |
| FR-003 | T014, T016, T027: historial y turno sobreviven al cierre del panel. |
| FR-004 | T028, T032: reinicio crea identidad vacía y mantiene panel abierto. |
| FR-005 | T028, T032: confirmación, borrado servidor y cierre del panel. |
| FR-006 | T014, T028: pruebas independientes de cerrar, nuevo chat y eliminar. |
| FR-007 | T014, T017, T044: 360/768/escritorio, sin overflow y navegación utilizable. |
| FR-008 | T014, T017, T044: teclado, foco, lector de pantalla, estados y contraste. |
| FR-009 | T018, T021, T042: cadena real, sin respuestas simuladas. |
| FR-010 | T018, T020, T023: vacío, Unicode y límite de 4.000 caracteres. |
| FR-011 | T018, T020, T029: un turno por conversación, deduplicación y cancelación. |
| FR-012 | T020, T044: indicador medido antes de 2 s y fin terminal explícito. |
| FR-013 | T014, T044 (F-15): seguir al final solo a ≤80 px; preservar scroll anterior, mostrar/activar «Ir al último mensaje» y no mover por cambios sin mensaje. |
| FR-014 | T024, T042: Markdown, cuatro clasificaciones, preguntas, fuentes y readiness visibles. |
| FR-015 | T004, T024: esquema completo con IDs y duración real. |
| FR-016 | T023, T024: respuesta inválida produce error; sin JSON crudo ni parcial. |
| FR-017 | T023, T026, T046: Markdown GFM y matriz de cargas maliciosas neutralizada. |
| FR-018 | T004, T024, T035: enum de categorías/estados y render validado. |
| FR-019 | T032–T035: contexto por sesión; reset, borrado, recarga y expiración lo invalidan. |
| FR-020 | T033–T035: respuesta de Negocio actualiza clasificación y preguntas pendientes. |
| FR-021 | T006, T009, T038, T042: solo cuatro fuentes de lectura MCP ejecutadas. |
| FR-022 | T006, T009, T024: fuentes provienen de ejecuciones exitosas reales. |
| FR-023 | T036–T038, T047–T050: pruebas adversariales y medición de cero invenciones. |
| FR-024 | T036–T038: prohibición de redactar/aprobar/priorizar HU. |
| FR-025 | T036–T038: inyección en mensaje/fuente no altera misión. |
| FR-026 | T001, T007, T037, T040: archivo externo, carga verificada, versión/hash y reinicio. |
| FR-027 | T001, T006–T009, T038: permisos efectivos deny y allowlist exterior al prompt. |
| FR-028 | T011, T012, T015, T039, T041, T044: secretos fuera de browser/bundle/logs/trazas. |
| FR-029 | T014, T031–T032, T045: sin storage; pestaña nueva vacía y registro volátil con TTL. |
| FR-030 | T019, T040: estado real `ready`/`degraded`/`unavailable`. |
| FR-031 | T022, T043: mensajes recuperables sin datos internos. |
| FR-032 | T030–T031, T043, T045: deadline total, aborto y descarte tardío. |
| FR-033 | T027–T032: reset/delete invalidan antes de abortar. |
| FR-034 | T022, T032, T043: 404/TTL ofrece chat nuevo sin reutilizar contexto. |
| FR-035 | T011, T039–T041: correlación y duración con masking comprobado. |
| FR-036 | T011, T039, T041, T043: chat sigue operativo con Langfuse caído o ausente. |
| FR-037 | T014, T044: regresión de pantallas, datos, estilos, rutas y simulaciones. |
| FR-038 | T003, T010, T014, T044: backend loopback y sin CORS abierto. |
| FR-039 | T036–T038, T047–T050: aviso y manejo adversarial de datos personales. |
| FR-040 | T006, T009, T038, T043: fuente fallida/límite declarado sin invención. |
| FR-041 | T024, T042, T044: duración y fuentes aparecen solo si son medidas/ejecutadas. |
| FR-042 | T027, T029, T031, T043: cancelación preserva contexto previo y excluye turno. |
| FR-043 | T027, T029, T031, T043: respuesta tardía descartada por identidad/época. |
| FR-044 | T037, T047–T050: protocolo PEAS congelado y métricas reportadas con evidencia. |
| FR-045 | T006, T037, T042, T047: fuentes anonimizadas y motor local; sin sistemas reales. |
| FR-046 | T036–T038, T047–T050: actuadores allowlist y rol evaluados. |
| FR-047 | T033–T035, T037, T047: sensores de usuario, Negocio, analista, tools y contexto. |

### PEAS measurement protocol

**Estado: obligatorio y aún no medido.** Los umbrales de Clarify son criterios de aceptación, no resultados: vacíos detectados ≥80 %, preguntas útiles ≥70 %, tiempo de análisis ≤50 % de la línea base, satisfacción ≥4/5 y cero datos inventados presentados como hechos. No se muestran en la UI ni se declaran cumplidos sin evidencia.

1. **Corpus**: usar 3–5 requerimientos históricos anonimizados para la evaluación inicial PEAS, de acuerdo con Clarify; registrar N real. Para afirmar SC-005 (M1 y M5), ampliar la muestra a 10 porque ese criterio especifica ese tamaño. Con N < 10, SC-005 se reporta `PARTIAL`, no cumplido.
2. **Congelar**: commit, `prompt_version`, `prompt_hash`, modelo/proveedor y configuración de OpenCode.
3. **Línea base manual**: los mismos analistas, mismas fuentes y condiciones; medir tiempo y vacíos detectados sin el agente.
4. **Ejecución asistida**: usar el chat real; guardar respuestas y trazas enmascaradas; no revelar objetivos a los evaluadores.
5. **Etiquetado**: dos evaluadores independientes marcan vacíos válidos, preguntas útiles, invenciones y satisfacción; discrepancias se adjudican.
6. **Cálculo**:
   - M1: recall/precisión de vacíos contra el etiquetado; reportar N y proporción.
   - M2: proporción de preguntas clasificadas como útiles y llevadas a Negocio.
   - M3: mediana de tiempo asistido vs. línea base; reportar −% solo si se midió.
   - M4: encuesta de 5 usuarios; media y comentarios.
   - M5: conteo de datos inventados presentados como hechos; objetivo 0.
7. **Informe**: `EvaluationRecord` con estado `MEASURED`/`PARTIAL`/`NOT_MEASURED`, evidencia y limitaciones; adjuntar a la PR.
8. **Compuerta**: los cinco umbrales son obligatorios. Sin informe se mantienen `NOT_MEASURED`; con muestra insuficiente se usa `PARTIAL`. Ningún estado equivale a aceptación. La reducción de cambios post-grooming queda fuera de esta fase.

## Implementation Phases

### Phase 0 — Preflights and compatibility gates

- T001 comprobó históricamente el servidor v2 activo, auth local, `/api/info`, agente, prompt, permisos, generación con Ollama, cancelación y eliminación; esa generación no valida `providerID=opencode`. La generación autorizada vigente sigue pendiente; no se inició otro servidor.
- T002 prueba importaciones y contratos mínimos de LangChain, MCP/FastMCP y Langfuse con las versiones candidatas; comprueba masking y degradación sin credenciales. No escribe código de aplicación.
- **Gate**: T006/T009/T011 y sus consumidores dependen de T002. El trabajo OpenCode estructural depende de T001; un 429 deja pendientes solo generación real y tareas que la requieren, y no detiene el trabajo independiente. Si cualquier API/schema no coincide, se detiene y corrige la investigación/contratos/versiones antes de continuar.
- El ciclo estructural interrupt/eliminación v2 se comprobó históricamente. La llamada con el modelo `opencode` está pendiente en T001; la integración completa React→backend sigue en T042.

### Phase 1 — Backend foundation

- Configuración, `.env`, logging sin contenido, errores, IDs, store en memoria, locks, TTL, capacity.
- Prompt loader con versión/hash/validación.
- Health con dependencias y `restart_required`.
- Esqueleto REST y contrato OpenAPI.
- **Gate**: pruebas de validación, store y health.

### Phase 2 — MCP server and sources

- FastMCP stdio, cuatro tools, fixtures JSON, repositorios de solo lectura.
- Allowlist, límites, timeouts, errores, determinismo, fichas de fuentes.
- **Gate**: contrato MCP y pruebas de no escritura/no red.

### Phase 3 — Agent pipeline

- LangChain prompt/contexto, `RunnableParallel`, adaptador MCP, OpenCode client, parser Pydantic, reparación.
- Contexto canónico, fusión de preguntas, readiness, fuentes.
- **Gate**: pruebas de cadena, parseo, reparación y contrato OpenCode.

### Phase 4 — Concurrency, cancel, timeout, lifecycle

- Una solicitud en vuelo, idempotencia, cancelación, reset, delete, expiración y descarte tardío.
- Deadline total, aborto, limpieza de sesión y errores.
- **Gate**: B-06–B-14, B-34, B-35.

### Phase 5 — Frontend

- Componentes, hook, API client, state machine, Markdown, tarjetas, health, errores, a11y, responsive, SCSS.
- Proxy Vite y montaje en `EnvolturaPaginaComponent`; sin tocar pantallas.
- **Gate**: F-01–F-18 + build.

### Phase 6 — Observability

- Langfuse cliente, callback, spans, masking, modo deshabilitado, aviso de degradación.
- **Gate**: B-31/B-32 y revisión de trazas.

### Phase 7 — Verification and delivery

- Suite completa, build, prueba manual end-to-end, regresión, búsqueda de secretos.
- Evaluación PEAS con corpus disponible; informe y estado real.
- README del agente, quickstart sincronizado, evidencia de PR.
- **Gate**: G1–G7; sin merge automático.

## Risks and Mitigations

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Diferencias en API/configuración v2 de OpenCode | Media | Alto | Validar `GET /api/info`, OpenAPI v2 y permisos efectivos; bloquear readiness ante schema o versión inesperados |
| `MCPAdapter` beta cambia | Media | Alto | Pin 1.4.7; adaptador aislado; pruebas de listado |
| Incompatibilidad FastAPI/Starlette/FastMCP | Media | Alto | Dry-run resuelto; instalación/import real en Fase 0; lockfile |
| Modelo OpenCode no configurado o lento | Alta | Alto | Health accionable; timeout 90 s; no simular respuesta |
| OpenCode no carga el prompt | Media | Alto | Validar archivo/hash; `restart_required`; bloqueo de envío |
| Respuesta tardía contamina contexto | Media | Alto | Invalidar antes de abortar; lock/generación; pruebas de carrera |
| Doble envío duplica turno | Media | Medio | `request_id`, one-in-flight, 409, UI disable |
| XSS en Markdown | Baja | Alto | `skipHtml`, allowlist, urlTransform, tests adversariales |
| Secreto en bundle/log/traza | Baja | Muy alto | `.env`, proxy, masking, búsqueda, G4 |
| Langfuse caído bloquea chat | Baja | Medio | Inicialización opcional; try/catch; flush no bloqueante |
| Herramienta MCP inventa/omite fuentes | Media | Alto | Fan-out real; fuente solo por ejecución; limitaciones |
| Inyección de prompt en fuentes | Media | Alto | Delimitadores, “datos no confiables”, sin tools OpenCode |
| Corpus PEAS insuficiente | Alta | Medio | Mínimo 3–5; reportar N; `PARTIAL` si <10 |
| Regresión de pantallas/Stepper | Baja | Alto | Cambios aditivos; G5; pruebas paralelas |
| Nombre `mcp` sombrea SDK | Media | Medio | `agentes.analista.mcp`; arranque desde raíz; test |
| Paths/encoding Windows | Media | Medio | PowerShell, UTF-8, comandos reproducibles |
| Una sola instancia/pérdida al reiniciar | Alta | Bajo | Documentado; sin persistencia; TTL |

## Complexity Tracking

No hay excepciones a la Constitución. La complejidad añadida se justifica frente a la alternativa más simple:

| Complejidad | Por qué es necesaria | Alternativa simple descartada |
|---|---|---|
| Servicio Python + MCP + OpenCode | La Constitución exige agente en `./agentes/analista`, MCP real, OpenCode y LangChain | Un solo endpoint Express o respuestas simuladas; incumple |
| Sesión OpenCode por turno | Aislamiento de contexto y descarte de turnos cancelados/tardíos | Sesión persistente; contamina contexto |
| Fan-out determinista de 4 tools | Verifica fuentes reales y evita selección no auditable | Selección por modelo; no garantiza consultas |
| LangChain con parser/reparación | Tipado, orquestación y uso efectivo exigido | Llamada HTTP directa sin validación; incumple |
| Estado en memoria con locks/TTL | Suficiente para demo local; sin DB | Base de datos/cola; sobra para el alcance |
| Markdown + dependencias de prueba | Seguridad GFM y G3 | HTML crudo o no probar; incumple |
| Session-per-turn + epoch en UI | Doble defensa contra respuestas tardías | Solo tiempo/UI; no confiable |

No se introducen TypeScript, framework UI, gestor de estado, base de datos, cola, vector store ni streaming. Las dependencias nuevas se fijan y se justifican en la PR.

## Definition of Done

- Todas las FR y ERR tienen implementación y prueba o evidencia manual.
- Una sola solicitud en vuelo; cancelar/timeout/reiniciar/eliminar invalidan y descartan respuestas tardías.
- Nuevo chat mantiene el panel abierto; Eliminar confirma y cierra; Cerrar conserva; recarga inicia vacío.
- Markdown seguro y sin HTML crudo; sin secretos ni persistencia de chat en navegador.
- Backend con OpenCode, LangChain, MCP y Langfuse reales; sin respuestas simuladas.
- `npm run build`, pytest y Vitest en verde; prueba manual end-to-end adjunta.
- G1–G7 verificadas; PR revisada; sin escritura directa a `main`.
- Informe PEAS con evidencia de los cinco umbrales obligatorios. Si no se midió, `NOT_MEASURED`; si N < 10, SC-005 `PARTIAL`, nunca “cumplido”. Ninguno de esos estados satisface la aceptación.
- Quickstart y README actualizados con comandos PowerShell reproducibles.

## Open Issues and Decisions

1. **SC-005 y muestra PEAS**: resuelto por alcance de medición. La evaluación inicial sigue siendo 3–5 según Clarify; SC-005 requiere N=10 y con N<10 se reporta `PARTIAL`, nunca cumplido.
2. **Métricas PEAS**: los cinco umbrales son obligatorios, pero todavía no medidos. `NOT_MEASURED` comunica estado, no aprobación; la UI no los presenta como resultados.
3. **OpenCode**: T001 confirmó `2.0.27`/API v2 en el servidor existente; el contrato activo está en `contracts/opencode-v2.md`. No se infiere el protocolo v1.
4. **`MCPAdapter` beta**: adaptador aislado y pruebas; si cambia, se actualiza el contrato antes de la UI.
5. **Modelo/proveedor**: se configura en OpenCode; sin credenciales en el repo. Si falta, health y error accionable.
6. **Langfuse local**: puede estar deshabilitado; el modo degradado es parte de la aceptación.
7. **Prompt**: se edita el archivo; requiere reinicio de OpenCode y backend; el health detecta hash desincronizado.
8. **Dependencias**: versiones candidatas resueltas en dry-run; la instalación/import real es Fase 0 y el lockfile se genera después.
9. **Persistencia**: una sola instancia, memoria; un reinicio invalida sesiones. Fuera de alcance la persistencia.
10. **`.opencode/` ignorado**: no se modifica en este feature; el prompt del agente vive en `agentes/analista/prompts/`.

## References

- `specs/002-chat-agente-analista/spec.md`
- `.specify/memory/constitution.md` v1.0.0
- `agentes/analista/prompts/sistema.md`
- `agentes/analista/.env.example`
- `specs/002-chat-agente-analista/research.md`
- `specs/002-chat-agente-analista/data-model.md`
- `specs/002-chat-agente-analista/contracts/rest-api.yaml`
- `specs/002-chat-agente-analista/contracts/mcp-tools.yaml`
- `specs/002-chat-agente-analista/contracts/opencode-v2.md`
- `specs/002-chat-agente-analista/quickstart.md`
- OpenCode `2.0.27` API v2 (`GET /api/info` y OpenAPI oficial); LangChain 1.4.7; FastMCP 4.1.4; Langfuse 5.0.4; React Markdown 10; Remark GFM 4.

**Nota de nomenclatura (actualizada):** los componentes se agrupan por funcionalidad en `src/components/<Funcionalidad>/`, con nombres en español, en singular y con sufijo `Component`; los hooks usan `use` + nombre en español (`useAsistenteAnalista`). Las vistas del panel (análisis, preguntas, fuentes, composer y estado de salud) se implementaron dentro de `PanelAsistenteComponent.jsx` en lugar de archivos separados.
