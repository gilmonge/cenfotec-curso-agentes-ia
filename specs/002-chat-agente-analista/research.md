# Research — Chat flotante con Agente Analista

**Feature**: `002-chat-agente-analista`  
**Branch**: `feat/chat-agente-analista`  
**Date**: 2026-10-26  
**Status**: Investigación inicial y resultados de compuertas. Las hipótesis OpenCode v1 quedaron supersedidas por el contrato v2; la evidencia de generación con un proveedor histórico no acredita el proveedor `opencode` vigente. La referencia normativa es [contracts/opencode-v2.md](./contracts/opencode-v2.md).

> **Decisión vigente (2026-10-27):** OpenCode Server `2.0.27`/API v2 es la única interfaz de generación. Las comprobaciones estructurales de T001 se conservan; ninguno de los nueve modelos con costo cero produjo respuesta (ocho 429 y uno no disponible). Los resultados históricos de generación con otro proveedor son evidencia, no requisito arquitectónico.

## 1. Objetivo y restricciones de la investigación

La investigación debía resolver cómo integrar, de forma real y verificable, React 18 + Vite 5 con un backend FastAPI, OpenCode Server, LangChain, herramientas MCP de solo lectura y Langfuse, sin:

- simular respuestas del chat;
- exponer secretos al navegador;
- sustituir pantallas, rutas o simulaciones existentes;
- introducir TypeScript, un framework UI nuevo o `rehype-raw`;
- persistir la conversación en el navegador;
- aceptar respuestas tardías después de cancelar, reiniciar o eliminar;
- presentar como logradas las metas PEAS todavía no medidas.

La especificación `specs/002-chat-agente-analista/spec.md` y la Constitución v1.0.0 son la autoridad. El prompt existente `agentes/analista/prompts/sistema.md` define el rol y el JSON de salida; el plan no lo modifica.

## 2. Hechos verificados en el entorno

| Elemento | Valor observado | Uso en el plan |
|---|---|---|
| Sistema | Windows, PowerShell | Comandos de `quickstart.md` |
| Node | `24.15.0` | Frontend y pruebas |
| npm | `11.12.1` | Instalación y scripts |
| Python | El venv local declara CPython `3.12.10`, pero su intérprete base no está accesible en esta sesión | Requiere reparar el runtime local antes de validar el backend |
| OpenCode objetivo observado | `2.0.27` | API v2; PID, ejecutable, autenticación y API verificados por T001 |
| Frontend | React 18.2, Vite 5.1.6, React Router 6.22, JavaScript, SCSS | Sin migración de stack |
| Pruebas frontend | No existían dependencias ni script de prueba | Se añade Vitest + RTL + jsdom como devDependencies |
| Persistencia existente | `localStorage` solo para historias (`storycraft_user_stories`) | No se toca ni se reutiliza para el chat |
| Prompt del Analista | `agentes/analista/prompts/sistema.md`, versión editorial 1.0.0 | Se carga desde archivo; no se hardcodea |
| Langfuse local | No se asumió configurado | El modo deshabilitado debe funcionar y mostrarse como degradado |
| Git | Rama `feat/chat-agente-analista`; sin commits de la funcionalidad | No se hicieron escrituras Git durante la planificación |

La comprobación inicial asumió API v1 y resultó incorrecta para la instancia disponible: `/global/health` y `/doc` entregan HTML. T001 contrastó el contrato real con [`/api/info`](https://dev.opencode.ai/v2/docs/api) y el [OpenAPI oficial v2](https://dev.opencode.ai/v2/openapi.json). La autenticación, configuración y ciclo de vida se probaron en la instancia existente; no se inició otro servidor.

### Decisiones de Clarify consideradas

| # | Decisión aclarada | Resolución de diseño |
|---|---|---|
| 1 | Nuevo chat y Eliminar tienen efectos distintos | Nuevo chat crea identidad nueva y conserva abierto el panel; Eliminar requiere confirmación, elimina contexto y cierra el panel. |
| 2 | Cancelación explícita durante procesamiento | Se invalida y aborta solo el turno en curso; el turno no se añade al contexto y se conservan los mensajes/contexto anteriores. |
| 3 | Recargar inicia vacío | No se guarda historial ni ID de conversación en el navegador; estado canónico en memoria del backend, limitado a la vida de pestaña/servicio. |
| 4 | Timeout total de 90 s | Un deadline compartido cubre MCP, OpenCode y validación; al vencer se aborta y se descarta toda salida tardía. |
| 5 | Cinco métricas PEAS obligatorias | Umbrales de aceptación: vacíos ≥80 %, preguntas útiles ≥70 %, tiempo −50 %, satisfacción ≥4/5 y cero invenciones. No se declara cumplimiento sin medición. La evaluación inicial es de 3–5; SC-005 mantiene el requisito de N=10 para marcarse cumplido. |

## 3. Decisiones de arquitectura

| ID | Decisión | Razón | Alternativa descartada |
|---|---|---|---|
| D-01 | Backend Python 3.12 con FastAPI, Pydantic v2, `httpx`, `pydantic-settings` y Uvicorn | Stack solicitado, tipado y validación; una sola instancia local | Node para el agente; viola la separación pedida |
| D-02 | OpenCode `2.0.27`/API v2 como única interfaz de generación | Versión y rutas comprobadas históricamente; generación con el proveedor `opencode` sigue pendiente y el navegador no lo contacta | Asumir compatibilidad con v1 o conectar FastAPI directamente a un proveedor |
| D-03 | Agente OpenCode personalizado `analista` declarado en `opencode.jsonc` | Mantiene el prompt fuera de Python y usa configuración de proyecto v2 | Prompt embebido en Python; difícil de auditar |
| D-04 | `agents.analista.system` con `{file:...}` y permisos deny-all | T001 confirmó prompt cargado y deny-all en agente/sesión | Suponer que `agent.<id>.prompt` legacy es alias v2 |
| D-05 | Una sesión efímera de OpenCode por turno | El contexto canónico vive en Python; una sesión nueva no arrastra turnos cancelados o contaminados | Sesión persistente por conversación; una respuesta tardía podría contaminar el contexto |
| D-06 | El backend ejecuta siempre las cuatro herramientas MCP en paralelo, con `RunnableParallel`, y entrega los resultados al modelo | Garantiza consultas reales, permite declarar fuentes solo por ejecución y evita selección no determinista | Selección de herramientas por el modelo; difícil de auditar y de mapear a fuentes reales |
| D-07 | LangChain construye el prompt de contexto, orquesta las herramientas y parsea con Pydantic; una sola reparación | Cumple el uso efectivo de LangChain sin introducir un agente autónomo | `create_agent` con un chat model simulado; viola la integración real |
| D-08 | Langfuse v5 con `CallbackHandler`, `propagate_attributes` y `mask_otel_spans` | Trazas correlacionadas y exportación sin texto completo del usuario | Instrumentación casera; no cumple la observabilidad pedida |
| D-09 | Estado canónico en memoria, por conversación, con TTL y tope | Una sola instancia local; no hay requisito de persistencia | Base de datos o `localStorage`; fuera de alcance |
| D-10 | REST bloqueante por turno (`POST /mensajes`) con timeout total de 90 s y aborto | El cliente necesita una respuesta o un error explícito; no hay streaming | SSE/WebSocket; fuera de alcance |
| D-11 | `request_id` UUID generado por el cliente e idempotencia por solicitud | Evita duplicados ante doble envío o corte de red | Idempotencia por texto; dos mensajes iguales podrían ser legítimos |
| D-12 | Cancelar, reiniciar y eliminar invalidan por identidad y generación antes de abortar | Las respuestas tardías se descartan sin depender del tiempo | Ignorar solo en la UI; el backend conservaría contexto contaminado |
| D-13 | Montar un único `AnalystChat` en `MainLayout` | Todas las rutas existentes lo heredan sin duplicarlo ni cambiar rutas | Montarlo en cada página; riesgo de múltiples estados |
| D-14 | `react-markdown` + `remark-gfm` con `skipHtml`, lista blanca y `urlTransform` | GFM seguro, sin HTML crudo ni `rehype-raw` | `dangerouslySetInnerHTML`; prohibido |
| D-15 | Vitest + React Testing Library + jsdom | Pruebas focalizadas de UI, estados y XSS sin cambiar el stack de producción | No tener pruebas; incumple la constitución |
| D-16 | Sin persistencia del chat en navegador; recarga inicia vacío | Requisito explícito y minimiza exposición | `sessionStorage`; también persistiría datos |
| D-17 | Backend en `127.0.0.1` y frontend por proxy Vite; sin CORS `*` | Frontera de confianza local; el navegador no necesita CORS | Exponer `0.0.0.0` o CORS abierto |
| D-18 | Errores con código estable y mensaje comprensible; sin stack, rutas ni credenciales | Recuperación y soporte sin filtrar infraestructura | Devolver excepciones FastAPI sin normalizar |
| D-19 | Medir obligatoriamente los cinco umbrales PEAS; iniciar con N=3–5 y ampliar a N=10 para declarar SC-005 cumplido | Conserva Clarify y el tamaño explícito de SC-005; reporta evidencia real | Presentar un resultado parcial como aceptación |
| D-20 | Datos de fuentes ficticios o anonimizados, versionados bajo `fuentes/` | Requisito académico y de privacidad | Datos reales de pólizas o siniestros |
| D-21 | Dependencias nuevas justificadas y fijadas; lockfile de Python generado tras la compuerta de instalación | Reproducibilidad y control de cambios | Instalar versiones flotantes |

## 4. Historial de contrato OpenCode 0.2.27 (API v1; supersedido)

La siguiente descripción preserva las hipótesis de la planificación original para trazabilidad. No debe usarse para implementar ni validar. El contrato vigente está en [opencode-v2.md](./contracts/opencode-v2.md), y T001 comprobó la API v2 real.

### 4.1 Arranque y autenticación

- Servidor local: `opencode serve --hostname 127.0.0.1 --port 4096`.
- El comando `serve` no tiene `--config`; la configuración personalizada se indica con la variable `OPENCODE_CONFIG`.
- Basic Auth del servidor con `OPENCODE_SERVER_USERNAME` y `OPENCODE_SERVER_PASSWORD`; el backend envía `httpx.BasicAuth`. Las credenciales viven solo en el entorno del backend y en el proceso de OpenCode, nunca en React.
- El backend usa `OPENCODE_SERVER_URL=http://127.0.0.1:4096`.
- No se asume compatibilidad con OpenAI Chat Completions. Se usa la API HTTP nativa v1 del pin.
- El modelo y el proveedor se configuran en OpenCode, no en el repositorio. Si no hay modelo configurado, el health lo reporta y el chat devuelve un error accionable.

### 4.2 Configuración del agente

La configuración personalizada candidata se cargaría con `OPENCODE_CONFIG` y declararía:

- un agente `analista` bajo `agent` (forma v1);
- `mode: "primary"`;
- `prompt` con sustitución de archivo `{file:../prompts/sistema.md}`;
- `permission` con denegación total, cuya sintaxis y eficacia deben verificarse contra la configuración de `0.2.27`;
- sin `model` fijado, para heredar el modelo configurado por OpenCode.

La documentación oficial legacy de agentes muestra el campo `prompt` y permite referenciar un archivo; la documentación oficial v2 usa `agents` y `system`. No son nombres intercambiables. La forma exacta, `{file:...}`, precedencia de `OPENCODE_CONFIG`, herencia y eficacia del deny quedan pendientes del preflight temporal T001 contra `0.2.27`; no se registra el ejemplo como compatible antes de esa verificación. El backend valida existencia, longitud y hash antes de aceptar tráfico. El prompt no se envía como override en cada mensaje. Si no se garantiza el modo read-only, se bloquea el uso.

### 4.3 Endpoints usados

| Uso | Método y ruta | Observación |
|---|---|---|
| Preflight/health | `GET /global/health` | Devuelve `healthy` y `version`; no prueba el modelo |
| Verificar agente | `GET /agent` | Lista agentes; extraer solo el nombre y no registrar el prompt |
| Crear sesión | `POST /session` | Crear sesión efímera con título opaco; campos extra solo si los define el OpenAPI de `0.2.27` |
| Enviar mensaje | `POST /session/{id}/message` | POST síncrono; entrega la respuesta assistant en el cuerpo |
| Validar forma | Respuesta `{info, parts}` | Concatenar partes textuales y validar rol/campos contra el schema local |
| Interrumpir | `POST /session/{id}/abort` | Abortar al cancelar o vencer el deadline; validar respuesta con el OpenAPI del pin |
| Eliminar | `DELETE /session/{id}` | Limpiar sesión; status/body exactos se fijan contra el pin |

La sesión se crea con un título opaco basado en IDs, nunca con el texto del requerimiento. La correlación de `conversation_id`, `request_id` y `turn_id` se conserva en backend/Langfuse enmascarado; no se presupone que OpenCode `0.2.27` soporte metadata por sesión.

### 4.4 Forma real del mensaje assistant

La documentación oficial de API v1 describe mensajes como `{info, parts}`. Los campos exactos se verifican en el OpenAPI de `0.2.27`; el adaptador necesita identificar un mensaje assistant completo y su contenido textual antes de parsear.

- `info` con el tipo/rol assistant y los metadatos de finalización soportados;
- `parts` con contenido; solo las partes de texto se concatenan;
- error y metadatos de uso, si el pin los devuelve, se procesan sin inventar valores.

El backend valida que la respuesta pertenece al agente `analista`, que está completa según el schema v1 y que no es error. No lee ni confirma la respuesta si la cancelación o el timeout ganaron la carrera.

### 4.5 Secuencia por turno

1. El backend valida la conversación, el `request_id` y que no haya otro turno activo.
2. Construye el contexto canónico y ejecuta las cuatro herramientas MCP en paralelo.
3. Crea una sesión OpenCode efímera con el agente `analista` y permisos de denegación.
4. Envía el prompt construido por `POST /session/{id}/message`, que espera la respuesta; el timeout HTTP está limitado por el deadline total.
5. Valida la respuesta assistant devuelta y parsea el JSON.
6. Si el JSON es inválido, hace **un** intento de reparación en la misma sesión efímera del turno, con un segundo prompt acotado y el mismo deadline; si sigue inválido, devuelve error controlado.
7. Actualiza el contexto canónico solo si el turno sigue vigente.
8. Elimina la sesión OpenCode en `finally`, incluso en error, cancelación o timeout.

No se hace sondeo ni se usa endpoint `wait`: el POST v1 entrega la respuesta. Un timeout, respuesta incompleta o error del servidor se trata como fallo controlado y no como respuesta del agente.

### 4.6 Errores y compatibilidad

- `401/403`: fallo de autenticación de OpenCode; el backend devuelve un error accionable sin credenciales.
- `404` al abortar/eliminar: la sesión ya no existe; se trata como cancelada/descartada o limpia.
- `409`: conflicto de ejecución; no se reintenta a ciegas.
- `503`: servidor no disponible.
- El endpoint v2 `SessionV2.wait()` no se usa; el issue oficial de respuesta 503 se cita solo como evidencia de API v2. Para el pin `0.2.27`, el POST de mensaje es síncrono y la compuerta compara las rutas/cuerpos con `GET /doc`.
- El backend comprueba que la versión reportada sea `0.2.27`. Una versión distinta bloquea el envío con `OPENCODE_INCOMPATIBLE` hasta actualizar/validar el contrato.

## 5. Prompt, hash y recarga (actualizado a v2)

La configuración vigente es `opencode.jsonc`, con prompt externo y permisos deny-all, sin modelo/provider fijo. FastAPI valida el `OPENCODE_MODEL_ID` opcional contra la lista v2 y exige `providerID=opencode`; si no se fija, acepta el default solo cuando pertenece a ese provider. El backend valida versión/hash del prompt y requiere reinicio ante cambios del archivo.

- Ruta única: `agentes/analista/prompts/sistema.md`.
- El backend carga el archivo al iniciar, valida que no esté vacío y calcula SHA-256; extrae `Versión editorial` si existe.
- `opencode.jsonc` referencia el archivo canónico mediante `{file:./agentes/analista/prompts/sistema.md}`; T001/T007 confirmó carga y coincidencia exacta. Python conserva solo snapshot, versión y hash, no una copia del prompt.
- El health devuelve `prompt_version`, `prompt_hash` y `restart_required`; no devuelve el texto.
- Si el archivo desaparece o queda vacío: health `unavailable`, envíos `503 PROMPT_INVALID`.
- Si el hash local difiere del snapshot backend al iniciar: health `degraded` con `restart_required: true` y envíos `503 PROMPT_RESTART_REQUIRED`; reiniciar el backend después de que el watcher v2 haya recargado el agente. No se crea otro servidor.
- El prompt define el JSON de salida y prohíbe `fuentes_consultadas`; el backend las calcula.

## 6. LangChain y orquestación

Se usará `langchain==1.4.7` con `langchain-core`/`langgraph` resueltos y fijados en el lockfile. La cadena efectiva será:

1. `ChatPromptTemplate`/plantilla de prompt de usuario para inyectar el estado canónico, el mensaje actual, los resultados MCP y las limitaciones. El system prompt sigue en OpenCode.
2. `RunnableParallel` con las cuatro herramientas MCP, cada una con timeout y captura de error independiente.
3. `PydanticOutputParser` sobre el esquema `AgentOutput` (campos extra prohibidos).
4. Una llamada HTTP a OpenCode dentro de un `RunnableLambda`/adaptador, no un chat model falso.
5. Una reparación única si el parseo falla, con el error de validación y la salida inválida acotada, enviada como segundo prompt en la misma sesión y con el deadline total compartido.
6. Un `RunnableLambda` final que normaliza preguntas, readiness y fuentes.

`MCPAdapter` de `langchain.mcp` es beta en 1.4.7; se usa con un adaptador propio y pruebas de contrato. En runtime el orquestador abre un adaptador stdio por turno usando `agentes/analista/mcp/server.py`, lista exactamente las cuatro herramientas y lo cierra al terminar. En pruebas se puede pasar un servidor FastMCP en proceso.

No se usa `create_agent` ni un modelo de chat simulado: el valor de LangChain está en la construcción del prompt, la orquestación paralela, los timeouts, el parseo tipado y la reparación. La llamada al modelo es siempre HTTP contra OpenCode.

## 7. MCP: cuatro fuentes reales de solo lectura

- Servidor FastMCP (`fastmcp==4.1.4`, SDK `mcp==2.3.0`) por stdio; sin red, sin shell, sin escritura.
- Solo cuatro herramientas: `consultar_glosario`, `buscar_hu_similares`, `consultar_estandares`, `aplicar_checklist_vacios`.
- Datos ficticios/anonimizados en `agentes/analista/fuentes/`, cargados en modo lectura.
- Entrada común: `consulta` (1–4.000 caracteres) y `limite` (1–5); la consulta se construye con el mensaje actual y un resumen del estado canónico, no con secretos.
- Salida tipada y determinista; `total` debe coincidir con la longitud de la lista.
- Cada llamada tiene timeout de 5 s y se ejecuta en paralelo con las otras. Un fallo no cancela las demás.
- El backend registra `fuentes_consultadas` solo para llamadas exitosas (incluidas las que devuelven cero resultados). Las fallidas o no ejecutadas se declaran en `limitaciones`.
- El servidor MCP no expone herramientas genéricas de archivo, shell, red o escritura. La allowlist está en Python y en la configuración de OpenCode; el prompt no es la única defensa.
- El subpaquete se llama `agentes.analista.mcp` para cumplir la estructura de la constitución y **no** se ejecuta como `python -m mcp.server` desde `agentes/analista`, porque eso haría sombra al paquete oficial `mcp`. Se ejecuta como `python -m agentes.analista.mcp.server` desde la raíz, con `PYTHONPATH` explícito.
- Si el servidor MCP no arranca, health `unavailable` y envíos `503 MCP_UNAVAILABLE`. Si una herramienta individual falla en un turno, se continúa con las disponibles y se declara la limitación.

## 8. Langfuse v5

- Cliente `Langfuse` inicializado solo si `LANGFUSE_PUBLIC_KEY` y `LANGFUSE_SECRET_KEY` están presentes; `LANGFUSE_BASE_URL` por defecto `https://us.cloud.langfuse.com` (configurable).
- `propagate_attributes(session_id=conversation_id, user_id="analista-local", metadata={request_id, turn_id, prompt_version, ...})` para correlación. `user_id` es un pseudónimo fijo, no un dato personal.
- `CallbackHandler` de `langfuse.langchain` en la cadena LangChain.
- Span raíz del turno con duración total; spans hijos por herramienta MCP (nombre, éxito, duración) y por llamada OpenCode (modelo, `finish`, duración, error code). No se adjuntan contenido, tokens ni coste a las trazas.
- `mask_otel_spans` se configura en el cliente para eliminar o reemplazar atributos de contenido: `gen_ai.prompt.*`, `gen_ai.completion.*`, `gen_ai.input.*`, `gen_ai.output.*`, `langfuse.observation.input`, `langfuse.observation.output`, `langfuse.trace.input`, `langfuse.trace.output` y mensajes/body equivalentes. Se conservan IDs, modelo, herramienta, duración, estado y códigos de error.
- El hook es síncrono y determinista; si falla, se registra localmente y no se propaga. Los fallos de exportación no bloquean la respuesta.
- Modo deshabilitado: sin claves, no se inicializa el cliente, health `degraded` con `langfuse.status = "disabled"`, el chat funciona y la UI muestra un aviso de diagnóstico limitado.
- El navegador nunca recibe claves, endpoint OTLP, trace ID interno ni prompt. El backend no devuelve `trace_id`.
- Se hace `flush` al apagar y, si se usa por turno, en segundo plano con timeout; nunca se espera la red para responder al usuario.

## 9. Markdown seguro

- `react-markdown@10.1.0` y `remark-gfm@4.0.1`; no se instala `rehype-raw`.
- `skipHtml` activo: el HTML crudo no se interpreta. Además, `allowedElements` limita a encabezados, párrafos, listas, tablas GFM, énfasis, código, blockquote, enlaces y separadores; se excluyen `img`, `iframe`, `script`, `style`, `form` y elementos interactivos. Si GFM genera un `input` de task list, se renderiza como checkbox deshabilitado, sin eventos ni edición.
- `urlTransform` solo permite `http:`, `https:` y anclas `#`; `javascript:`, `data:`, `blob:`, `file:` y esquemas desconocidos se reemplazan por cadena vacía. Los enlaces externos usan `rel="noopener noreferrer"`; no se cargan imágenes remotas.
- El mensaje del usuario se muestra como texto plano; solo la respuesta del agente pasa por el renderer.
- Se prueban HTML anidado, `javascript:`, `data:`, imágenes remotas, eventos, codificación ofuscada y GFM válido. El objetivo es cero ejecución y cero HTML arbitrario, no “sanitizar” con una librería adicional no aprobada.

## 10. Estado, idempotencia y descarte tardío

- Estado canónico en Python: conversación, turnos completados, análisis vigente, preguntas, fuentes, prompt/hash y TTL. No se guarda en el navegador.
- Cada turno usa una sesión OpenCode nueva. El prompt incluye el estado canónico y los resultados MCP; no se reutiliza una sesión que pudo quedar contaminada.
- `request_id` UUID del cliente; el servidor guarda el hash del texto para detectar reutilización con otro contenido. Un `request_id` completado devuelve la respuesta cacheada; uno activo devuelve `409 TURN_IN_PROGRESS`; uno con texto distinto devuelve `409 REQUEST_ID_CONFLICT`.
- Una sola solicitud en vuelo por conversación. El servidor no encola; la segunda se rechaza.
- Cancelar: se marca el turno como cancelado, se quita de `active_turn`, se solicita `POST /session/{id}/abort` y se elimina la sesión. El turno no entra al contexto. El `POST /mensajes` original devuelve `409 TURN_CANCELLED`; la UI lo ignora si ya canceló.
- Timeout: deadline total de 90 s desde el inicio del turno. Al vencer, se marca timeout, se aborta/interrumpe, se elimina la sesión y se devuelve `504 TURN_TIMEOUT`; el resultado no entra al contexto.
- Reiniciar: invalida la generación anterior y elimina la conversación del store antes de abortar; crea una conversación nueva con ID nuevo. El panel permanece abierto.
- Eliminar: invalida y elimina la conversación antes de abortar; `DELETE` es idempotente (`204` incluso si ya no existe); la UI cierra el panel.
- Descarte tardío: la ruta de envío comprueba `generation`, `active_turn` e identidad de turno bajo lock antes de actualizar contexto; la UI comprueba `requestEpoch` y `request_id` antes de insertar. Ganar la carrera de cancelación/reinicio impide la actualización canónica aunque OpenCode ya haya generado texto.
- TTL de inactividad 30 min y tope de 32 conversaciones por proceso; limpieza periódica. El backend es una sola instancia; un reinicio invalida sesiones.

## 11. Capa frontend

- Un único componente `AnalystChat` montado al final de `MainLayout`; el launcher es fijo abajo a la derecha, con `aria-expanded`/`aria-controls`.
- El panel se mantiene montado al cerrarse para conservar mensajes/estado; cerrar no aborta. Nuevo chat limpia y mantiene abierto; Eliminar confirma y cierra.
- Estado explícito: `idle`, `sending`, `cancelling`, `error`, `confirm-delete`, `deleting`, `resetting`; el estado de salud es independiente.
- `requestEpoch` + `activeRequestId` + `AbortController` para descartar respuestas tardías. Cancelar/Nuevo/Eliminar incrementan la época inmediatamente.
- Timer de cliente basado en `timeout_seconds` del health (90 por defecto) con margen de seguridad; al vencer llama a cancelar y descarta la respuesta.
- El indicador de procesamiento se muestra al enviar (antes de la red), no cuando llega la respuesta.
- Markdown seguro, tarjetas de análisis, preguntas, fuentes y readiness; las categorías vacías se muestran con cero, no se omiten.
- Auto-scroll solo si el usuario está cerca del final; si no, se muestra un botón “Ir al último mensaje”.
- Accesibilidad: etiquetas, foco al abrir, retorno al launcher, Escape, `role="dialog"` no modal, `aria-live` para estado/mensajes, `role="alert"` para errores, contraste y `prefers-reduced-motion`.
- Responsive: panel con ancho máximo, altura limitada para no cubrir el header; en móvil ocupa el ancho disponible con márgenes y `safe-area-inset-bottom`; sin overflow horizontal.
- Sin secretos, sin `localStorage`/`sessionStorage` del chat, sin contacto directo a OpenCode/Langfuse. La API se llama por `/api/analista` (proxy Vite).

## 12. Pruebas y dependencias

### 12.1 Backend

- `pytest==9.1.1` + `pytest-asyncio==1.4.1`; `httpx.MockTransport` para el cliente OpenCode, sin una dependencia adicional de mocking HTTP.
- Pruebas de contrato REST, validación, errores, concurrencia, cancelación, reset, timeout, idempotencia, MCP, parseo/reparación, prompt/hash, health, observabilidad y secretos.
- La integración real se prueba manualmente con OpenCode, MCP y Langfuse; las pruebas automatizadas no fingen una respuesta del agente en runtime.

### 12.2 Frontend

- `vitest@3.2.7` (compatible con Vite 5), `jsdom@26.1.0`, `@testing-library/react@16.3.3`, `@testing-library/user-event@14.6.8`, `@testing-library/jest-dom@6.9.1` y `@testing-library/dom@10.4.2`.
- `vitest.config.js` con `environment: "jsdom"` y setup de jest-dom; scripts `test:run` y `test:watch`.
- Pruebas de launcher/panel, foco, cierre, nuevo/eliminar, envío, cancelación, timeout, reintento, doble envío, respuesta tardía, recarga vacía, Markdown/XSS, estructura, salud, auto-scroll y no persistencia.
- No se introduce Playwright; la verificación responsive/visual y el flujo real se hacen manualmente y se registran como evidencia.

### 12.3 Versiones candidatas

| Paquete | Versión | Rol | Compuerta |
|---|---:|---|---|
| Python | 3.12.10 | Runtime | Instalación e importación en Fase 0 |
| FastAPI | 0.162.0 | API | Smoke test con Starlette 1.x |
| Uvicorn | 0.54.0 | Servidor ASGI | Smoke test |
| httpx | 0.28.1 | Cliente OpenCode | Smoke test |
| Pydantic | 2.14.1 | Esquemas | Smoke test |
| pydantic-settings | 2.16.1 | Configuración/.env | Smoke test |
| LangChain | 1.4.7 | Orquestación/parseo | Importar `MCPAdapter` |
| FastMCP | 4.1.4 | Servidor/cliente MCP | Arranque stdio |
| MCP | 2.3.0 | SDK MCP | Tool listing |
| Langfuse | 5.0.4 | Trazas | Inicialización, masking y modo deshabilitado |
| pytest | 9.1.1 | Pruebas backend | Ejecutar suite |
| pytest-asyncio | 1.4.1 | Pruebas async | Ejecutar suite |
| react-markdown | 10.1.0 | Markdown | Build y XSS |
| remark-gfm | 4.0.1 | GFM | Build y tablas |
| Vitest | 3.2.7 | Pruebas frontend | Vite 5 |
| jsdom | 26.1.0 | DOM de pruebas | Node ≥18 |
| RTL | 16.3.3 | Pruebas React | React 18 |
| user-event | 14.6.8 | Interacción | RTL |
| jest-dom | 6.9.1 | Matchers | Vitest |
| @testing-library/dom | 10.4.2 | Peer de RTL | Instalación |

El registro previo de `pip install --dry-run` resolvió a Starlette 1.10.0 y `langchain-core` 1.7.0 sin conflicto declarado. Esto es solo evidencia de resolución candidata, no de API/importación/ejecución. T002 debe volver a resolver e instalar las versiones candidatas en un entorno desechable, comprobar las APIs de composición/parser, el MCP stdio real y el masking/degradación de Langfuse, y registrar resultados. El lockfile se genera después de aprobar esa compuerta; un fallo obliga a revisar versiones y diseño antes de escribir código dependiente.

## 13. Inconsistencias y cuestiones abiertas

1. **SC-005 vs aclaración**: la evaluación inicial usa 3–5 casos según Clarify; para cerrar SC-005 se requieren 10, como especifica ese criterio. Con N < 10, SC-005 queda `PARTIAL`.
2. **PEAS pendiente de evidencia**: 80 %, 70 %, −50 %, 4/5 y cero invenciones son criterios obligatorios de aceptación por Clarify. No hay resultados medidos en esta fase; `NOT_MEASURED` no cuenta como aprobación.
3. **OpenCode**: T001 verificó OpenCode `2.0.27`/API v2 y contratos con el proceso existente. Los nueve modelos con precio cero consultados/probados no produjeron respuesta (ocho 429 y uno no disponible); no se probó un modelo de pago. La generación a través del proveedor autorizado queda pendiente.
4. **Integraciones LangChain/MCP/Langfuse**: T002 es la compuerta técnica previa al código dependiente. Verifica el `MCPAdapter`/APIs elegidas, el servidor stdio y masking; cualquier incompatibilidad exige revisar el contrato antes de continuar.
5. **Modelo/proveedor de OpenCode**: no se versiona ninguna credencial ni se asume un modelo. Si el entorno local no tiene modelo, el health debe indicarlo y el chat no debe fingir una respuesta.
6. **Langfuse local**: puede no estar configurado. El modo deshabilitado es parte de la aceptación, no un fallo del análisis.
7. **Prompt y reinicio**: el watcher v2 recarga el agente de proyecto; el backend detecta hash desactualizado y bloquea envíos hasta reiniciarse.
8. **Nombre del subpaquete `mcp`**: se evita la colisión con el SDK oficial mediante el paquete `agentes.analista.mcp` y el arranque desde la raíz.
9. **Sin streaming**: el requisito es una respuesta completa con timeout total; no se implementa token a token.
10. **Una instancia y retención**: no hay persistencia ni escalado; una recarga pierde el ID del lado del cliente, pero el registro huérfano permanece en memoria del servidor hasta borrado, TTL de 30 minutos desde última actividad, expulsión por capacidad o reinicio del proceso. No existe recuperación por una pestaña recargada y no se usa almacenamiento de navegador.

## 14. Referencias

- `specs/002-chat-agente-analista/spec.md`
- `.specify/memory/constitution.md` v1.0.0
- `agentes/analista/prompts/sistema.md`
- [OpenCode API v2 y OpenAPI](https://dev.opencode.ai/v2/docs/api), [configuración](https://dev.opencode.ai/v2/docs/config/), [agentes](https://dev.opencode.ai/v2/docs/agents/) y [permisos](https://dev.opencode.ai/v2/docs/permissions/).
- [Basic Auth de OpenCode Server](https://dev.opencode.ai/docs/server/).
- LangChain 1.4.7, `langchain.mcp` y FastMCP 4.1.4.
- Langfuse Python v5, `CallbackHandler` y `mask_otel_spans`.
- React Markdown 10 y Remark GFM 4.
- [PyPI LangChain 1.4.7](https://pypi.org/project/langchain/1.4.7/), [PyPI FastMCP 4.1.4](https://pypi.org/project/fastmcp/4.1.4/), [PyPI MCP 2.3.0](https://pypi.org/project/mcp/2.3.0/) y [PyPI Langfuse 5.0.4](https://pypi.org/project/langfuse/5.0.4/); `pip --dry-run` para la resolución local.

La prueba completa React→FastAPI→MCP→LangChain→OpenCode sigue pendiente en T042. T001 registró históricamente ciclo de vida estructural y una generación con Ollama; ninguna de esas comprobaciones confirma generación mediante `opencode`. Las métricas PEAS quedan pendientes.

## Evaluación de OpenCode 2.1.2 (2026-10-27)

- Se instaló `@opencode/cli@2.1.2` con `npm install --prefix %TEMP%\opencode-2.1.2-isolated`; no se actualizó la instalación oficial ni se modificaron credenciales globales.
- El servidor inició desde un directorio/profil temporal, con un password Basic de prueba de alcance de proceso. `GET /api/info` reportó `2.1.2`; `/openapi.json` incluyó `Session.StructuredError.retryAfterMs` (`integer`, `minimum: 0`).
- Se verificaron Basic Auth, `/api/agent`, `/api/provider`, `/api/model`, creación de sesión, deny-all, `GET /message`, `/interrupt` sin generación (respuesta `interrupted: false`), `DELETE /session` y posterior `404`. No se envió `POST /prompt`, no hubo generación ni llamadas a proveedor.
- El error `provider.free-limit` y `retryAfterMs` se agregaron en 2.1.2 para el límite gratuito OpenCode cuando el error de Console incluye `FreeUsageLimitError`. OpenCode da una duración; se ancla a `time.completed` del mensaje para reducir el desfase del sondeo, y FastAPI la publica como `retry_at`.
- 2.1.0 cambia nombres de replay (`state`/`providerState` a `native`), forma de replay de herramientas, metadatos de credenciales y datos de compactación. Los campos consumidos por este backend permanecen en el contrato de mensaje/sesión observado; no usa los campos renombrados. La creación y limpieza de sesión se comprobaron sin generación. El prompt de generación y cancelar una generación activa quedan sin validar por la restricción de no llamar generación.
- Resultado: 2.1.2 es compatible para los endpoints y ciclos sin generación que usa el backend. El backend admite explícitamente 2.0.27 y 2.1.2; versiones no probadas se rechazan. El dato de recuperación es automático cuando `retryAfterMs` está presente; sin esa propiedad se conserva el estado desconocido. La alternativa de entrada manual no se implementó porque la API sí expone la propiedad.

La evidencia detallada y comandos de inspección están en [evidence/opencode-2.1.2-compatibility.md](evidence/opencode-2.1.2-compatibility.md).

## 15. Resultados ejecutados de T001/T002 (2026-10-26)

- **T001 — GENERACIÓN ABIERTA:** la primera propuesta fijaba `0.2.27`/v1; el binario aislado no abrió el puerto. El servidor manual se verificó después, pero la generación exitosa histórica fue con Ollama. El estado vigente y la clasificación por proveedor están en `evidence/preflight-results.md`.
- **T002 — PASS:** en Python 3.12.10 temporal se resolvieron e importaron LangChain 1.4.7, FastMCP 4.1.4, MCP 2.3.0 y Langfuse 5.0.4; composición/parser, MCP stdio + `MCPAdapter`, esquema/resultado/rechazo de entradas y masking sintético/no-credenciales pasaron. `langchain.mcp` es beta. Ver versiones, comandos y límites en `evidence/preflight-results.md`.
- Las dependencias instaladas de T002 y el CLI de T001 quedaron bajo `%TEMP%`; no se instalaron dependencias en el proyecto para ejecutar las compuertas.
- **Reanudación inicial T001 — HISTORIAL:** `/global/health` y `/doc` entregaron HTML y las primeras credenciales locales fueron rechazadas. Después se ingresó una clave temporal mediante `.env` local y se completaron las verificaciones estructurales; ver la clasificación en [preflight-results.md](evidence/preflight-results.md).
- **T001 — ABIERTA PARA `opencode`:** el servidor/API v2 y ciclo de vida estructural se verificaron históricamente; Ollama produjo la única generación exitosa histórica. Ninguno de los nueve modelos con costo cero produjo respuesta (ocho 429 y uno no disponible). T008 se verifica por pruebas aisladas y no depende de cuota.
