# Compatibilidad de OpenCode 2.1.2

**Fecha:** 2026-10-27  
**Rama:** `feat/chat-agente-analista`  
**Resultado:** compatible para los contratos de sesión usados; no se ejecutó generación.

## Entorno aislado

- Instalación local desechable: `npm install --prefix %TEMP%\opencode-2.1.2-isolated --no-audit --no-fund @opencode/cli@2.1.2`.
- El binario temporal reportó `opencode v2.1.2`. El servidor corrió en `127.0.0.1:4197` desde un directorio de proyecto vacío, con perfil/configuración/datos temporales y Basic Auth de prueba limitado al proceso.
- La instalación existente de OpenCode, el `.env`, las credenciales globales y los archivos de configuración oficiales no se modificaron.
- No se envió `POST /api/session/{id}/prompt`; no hubo llamadas de generación ni a proveedores/modelos.

## Verificaciones HTTP

| Verificación | Resultado |
|---|---|
| Basic Auth con credencial efímera | Aceptada |
| `GET /api/info` | `200`, versión `2.1.2` |
| `GET /openapi.json` | `200`, OpenAPI `3.1.0` |
| `Session.StructuredError` | Incluye `type`, `message`, `status`, `response` y `retryAfterMs` opcional (`integer`, mínimo `0`) |
| `GET /api/agent`, `/api/provider`, `/api/model` | Contratos responden; agente y catálogo accesibles sin una llamada de generación |
| `POST /api/session` | `200`, respuesta `{data: Session.Info}`; conserva la regla deny-all |
| `GET /api/session/{id}/message?limit=30&order=asc` | `200`, respuesta con `data` como array |
| `POST /api/session/{id}/interrupt` sin ejecución | `200`, cuerpo directo `{interrupted: false}` |
| `DELETE /api/session/{id}` | `204`; el `GET` posterior devuelve `404` |

Se usó un modelo de costo cero listado únicamente como referencia al crear y borrar la sesión efímera; no se inició una generación. La ruta/cuerpo de `POST /prompt` se contrastó en el OpenAPI pero no se invocó.

## Compatibilidad con 2.1.0

El changelog describe cambios incompatibles en datos públicos de replay del proveedor (`state`/`providerState` → `native`), forma de datos de replay para herramientas, metadatos de configuración de credenciales y referencias de compactación. El cliente de esta feature no lee/escribe esos campos. Continúa usando `type`, `time`, `finish`, `content` y `error` de los mensajes assistant; crea sesiones con agente/modelo/location/permisos; sondea mensajes; interrumpe y elimina sesiones. OpenAPI y la sesión efímera confirmaron esos contratos usados en 2.1.2.

La autenticación v2 usa el usuario Basic `opencode`; se mantiene el password local configurado para FastAPI. La feature conserva exclusivamente OpenCode Server como interfaz de generación y mantiene la selección de modelos `providerID=opencode` cuyo precio publicado sea cero.

No se verificaron generación efectiva, continuidad de prompt ni cancelación mientras existe una generación en curso. Esos puntos requieren una llamada real y siguen pendientes de la aceptación manual; esta inspección no se presenta como prueba de generación.

## Recuperación de cuota

En 2.1.2, OpenCode mapea errores Console `FreeUsageLimitError` a `provider.free-limit` y conserva `retryAfterMs` cuando el servicio envía el tiempo de restablecimiento. El campo aparece en el `error` del mensaje que recupera el backend por `GET /api/session/{id}/message`; no hay que leer Console ni agregar una llamada.

`retryAfterMs` es duración, no epoch. El esquema de OpenCode describe la duración como contada desde que se registró el fallo; el backend usa `time.completed` del mensaje assistant como esa base y agrega la duración válida para producir `retry_at` UTC en el sobre de error FastAPI. Si el campo no está, es inválido o ya venció, la interfaz mantiene el mensaje de recuperación desconocida. React actualiza el contador local una vez por segundo, sin solicitudes automáticas; el botón de reintento sigue siendo manual. Como la API de 2.1.2 entrega el dato, no se agregó entrada manual de fecha.

OpenCode `2.0.27` se conserva como versión compatible para el resto del chat, pero no expone el tiempo de reinicio de esta cuota en el error de sesión, así que seguirá usando el estado desconocido.

## Fuentes primarias

- [Changelog v2.1.2](https://github.com/anomalyco/opencode/blob/v2.1.2/CHANGELOG.md)
- [Pull request #57146: error tipado de límite gratuito y `retryAfterMs`](https://github.com/anomalyco/opencode/pull/57146)
- [Schema de OpenCode 2.1.2: `retryAfterMs` contado desde el registro del fallo](https://github.com/anomalyco/opencode/blob/v2.1.2/packages/schema/src/session-error.ts)
- [Schema de OpenCode 2.1.2: timestamps de sesión en milisegundos](https://github.com/anomalyco/opencode/blob/v2.1.2/packages/schema/src/session.ts)
- [Changelog v2.1.0: cambios incompatibles](https://github.com/anomalyco/opencode/blob/v2.1.0/CHANGELOG.md)
- [API v2 / OpenAPI](https://dev.opencode.ai/v2/docs/api)
- [Schema v2.1.2 de mensajes y tiempos](https://github.com/anomalyco/opencode/blob/v2.1.2/packages/schema/src/session-message.ts)

## Validación adicional con el proyecto real

Después de la inspección del directorio vacío, se inició otra vez el binario `2.1.2` desde la raíz real del proyecto, aún con profile/config/data temporales. `/api/agent` devolvió `analista` con el prompt cargado y deny-all. Se creó una sesión efímera con ese agente y un ID de modelo listado de costo cero, se confirmó deny-all, se consultaron mensajes, se llamó a interrupt sin generación (`false`), se borró la sesión y el GET siguiente devolvió 404. No se llamó `/prompt`.

La Basic Auth se validó con el password de prueba efímero; no se leyó el password ni el almacén de credenciales global del usuario. La compatibilidad de esas credenciales con el arranque real queda pendiente de la activación manual. Tampoco se verificó cancelar una generación activa.
