# Data Model — Chat flotante con Agente Analista

**Feature**: `002-chat-agente-analista`  
**Date**: 2026-10-26  
**Scope**: Modelo lógico del estado en memoria, contratos de datos y reglas de validación. No define código de implementación.

## 1. Convenciones

| Convención | Regla |
|---|---|
| Identificadores | UUID v4 opacos para conversación, solicitud y turno; las preguntas reciben un identificador opaco generado por el backend |
| Fechas | UTC en ISO 8601 con zona; las duraciones se calculan con reloj monotónico y se expresan en milisegundos |
| Texto | UTF-8; el límite de 4.000 se cuenta en puntos de código Unicode, no en bytes |
| Persistencia | Solo memoria del proceso; no hay base de datos, archivo de conversación, `localStorage` ni `sessionStorage` del chat |
| Retención | TTL inicial de 30 minutos desde `last_activity_at`; eliminación explícita, expulsión al alcanzar capacidad y apagado/reinicio del backend eliminan antes el registro |
| Contenido sensible | El texto del usuario, el prompt y los resultados de fuentes no se registran en logs ni en trazas |
| Fuentes | Solo datos ficticios o anonimizados bajo `agentes/analista/fuentes/` |
| Autoridad | El backend es la autoridad del contexto; el navegador solo mantiene la vista de la pestaña actual |

## 2. Entidades

### 2.1 Conversation

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---:|---|
| `conversation_id` | UUID v4 | Sí | Generado por el backend; nunca es el ID de la sesión OpenCode |
| `created_at` | timestamp UTC | Sí | Inmutable |
| `last_activity_at` | timestamp UTC | Sí | Se actualiza con cada turno aceptado, cancelado o completado |
| `expires_at` | timestamp UTC | Sí | `last_activity_at + TTL`; TTL inicial 30 min |
| `generation` | entero | Sí | Incrementa al reiniciar/eliminar; invalida tareas y respuestas antiguas |
| `status` | enum | Sí | `activa`, `procesando`, `reemplazada`, `eliminada`, `expirada` |
| `active_turn` | Turn o nulo | No | Como máximo uno; se limpia al completar, fallar, cancelar o expirar |
| `context_turns` | lista de CompletedTurn | Sí | Solo turnos completados y vigentes; alimenta el contexto del agente |
| `previous_summary` | string | Si | Resumen canonico de analisis y preguntas; maximo 2.000 caracteres |
| `analysis` | Analysis | No | Último análisis canónico; vacío al crear |
| `questions` | lista de Question | Sí | Estado consolidado, con IDs estables |
| `request_cache` | mapa `request_id → TurnRecord` | Sí | Idempotencia y detección de conflicto de clave |
| `last_sources` | lista de SourceConsultation | No | Últimas fuentes realmente consultadas; se usa para contexto y respuesta |
| `prompt_version` | string | Sí | Versión editorial del prompt cargada al iniciar |
| `prompt_hash` | string | Sí | SHA-256 del prompt cargado al iniciar |
| `turns_count` | entero | Sí | Contador de turnos aceptados, para diagnóstico (no se expone como métrica inventada) |

Los únicos estados de servidor son `activa`, `procesando`, `reemplazada`, `eliminada` y `expirada`. `abierta`/`cerrada` describe únicamente la visibilidad del panel y nunca es un estado de conversación. `reemplazada` identifica la conversación anterior a un reinicio; `eliminada` corresponde a una solicitud de borrado; `expirada` indica que venció el TTL.

Al recargar, el navegador no conserva el `conversation_id` ni los mensajes. El registro previo queda temporalmente huérfano en la memoria del backend, inaccesible para la pestaña nueva, hasta su borrado, TTL, expulsión por capacidad o reinicio del proceso. El cliente intenta abortar el turno activo al detectar la descarga, pero esa señal es de mejor esfuerzo; el TTL y la invalidación de generación son la limpieza garantizada. Esta política no habilita almacenamiento del chat en el navegador.

El límite inicial es de 32 conversaciones. Al crear una nueva con el límite alcanzado, el servidor
expulsa la conversación sin turno activo más antigua (menor `last_activity_at`; desempate por
`created_at` y luego `conversation_id`). Si las 32 tienen turnos activos, rechaza la creación con
`503 CAPACITY_EXCEEDED`; nunca expulsa un turno en curso.

**Invariantes**

- `active_turn` es nulo o uno; nunca hay dos turnos activos.
- Si `status = procesando`, `active_turn` no es nulo.
- Un turno cancelado, fallido o expirado nunca aparece en `context_turns`.
- `generation` solo aumenta; una tarea con una generación anterior no puede escribir.
- `expires_at >= last_activity_at`.
- El ID de sesión OpenCode no se guarda en la conversación ni se expone; solo vive en el `Turn` mientras está activo y en el cliente interno.

### 2.2 Turn

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---:|---|
| `turn_id` | UUID v4 | Sí | Generado por el backend por intento |
| `request_id` | UUID v4 | Sí | Generado por el cliente; clave de idempotencia |
| `conversation_id` | UUID v4 | Sí | Referencia lógica; no se expone el objeto completo |
| `message` | string | Sí | 1–4.000 puntos de código; no vacío ni solo espacios |
| `message_hash` | string | Sí | SHA-256 del mensaje normalizado para detectar reutilización de `request_id` |
| `status` | enum | Sí | `enviado`, `procesando`, `completado`, `fallido`, `cancelado`, `expirado`, `descartado` |
| `created_at` | timestamp UTC | Sí | Inicio del turno |
| `started_at` | timestamp UTC | No | Cuando empieza el trabajo efectivo |
| `completed_at` | timestamp UTC | No | Fin, éxito o error |
| `duration_ms` | entero | No | Medido; solo se publica si el turno terminó |
| `opencode_session_id` | string | No | Interno; nunca se devuelve al navegador |
| `trace_id` | string | No | Interno de Langfuse; nunca se devuelve al navegador |
| `tool_results` | lista de ToolExecution | Sí | Resultado real de cada herramienta intentada |
| `analysis` | Analysis | No | Solo en turnos completados |
| `questions` | lista de Question | No | Solo en turnos completados |
| `response` | AgentTurnResponse | No | Respuesta validada y cacheada |
| `error` | ErrorEnvelope | No | Error controlado del turno |
| `finish_reason` | string | No | Valor `finish` del mensaje assistant v2 en `GET /api/session/{id}/message`; solo se conserva tras validar `time.completed` |
| `model` | string | No | Proveedor/modelo reportado por OpenCode; se registra en traza si está disponible |
| `repair_attempts` | entero | Sí | 0 o 1; nunca más de una reparación |
| `cancel_requested_at` | timestamp UTC | No | Marca la intención de cancelar antes del aborto |
| `invalidated_by_generation` | entero | No | Generación que descartó el turno |

**Estados y transiciones**

```text
enviado ──► procesando ──► completado
   │            │
   │            ├──► fallido
   │            ├──► cancelado
   │            └──► expirado (timeout)
   │
   └──► descartado (reinicio/eliminación antes de empezar o durante el trabajo)
```

- `completado`: salida validada y comprometida en el contexto; solo entonces se devuelve 200.
- `fallido`: error controlado; no contamina el contexto.
- `cancelado`: el usuario canceló; no contamina el contexto; el mensaje visible puede conservarse con marca de cancelado.
- `expirado`: se agotó el deadline total de 90 s; no contamina; se devuelve 504.
- `descartado`: reinicio/eliminación invalidó el turno; la respuesta se ignora por identidad, aunque OpenCode la haya generado.
- `enviado` es un estado transitorio bajo lock; no debe ser visible al cliente durante mucho tiempo.

### 2.3 Analysis

| Campo | Tipo | Reglas |
|---|---|---|
| `conocida` | lista de string | Hechos confirmados; máximo 100; cada uno 1–1.000 caracteres |
| `faltante` | lista de string | Vacíos pendientes; máximo 100; cada uno 1–1.000 caracteres |
| `supuesta` | lista de string | Supuestos explícitos; máximo 100; cada uno 1–1.000 caracteres |
| `ambigua` | lista de string | Ambigüedades; máximo 100; cada uno 1–1.000 caracteres |

Todas las listas son obligatorias. Una lista sin elementos se representa como `[]` y la UI muestra “0” o “Sin elementos”; nunca se omite la categoría.

**Invariantes**

- No se permiten cadenas vacías dentro de las listas.
- Se eliminan duplicados exactos después de normalizar espacios; si el modelo devuelve duplicados, se conserva el primero.
- `listo_para_redactor = true` exige `faltante`, `supuesta` y `ambigua` vacías y cero preguntas pendientes. Es una compuerta más estricta que “no quedan vacíos relevantes”, deliberadamente conservadora.
- Si el modelo declara `listo_para_redactor = true` pero la compuerta calculada es falsa, se intenta una reparación; si persiste, se rechaza la salida.
- `listo_para_redactor` no autoriza redactar ni aprobar una HU; solo indica que el análisis puede pasar al Redactor-Revisor.

### 2.4 Question

| Campo | Tipo | Reglas |
|---|---|---|
| `question_id` | string opaco | Generado por el backend; estable entre turnos |
| `categoria` | enum | `Reglas de negocio`, `Datos requeridos`, `Validaciones`, `Excepciones`, `Comportamiento esperado` |
| `pregunta` | string | 1–500 caracteres; concreta y no redundante |
| `estado` | enum | `pendiente`, `respondida` |
| `created_turn_id` | UUID | Turno donde apareció |
| `updated_turn_id` | UUID | Último turno que la actualizó |

**Fusión de preguntas**

1. Normalizar el texto para comparar: minúsculas, espacios colapsados, sin puntuación final.
2. Para cada pregunta existente, buscar una coincidencia normalizada en la salida del modelo.
3. Si coincide, conservar `question_id` y `created_turn_id`, actualizar categoría/estado y `updated_turn_id`.
4. Si una pregunta existente estaba `respondida` y el modelo la omite o la devuelve pendiente sin evidencia nueva, conservar `respondida`. Una reapertura requiere una contradicción explícita; si el modelo la intenta sin evidencia, se mantiene el estado anterior.
5. Si no coincide y estaba `pendiente`, conservarla como pendiente; el modelo no puede hacerla desaparecer por omisión.
6. Añadir preguntas nuevas con ID nuevo y `estado` validado.
7. Eliminar duplicados normalizados; conservar la primera.
8. Si el total supera 50, rechazar la salida con `AGENT_OUTPUT_INVALID`; no se recortan preguntas silenciosamente.
9. Una pregunta `respondida` permanece visible en la vista y en el contexto como historial; no se vuelve a preguntar.

### 2.5 ToolExecution y SourceConsultation

| Campo | Tipo | Reglas |
|---|---|---|
| `tool_name` | enum | `consultar_glosario`, `buscar_hu_similares`, `consultar_estandares`, `aplicar_checklist_vacios` |
| `status` | enum | `ok`, `error`, `timeout`, `skipped` |
| `result_count` | entero | Solo para `ok`; puede ser 0 |
| `duration_ms` | entero | Medido por el backend |
| `error_code` | string | Código controlado si falló; no contiene detalles internos |
| `result_digest` | string | Hash corto del resultado para correlación; no se envía al navegador |

**Regla de fuentes**

- `fuentes_consultadas` de la respuesta se deriva exclusivamente de `ToolExecution.status = ok`.
- Una consulta exitosa con cero resultados sí cuenta como fuente consultada; la UI muestra “0 resultados”.
- `error`, `timeout` y `skipped` no aparecen como fuentes; se resumen en `limitaciones`.
- El agente no puede añadir fuentes; si el modelo incluye un campo de fuentes, el esquema lo rechaza (campos extra prohibidos).

### 2.6 AgentTurnResponse

| Campo | Tipo | Reglas |
|---|---|---|
| `conversation_id` | UUID | ID vigente |
| `request_id` | UUID | El del cliente |
| `turn_id` | UUID | El del servidor |
| `estado` | enum | `completado` en respuestas exitosas |
| `respuesta_markdown` | string | 1–50.000 caracteres; Markdown seguro |
| `analisis` | Analysis | Cuatro listas |
| `preguntas` | lista de Question | Máximo 50 |
| `fuentes_consultadas` | lista de SourceConsultation | Máximo 4; derivada de ejecuciones reales |
| `listo_para_redactor` | boolean | Debe coincidir con la compuerta calculada |
| `limitaciones` | lista de string | Máximo 10; cada una 1–300 caracteres; fallos/omisiones de fuentes y supuestos relevantes |
| `duracion_ms` | entero | Medido desde el inicio del turno hasta la respuesta; no inventado |
| `prompt_version` | string | Versión editorial cargada |

No se incluyen `trace_id`, ID de sesión OpenCode, coste, tokens ni rutas internas. Los tokens/coste, si se midieron, quedan en la traza interna.

### 2.7 HealthSnapshot

| Campo | Tipo | Reglas |
|---|---|---|
| `status` | enum | `ready`, `degraded`, `unavailable` |
| `checked_at` | timestamp UTC | Momento de la comprobación |
| `backend_version` | string | Versión del servicio |
| `timeout_seconds` | entero | 90 por defecto |
| `message_limit` | entero | 4.000 por defecto |
| `prompt_version` | string | Versión editorial |
| `prompt_hash` | string | SHA-256; no revela contenido |
| `restart_required` | boolean | Verdadero si el prompt cambió después de cargar |
| `checks.opencode` | objeto | `status`, `version`, `agent`; no credenciales |
| `checks.mcp` | objeto | `status`, `tools` disponibles; no rutas |
| `checks.langfuse` | objeto | `status`: `ok`, `degraded`, `disabled`, `unavailable` |

**Semántica**

- `ready`: OpenCode responde, versión/agente correctos, MCP con las cuatro herramientas, prompt válido y sin desincronización; Langfuse activo y sano.
- `degraded`: el chat puede operar, pero hay una limitación: Langfuse deshabilitado/caído, una herramienta MCP individual caída o una fuente con error. La UI lo avisa y no dice “en línea”.
- `unavailable`: no se puede garantizar el flujo real: OpenCode caído/autenticación fallida/versión incompatible, MCP no arranca, prompt ausente o reinicio requerido. El envío se bloquea con error controlado.
- `GET /health` no crea sesiones ni llama al modelo; solo comprueba dependencias y configuración.

### 2.8 ErrorEnvelope

| Campo | Tipo | Reglas |
|---|---|---|
| `error.code` | enum | Código estable de la tabla de errores |
| `error.message` | string | Mensaje comprensible en español; sin stack, rutas ni secretos |
| `error.retryable` | boolean | Indica si reintentar tiene sentido |
| `error.request_id` | UUID | Opcional; si el cliente lo envió |
| `error.field` | string | Opcional; solo para validación de entrada |
| `error.issues` | lista | Opcional; campo/mensaje, sin valores sensibles |

El cliente mapea el código a acciones: reintentar con la misma identidad (fallo incierto), reintentar con nueva identidad (error terminal), cancelar, nuevo chat o corregir entrada.

### 2.9 EvaluationRecord (PEAS)

| Campo | Tipo | Reglas |
|---|---|---|
| `evaluation_id` | string | Identificador del informe |
| `corpus_id` | string | Conjunto anonimizado usado |
| `sample_size` | entero | N real; evaluación inicial 3–5; SC-005 solo cumple con N=10 |
| `prompt_version` / `prompt_hash` | string | Versión evaluada |
| `commit` | string | Commit de la implementación evaluada |
| `metric` | enum | `M1_vacios`, `M2_preguntas_utiles`, `M3_tiempo`, `M4_satisfaccion`, `M5_invenciones` |
| `target` | string | Umbral obligatorio de aceptación definido por Clarify; nunca se confunde con el resultado |
| `value` | número o nulo | Nulo si no se midió |
| `status` | enum | `NOT_MEASURED`, `MEASURED`, `PARTIAL` |
| `evidence` | string | Enlace/ruta al informe y método |
| `measured_at` | timestamp UTC | Solo si se midió |
| `notes` | string | Limitaciones de muestra, discrepancias SC-005 |

Un registro `NOT_MEASURED` no se presenta como éxito. La UI no muestra métricas PEAS; el informe es evidencia de aceptación.

## 3. Invariantes globales

1. **Una solicitud en vuelo por conversación.** El servidor no crea un segundo turno mientras `active_turn` exista.
2. **Una respuesta por `request_id`.** Un `request_id` completado devuelve la respuesta cacheada; uno activo se rechaza; uno reutilizado con otro texto se rechaza.
3. **Solo turnos completados entran al contexto.** Los fallidos, cancelados, expirados y descartados no actualizan análisis, preguntas ni historial.
4. **Las fuentes son ejecuciones.** No se declara una fuente sin `ToolExecution.status = ok`.
5. **Readiness conservadora.** `listo_para_redactor` solo es verdadero si no hay faltantes, supuestos, ambigüedades ni preguntas pendientes.
6. **Sin invención silenciosa.** Cualquier dato no confirmado debe estar en `supuesta` o `faltante`; no se presenta como `conocida`.
7. **Sin HU.** El esquema no tiene campos de Historia de Usuario, criterios de aceptación, prioridad ni aprobación. El Markdown no debe redactar ni aprobar una HU.
8. **Sin secretos en datos.** El modelo de datos no contiene credenciales, tokens, claves ni el prompt completo en respuestas.
9. **Sin persistencia de navegador.** No hay claves de chat en `localStorage`/`sessionStorage`.
10. **Identidad de sesión opaca.** El navegador nunca ve IDs de sesión OpenCode ni IDs de traza.

## 4. Contexto canónico y construcción del prompt

El contexto se construye en Python con LangChain y se envía como **texto de usuario** a OpenCode. El system prompt no se repite en el mensaje.

### 4.1 Contenido

- `estado_actual`: análisis consolidado, preguntas con estado, readiness y nombres de fuentes de la última respuesta.
- `historial_reciente`: hasta 6 turnos completados de usuario/agente; se recortan primero los mas antiguos.
- `resumen_previo`: resumen determinista del ultimo analisis y estado de preguntas, maximo 2.000 caracteres; solo se recorta despues del historial si el contexto excede el limite.
- `mensaje_actual`: el texto del turno.
- `resultados_herramientas`: resultados MCP de este turno, con una nota de contenido no confiable.
- `limitaciones`: herramientas fallidas, omitidas o con timeout.
- `instrucciones_de_turno`: recordatorio de rol, no inventar, actualizar el estado y devolver solo el JSON.

### 4.2 Límites

| Límite | Valor inicial |
|---|---:|
| Mensaje del usuario | 4.000 caracteres |
| Contexto total enviado a OpenCode | 24.000 caracteres |
| Historial de usuario | Últimos 6 turnos completados |
| Resumen previo canonico | 2.000 caracteres |
| Elementos por lista de análisis | 100 |
| Preguntas | 50 |
| Respuesta Markdown | 50.000 caracteres |
| Resultados por herramienta | 5 |

Si el contexto excede el límite, se recortan primero los turnos más antiguos y luego el resumen previo; nunca se recorta el mensaje actual. El recorte se registra como limitación de contexto, no como una fuente.

### 4.3 Defensa contra inyección

- El texto del usuario y los resultados MCP se delimitan con marcadores y se etiquetan como **datos no confiables**.
- Se instruye al modelo a ignorar instrucciones embebidas y conservar su misión.
- OpenCode no tiene herramientas ni shell; el agente y cada sesión aplican deny-all. Si la respuesta v2 incluye una parte de herramienta o contenido no textual, el backend la rechaza como respuesta no utilizable.
- El backend no ejecuta código ni sigue instrucciones del contenido.

## 5. Idempotencia y concurrencia

### 5.1 Matriz de `request_id`

| Estado del registro | Mismo texto | Texto distinto | Acción |
|---|---|---|---|
| No existe | — | — | Crear turno si no hay otro activo |
| Activo | Sí | — | `409 TURN_IN_PROGRESS` |
| Activo | No | Sí | `409 REQUEST_ID_CONFLICT` si se puede comparar; si no, `TURN_IN_PROGRESS` |
| Completado | Sí | — | Devolver respuesta cacheada, 200 |
| Completado | No | Sí | `409 REQUEST_ID_CONFLICT` |
| Fallido/cancelado/expirado | Sí | — | Devolver el error terminal almacenado; la UI debe iniciar un nuevo intento con nueva identidad si quiere reintentar |
| Fallido/cancelado/expirado | No | Sí | `409 REQUEST_ID_CONFLICT` |

El cliente conserva el `request_id` cuando el fallo es de red o la respuesta es incierta, para que un turno ya completado se recupere sin duplicar. Si el servidor confirma un error terminal, la UI ofrece “Reintentar” con un `request_id` nuevo.

### 5.2 Carreras críticas

| Evento | Regla |
|---|---|
| Doble envío simultáneo | El lock de conversación crea un solo `active_turn`; el segundo recibe 409 |
| Cancelar mientras se procesa | Cancelar gana si marca antes del commit; el turno no entra al contexto |
| Cancelar después del commit | El turno ya es completado; cancelar devuelve `canceled:false` y la UI ignora la respuesta si ya marcó la época |
| Reiniciar mientras se procesa | La generación se incrementa, la conversación se elimina y el turno se descarta; el nuevo ID no puede recibir la respuesta vieja |
| Eliminar mientras se procesa | Igual que reiniciar, más `DELETE` idempotente y cierre del panel |
| Timeout justo al llegar la respuesta | El deadline y el commit se comprueban bajo lock; si gana el timeout, se descarta; si gana el commit, la respuesta es válida y el timeout se considera no aplicado |
| Respuesta tardía de conversación eliminada | Se descarta por `conversation_id` + `turn_id` + `generation`; no por tiempo |
| Recarga del navegador | El cliente no conserva IDs; la conversación vieja queda en el servidor hasta TTL y no se reutiliza |

## 6. Ciclo de vida y limpieza

- **Creación:** `POST /conversaciones`; conversación vacía, `generation = 0`, `expires_at = now + TTL`.
- **Actividad:** cada turno aceptado actualiza `last_activity_at`; los rechazos por concurrencia no deberían extender el TTL de forma indefinida.
- **TTL:** por defecto 30 min de inactividad. Un barrido cada 60 s marca `expirada` y elimina la conversación y sus turnos; si hay una tarea activa, la invalida y aborta.
- **Tope:** 32 conversaciones por proceso. Al llegar al tope, la creación expulsa el registro sin turno activo menos recientemente usado con desempate estable; si todos tienen un turno activo, `POST /conversaciones` devuelve `503 CAPACITY_EXCEEDED`. Nunca se elimina un registro con trabajo en curso.
- **Reinicio:** la conversación anterior se marca `reemplazada`, se elimina del store y se crea una nueva; el ID anterior devuelve 404.
- **Eliminación:** se marca `eliminada`, se elimina del store y se aborta; `DELETE` repetido devuelve 204.
- **Reinicio del backend:** todo el estado se pierde; el primer envío con un ID viejo devuelve 404 `CONVERSATION_NOT_FOUND`; la UI ofrece nuevo chat.

## 7. Validación de entrada y salida

### 7.1 Entrada

- `message`: no vacío, no solo espacios/saltos, ≤4.000 puntos de código.
- `request_id`: UUID v4 válido y obligatorio.
- `conversation_id`: UUID v4 existente.
- `Content-Length` limitado (por ejemplo, 64 KiB) para rechazar cuerpos anómalos.
- JSON con campos extra rechazado o ignorado de forma explícita; el contrato usa `additionalProperties: false` en los esquemas propios.
- No se aceptan adjuntos, archivos, HTML del usuario ni instrucciones de sistema.

### 7.2 Salida del modelo

- Debe ser un único objeto JSON, sin cercas de código ni texto alrededor. Se permite quitar una cerca única antes de parsear.
- Debe cumplir `AgentOutput` con `extra = forbid`.
- `respuesta_markdown` no vacío y ≤50.000; el renderer neutraliza HTML.
- `analisis` con cuatro listas; `preguntas` con categorías/estados permitidos.
- `listo_para_redactor` coherente con la compuerta.
- Si falla: una reparación con el error de validación; si vuelve a fallar, `502 AGENT_OUTPUT_INVALID` y ningún contenido parcial se muestra como válido.
- No se renderiza el JSON crudo en el chat.

## 8. Observabilidad: datos permitidos y prohibidos

| Permitido en traza | Prohibido en traza |
|---|---|
| `conversation_id`, `request_id`, `turn_id` | Texto del usuario, prompt completo, respuesta completa |
| `prompt_version`, `prompt_hash` | Claves, tokens, contraseñas, headers de autenticación |
| Nombre de herramienta, estado, duración, número de resultados | Contenido de glosario, HU similares, estándares o checklist |
| Modelo/proveedor reportado, `finish`, códigos de error | Datos personales, nombres, pólizas, siniestros |
| Duración total y por etapa | Coste/tokens inventados |
| `user_id` pseudónimo fijo | `user_id` real o correo |

La traza raíz se correlaciona con la conversación/solicitud/turno; los spans hijos registran herramientas y la llamada OpenCode. El masking de Langfuse elimina input/output/prompt/completion antes de exportar. El navegador no recibe la traza.

## 9. Evaluación PEAS (datos, no resultados)

El modelo de datos de evaluación registra, como mínimo:

| Métrica | Criterio obligatorio de aceptación | Cómo se mide | Estado inicial |
|---|---|---|---|
| M1 — Vacíos detectados | ≥80 % de los vacíos válidos | Dos analistas etiquetan vacíos en el corpus; se calcula recall/precisión contra el agente | `NOT_MEASURED` |
| M2 — Preguntas útiles | ≥70 % llevadas a Negocio | Dos analistas clasifican cada pregunta como útil/no útil; se mide la proporción | `NOT_MEASURED` |
| M3 — Tiempo de análisis | −50 % frente a línea base manual | Tiempo total asistido vs. análisis manual en el mismo corpus y condiciones | `NOT_MEASURED` |
| M4 — Satisfacción | ≥4/5 | 5 usuarios de prueba completan el flujo y responden encuesta | `NOT_MEASURED` |
| M5 — Datos inventados | 0 presentados como hechos | Revisión contra texto y fuentes; cualquier invención confirmada cuenta como defecto | `NOT_MEASURED` |

- La evaluación PEAS inicial usa 3–5 requerimientos anonimizados conforme a Clarify. SC-005 evalúa M1 y M5 con sus 10 requerimientos especificados; con N < 10, el informe declara `PARTIAL` y SC-005 no pasa. M4 conserva su muestra específica de 5 usuarios.
- Se registra `prompt_version`, `prompt_hash` y commit. Los criterios son obligatorios; sus valores siguen sin ser resultados hasta medirlos.
- La reducción de cambios post-grooming no se mide en esta fase.

## 10. Resumen de límites configurables

| Variable | Valor inicial | Límite/observación |
|---|---:|---|
| `ANALISTA_REQUEST_TIMEOUT_SECONDS` | 90 | Total por mensaje; incluye herramientas, OpenCode, parseo y reparación |
| `ANALISTA_MESSAGE_MAX_CHARS` | 4000 | Puntos de código |
| `ANALISTA_MAX_CONTEXT_CHARS` | 24000 | Recorte de historial |
| `ANALISTA_MAX_TOOL_CALLS` | 4 | No superar 4 |
| `ANALISTA_MCP_TIMEOUT_SECONDS` | 5 | Por herramienta |
| `ANALISTA_MAX_CONVERSATIONS` | 32 | Tope local |
| `ANALISTA_CONVERSATION_TTL_SECONDS` | 1800 | Inactividad |
| `ANALISTA_MAX_CONCURRENT_TURNS` | 2 | Límite de concurrencia del servicio OpenCode |

Los valores son configurables por entorno; los valores efectivos se devuelven en el health. No se presentan como métricas de rendimiento medidas.
