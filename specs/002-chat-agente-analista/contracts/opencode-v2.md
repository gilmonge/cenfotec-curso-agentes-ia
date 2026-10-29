# Contrato de integración — OpenCode Server API v2

**Feature**: `002-chat-agente-analista`  
**Servidor verificado históricamente**: OpenCode `2.0.27`, API v2, loopback `127.0.0.1:4096`. OpenCode `2.1.2` también se validó en un entorno aislado el 2026-10-27, sin llamadas de generación.
**Evidencia**: [preflight-results.md](../evidence/preflight-results.md) y `scripts/diagnostics/opencode-v2-t001.mjs`.

OpenCode Server v2 es la única interfaz autorizada para generar texto. FastAPI autentica y llama a OpenCode; ningún código del backend se conecta a proveedores directamente. La referencia de rutas es la [API/OpenAPI v2 oficial](https://dev.opencode.ai/v2/docs/api). La autenticación del servidor usa Basic Auth solo en el backend.

## Descubrimiento y selección de modelo

| Método y ruta | Uso | Respuesta relevante |
|---|---|---|
| `GET /api/info` | Identidad y versión | `ServerInfo` |
| `GET /api/agent?location[directory]=...` | Agentes del proyecto | `{location, data: Agent.Info[]}` |
| `GET /api/provider?location[directory]=...` | Proveedores activos | `{location, data: Provider.Info[]}` |
| `GET /api/model?location[directory]=...` | Modelos listados | `{location, data: Model.Info[]}` |
| `GET /api/model/default?location[directory]=...` | Modelo predeterminado | `{location, data: Model.Info \| null}` |

`OPENCODE_PROVIDER_ID` y `OPENCODE_MODEL_ID` son selecciones opcionales locales, no secretos. El provider predeterminado es `opencode`; el modelo predeterminado solo se acepta si pertenece a ese provider y su precio publicado es cero para entrada, salida y caché en todos los niveles. Si provider y modelo están configurados juntos, esa selección explícita autoriza precio positivo o metadata de costo ausente. En ambos casos, el provider/model debe aparecer anunciado y habilitado en `/api/model`; si no, se rechaza con `MODEL_UNAVAILABLE` antes de crear una sesión. La lista de modelos no demuestra cuota ni acceso de generación. `/api/analista/health` devuelve provider/model configurado, selección efectiva y código/motivo de rechazo sin exponer credenciales.

La consulta v2 más reciente listó el proveedor `opencode`, 45 modelos habilitados para ese proveedor y nueve con precio publicado en cero. Los nueve modelos de costo cero fueron probados; ninguno produjo respuesta (ocho devolvieron `provider.quota`/429 y uno no estuvo disponible). No se probaron modelos que pudieran consumir presupuesto. **La generación real mediante un modelo del proveedor `opencode` sigue sin verificar.** Los detalles por modelo están en [preflight-results.md](../evidence/preflight-results.md).

## Agente y permisos

V2 define agentes como `agents.<id>` con `system` y `permissions`; `{file:path}` carga el prompt externo. `opencode.jsonc` no fija proveedor ni modelo. El backend crea cada sesión con el modelo seleccionado y la regla deny-all:

```json
[{"action":"*","resource":"*","effect":"deny"}]
```

El preflight histórico confirmó que el agente cargaba el prompt y conservaba deny-all. La generación de herramientas MCP permitidas ocurre desde FastAPI/LangChain; OpenCode no recibe permiso para ejecutar herramientas.

## Sesiones, mensajes y limpieza

`POST /api/session` recibe `Model.Ref` con `{id, providerID}`, agente, location y deny-all; responde `200 {"data": Session.Info}`. Cada turno usa una sesión efímera nueva.

`POST /api/session/{sessionID}/prompt` admite `{ "text": "..." }` y confirma admisión, no finalización. El backend sondea `GET /api/session/{sessionID}/message?limit=...&order=asc`. Los mensajes assistant aparecen directamente en `data[]` con `type`, `time.completed`, `model`, `content[]`, `finish` y, en error, `error`. Solo se concatena texto assistant completo posterior a la admisión.

| Método y ruta | Resultado esperado | Uso |
|---|---|---|
| `POST /api/session/{sessionID}/interrupt` | `200 {"interrupted": boolean}` | Cancelar generación activa |
| `DELETE /api/session/{sessionID}` | `204 No Content` | Borrar siempre en `finally` |
| `GET /api/session/{sessionID}` | `404` después de borrar | Confirmar limpieza |

La respuesta de interrupt es directa, sin wrapper `data`. No se trata `POST /prompt` como generación síncrona.

## Errores

- `401/403`: `OPENCODE_AUTH_FAILED`; no se devuelven headers ni cuerpos del servidor.
- `404`: recurso API esperado ausente → `OPENCODE_INCOMPATIBLE`; modelo listado no disponible → `MODEL_UNAVAILABLE`.
- `409`: conflicto de sesión recuperable → `OPENCODE_UNAVAILABLE`.
- `429` o `provider.quota`: `OPENCODE_RATE_LIMITED`, reintentable y expuesto por FastAPI como `503`.
- `503`/otros `5xx`: `OPENCODE_UNAVAILABLE`; `504` o deadline excedido: `TURN_TIMEOUT`, HTTP `504`.
- Errores de proveedor que indican modelo ausente: `MODEL_UNAVAILABLE`. No se selecciona otro proveedor ni se genera respuesta simulada.
- Schema incompatible, respuesta assistant incompleta o contenido inválido: error controlado; nunca se registran prompt, texto, cuerpos de error ni credenciales.

### Recuperacion de cuota

El backend acepta OpenCode `2.0.27` y `2.1.2`; versiones desconocidas se rechazan. En `2.0.27`, `GET /api/session/{sessionID}/message` devuelve el error `provider.quota` sin un instante de recuperación verificable, por lo que la interfaz conserva el mensaje de tiempo desconocido.

OpenCode `2.1.2` añade `retryAfterMs` al error estructurado de sesión y el tipo `provider.free-limit`. Cuando OpenCode Console reconoce un `FreeUsageLimitError` con tiempo de reinicio, OpenCode lo traduce a `provider.free-limit` y conserva `retryAfterMs` en el mensaje devuelto por `GET /api/session/{sessionID}/message`. La API expone una duración en milisegundos, no una fecha absoluta. El backend la suma a `time.completed` del mensaje y FastAPI la propaga como `error.retry_at` ISO 8601 UTC. También se aceptan pistas válidas en respuestas HTTP 429 directas.

La conversión ignora duraciones ausentes, inválidas, negativas, vencidas o fuera de rango; no supone un periodo de 24 horas. Nunca se propagan el mensaje o cuerpo del proveedor ni las cabeceras originales. React ejecuta una cuenta regresiva local, no llama servicios durante la cuenta y conserva el reintento manual; al llegar a cero no reintenta automáticamente ni duplica el mensaje. Como 2.1.2 expone el dato por la API que usa el backend, no se requiere entrada manual ni leer OpenCode Console por separado.

#### Compatibilidad de 2.1.0

2.1.0 cambió campos públicos de replay/proveedor (`state`/`providerState` a `native`), estado y resultado de herramientas, metadata de credenciales y referencias de compactación. El cliente de esta feature no lee ni escribe esos campos: consume `Session.Message.Assistant` y sus campos `type`, `time`, `finish`, `content` y `error`; crea sesiones con `agent`, `model`, `location`, `permissions`; envía `text`; lista mensajes; interrumpe y borra sesiones. La inspección del OpenAPI y una sesión efímera en 2.1.2 confirmaron que esos contratos usados se conservan. La compatibilidad de generación y la cancelación de una generación activa requieren una prueba con generación real, que no se ejecutó.

La autenticación Basic de v2 usa el usuario `opencode`; al iniciar 2.1.2, el password local debe coincidir con el configurado en FastAPI. No se requieren cambios de credenciales globales. OpenCode Server debe anunciar y habilitar el provider/model elegido por FastAPI; el provider predeterminado es `opencode`, pero la selección explícita se configura mediante `OPENCODE_PROVIDER_ID` y `OPENCODE_MODEL_ID`.

El cliente también interpreta `Retry-After` (segundos delta o fecha HTTP futura) y `retry-after-ms` solo cuando esas cabeceras están en una respuesta HTTP 429 directa. Las fechas y duraciones futuras válidas se normalizan como `retry_at` en el sobre REST; los valores ausentes o no válidos se omiten.

## Referencias oficiales

- [API reference/OpenAPI v2](https://dev.opencode.ai/v2/docs/api)
- [OpenAPI JSON v2](https://dev.opencode.ai/v2/openapi.json)
- [OpenCode v2.1.2 changelog: `retryAfterMs` in structured session errors](https://github.com/anomalyco/opencode/blob/v2.1.2/CHANGELOG.md)
- [OpenCode PR #57146: contrato y origen de `retryAfterMs`](https://github.com/anomalyco/opencode/pull/57146)
- [Schema v2.1.2 de `Session.StructuredError`](https://github.com/anomalyco/opencode/blob/v2.1.2/packages/schema/src/session-error.ts)
- [OpenCode v2.1.0 changelog: breaking changes](https://github.com/anomalyco/opencode/blob/v2.1.0/CHANGELOG.md)
- [Agentes v2](https://dev.opencode.ai/v2/docs/agents/)
- [Permisos v2](https://dev.opencode.ai/v2/docs/permissions/)
- [Configuración y `{file:...}` v2](https://dev.opencode.ai/v2/docs/config/)
- [Autenticación Basic del servidor](https://dev.opencode.ai/docs/server/)
