# Quickstart — Chat flotante con Agente Analista (Windows PowerShell)

**Feature**: `002-chat-agente-analista`  
**Rama**: `feat/chat-agente-analista`  
**Fecha**: 2026-10-27  
**Alcance**: instalación, configuración, arranque, comprobaciones y pruebas. Este documento no implementa el código.

> **Seguridad**: usa solo `127.0.0.1`. No publiques OpenCode, el backend ni el frontend en la red. No pongas claves en React, en el repositorio ni en este documento. `.env` está ignorado por Git; verifica antes de commitear.

## 1. Requisitos

| Requisito | Versión / nota |
|---|---|
| Windows | 10 u 11; PowerShell 5.1 o PowerShell 7 |
| Git | Rama `feat/chat-agente-analista` |
| Node.js | 24.15.0 observado; se recomienda ≥20 |
| npm | 11.12.1 observado |
| Python | Python 3.12; el entorno local vive en `agentes/analista/.venv` |
| OpenCode | `2.0.27` o `2.1.2` (API v2); verifica el servidor activo con `GET /api/info`. Se recomienda `2.1.2` para el tiempo de recuperación. |
| Modelo OpenCode | Un proveedor/modelo configurado en OpenCode; no se versiona ninguna clave |
| Langfuse | Opcional para el chat; si no está configurado, el health queda `degraded` |
| Navegador | Chrome/Edge/Firefox actual; se prueba también a 360 px de ancho |

Comprobaciones iniciales, desde la raíz del repositorio:

```powershell
git branch --show-current
git status --short
node --version
npm --version
py -3.12 --version
opencode --version
```

La rama debe ser `feat/chat-agente-analista`. No se debe trabajar directamente en `main`.

## 2. Preparar el entorno Python

```powershell
py -3.12 -m venv .\agentes\analista\.venv
.\agentes\analista\.venv\Scripts\python.exe -m pip install --upgrade pip
.\agentes\analista\.venv\Scripts\python.exe -m pip install -r .\agentes\analista\requirements.txt
```

Los comandos llaman directamente al intérprete del entorno virtual; no requieren activar un
script `.ps1` ni cambiar la política de ejecución de PowerShell.

### 2.1 Lockfile

El archivo versionado `agentes/analista/requirements.lock` se genera con `uv pip compile` en T003. Para instalar o reinstalar de forma reproducible:

```powershell
.\agentes\analista\.venv\Scripts\python.exe -m pip install -r .\agentes\analista\requirements.lock
```

No se debe editar el lockfile a mano.

## 3. Crear el archivo de entorno

```powershell
if (-not (Test-Path .\.env)) { Copy-Item .\agentes\analista\.env.example .\.env }
notepad .\.env
```

Valores esperados (sin secretos reales en el repositorio):

```dotenv
OPENCODE_SERVER_URL=http://127.0.0.1:4096
OPENCODE_SERVER_USERNAME=opencode
OPENCODE_SERVER_PASSWORD=<misma contraseña que uses al arrancar OpenCode>
OPENCODE_PROVIDER_ID=
OPENCODE_MODEL_ID=
ANALISTA_HOST=127.0.0.1
ANALISTA_PORT=8000
ANALISTA_REQUEST_TIMEOUT_SECONDS=90
ANALISTA_TURN_TIMEOUT_SECONDS=90
ANALISTA_MAX_TOOL_CALLS=4
ANALISTA_MESSAGE_MAX_CHARS=4000
ANALISTA_MCP_TIMEOUT_SECONDS=5
ANALISTA_MAX_CONVERSATIONS=32
ANALISTA_CONVERSATION_TTL_SECONDS=1800
ANALISTA_MAX_CONCURRENT_TURNS=2
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

Notas:

- El backend y los diagnósticos leen el `.env` de la raíz del repositorio; está ignorado por Git y nunca se carga en el navegador.
- `OPENCODE_SERVER_PASSWORD` es la clave Basic Auth local del servidor activo. Se guarda solo en `.env`; no la pegues en código, logs ni navegador.
- Las claves de Langfuse vacías activan el modo deshabilitado; el chat sigue funcionando y el health será `degraded`.
- No se usa `LANGFUSE_HOST` ni claves en Vite. No se exponen en `/api/analista/health`.
- Los valores son límites configurables; el health devuelve los efectivos.
- Al recargar, la pestaña nueva empieza sin ID ni historial; el registro anterior sigue solo en
  memoria del servidor hasta eliminación, 30 min de inactividad, expulsión por capacidad o apagado.
  Al llegar a 32 registros se expulsa el inactivo menos recientemente usado; si todos tienen un
  turno activo, la creación devuelve `503 CAPACITY_EXCEEDED`.

## 4. Preflight de OpenCode (T001)

El servidor OpenCode ya está activo en `http://127.0.0.1:4096`. No arranques otro servidor. La contraseña temporal se guarda localmente en el `.env` de la raíz, ignorado por Git. Ejecuta la batería reutilizable desde la raíz; lee la clave en memoria y solo imprime resultados sanitizados:

```powershell
node .\scripts\diagnostics\opencode-v2-t001.mjs
```

La batería consulta `/api/info`, agentes, proveedores y modelos. Las llamadas de generación, permiso, interrupción de una generación activa y prueba de cuota requieren selección explícita de modelo y habilitación manual; no se consume presupuesto por defecto. Las sesiones y el agente temporal se eliminan en `finally`. No imprime prompt, respuesta, credenciales ni IDs de sesión.

La instancia probada es OpenCode `2.0.27`/API v2. `/global/health` y `/doc` sirven HTML en esta versión; no se deben usar como pruebas de API. Contrasta rutas y schemas con [OpenCode v2 API](./contracts/opencode-v2.md) y la referencia oficial, no con un contrato v1.

## 5. Configurar el agente v2

El agente de proyecto está en `opencode.jsonc`. `system` carga el prompt desde `agentes/analista/prompts/sistema.md` mediante `{file:...}` y conserva deny-all; no fija modelo ni proveedor. El backend genera exclusivamente a través de OpenCode. `OPENCODE_PROVIDER_ID` vacío usa `opencode`; `OPENCODE_MODEL_ID` permite elegir un ID listado por `/api/model`, y vacío usa el modelo predeterminado si pertenece al provider configurado. Sin selección explícita de provider y modelo, el backend exige costo cero publicado en entrada, salida y caché. Configurar ambos autoriza ese par aunque el precio sea positivo o desconocido; OpenCode aún debe anunciar el modelo y marcarlo habilitado. Por ejemplo, `OPENCODE_PROVIDER_ID=opencode-go` y `OPENCODE_MODEL_ID=glm-5.3-flash`. `/api/analista/health` informa configuración, selección efectiva y motivo de rechazo. La lista no garantiza cuota ni acceso real. Las herramientas MCP autorizadas se ejecutan en el backend.

Comprueba que el prompt existe y no está vacío:

```powershell
Get-Item .\agentes\analista\prompts\sistema.md | Select-Object FullName, Length, LastWriteTime
```

El agente y el prompt se verifican con `/api/agent` en el location del proyecto. OpenCode actualiza esta configuración mediante su watcher; el backend compara versión/hash y bloquea si el archivo cambió desde la última carga confirmada.

## 6. Arrancar o conectar OpenCode Server

Si OpenCode Server no está activo, abre una terminal PowerShell desde la raíz y arráncalo en loopback:

```powershell
opencode serve --hostname 127.0.0.1 --port 4096
```

Mantén abierta esa terminal y alinea el usuario/contraseña Basic Auth local que usa OpenCode con `.env`. Si el puerto 4096 ya está escuchando, reutiliza esa instancia: no arranques una segunda ni cambies el perfil habitual. FastAPI usa Basic Auth en llamadas servidor-a-servidor a `/api/...`.

T001 verifica el contrato API sin consumir presupuesto por defecto. Un `429 provider.quota` impide la generación real; no bloquea las pruebas automatizadas aisladas. No se selecciona otro proveedor ni se simulan respuestas.

### Contador automático de cuota

El contador toma `retryAfterMs` del error estructurado del mensaje de sesión en OpenCode `2.1.2`. El backend lo transforma a `retry_at` y React actualiza el contador local cada segundo; no hace llamadas adicionales ni reintenta al llegar a cero. En `2.0.27` el chat sigue funcionando y muestra que OpenCode no informó el tiempo. Para activarlo, ejecuta una instancia `2.1.2` en el URL configurado por `OPENCODE_SERVER_URL`, conserva el mismo password Basic Auth local y el usuario `opencode`, y reinicia FastAPI. No es necesario cambiar proveedor/modelo ni credenciales globales; el modelo debe mantener precio publicado cero.

Para evaluar la CLI sin modificar la instalación oficial, instala la versión candidata en una ruta temporal y arráncala desde el proyecto. Esto crea una instalación paralela:

```powershell
$opencodeProbe = Join-Path $env:TEMP 'opencode-2.1.2-isolated'
npm install --prefix $opencodeProbe --no-audit --no-fund @opencode/cli@2.1.2
& (Join-Path $opencodeProbe 'node_modules/@opencode/cli/bin/opencode.exe') --version
```

La prueba de compatibilidad guardada en [evidence/opencode-2.1.2-compatibility.md](./evidence/opencode-2.1.2-compatibility.md) usa directorios de configuración/datos temporales y no hace generación. Para habilitar el contador sin reemplazar la instalación oficial, detén el servidor `2.0.27` activo, ejecuta el binario instalado en `%TEMP%` desde la raíz del proyecto y proporciona de forma oculta el mismo password Basic Auth de `.env`. El password solo se exporta al proceso local de OpenCode y se limpia al cerrar:

```powershell
$opencodeProbe = Join-Path $env:TEMP 'opencode-2.1.2-isolated'
$securePassword = Read-Host 'Password Basic Auth local usado por FastAPI' -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
  $env:OPENCODE_SERVER_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
  & (Join-Path $opencodeProbe 'node_modules/@opencode/cli/bin/opencode.exe') serve --hostname 127.0.0.1 --port 4096
} finally {
  Remove-Item Env:OPENCODE_SERVER_PASSWORD -ErrorAction SilentlyContinue
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
}
```

El usuario Basic de OpenCode v2 es `opencode`; el backend usa ese valor por defecto. No arranques los dos servidores a la vez. Reinicia FastAPI y verifica `GET /api/info` en el mismo `OPENCODE_SERVER_URL`; no es necesario cambiar modelo ni proveedor, y el backend seguirá rechazando precios positivos o desconocidos. El perfil existente de OpenCode se reutiliza sin cambiar credenciales globales. No envíes una consulta para comprobar la cuota hasta que decidas hacerlo; la inspección estructural no consume generación.
## 7. Arrancar el backend

En otra terminal PowerShell, desde la raíz:

```powershell
& .\agentes\analista\.venv\Scripts\python.exe -m uvicorn agentes.analista.api.main:app --host 127.0.0.1 --port 8000 --workers 1
```

- `--workers 1` es obligatorio: el estado es en memoria.
- No uses `--reload`: un reinicio borra conversaciones en memoria.
- El backend lee Basic Auth desde el `.env` de la raíz; el archivo de ejemplo está en `agentes/analista/.env.example`.
- El backend no expone OpenCode ni Langfuse al navegador.

Comprueba el health:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/analista/health' | ConvertTo-Json -Depth 8
```

Interpretación:

- `ready`: flujo completo y Langfuse sano.
- `degraded`: el chat puede operar; por ejemplo, Langfuse deshabilitado o una fuente individual con problema. La UI lo muestra.
- `unavailable`: FastAPI respondió, pero OpenCode/MCP/prompt no están listos. Revisa la tabla de problemas.

Un HTTP 200 confirma que FastAPI respondió; no prueba que el modelo pueda generar. El panel diferencia `Backend conectado`, `OpenCode Server conectado` y `Generación del modelo sin verificar`. La capacidad de generación solo se confirma tras una respuesta real. Si health no responde, la UI muestra `Backend desconectado`; si `checks.opencode.status` no está disponible, muestra `OpenCode Server desconectado`. Los errores `MODEL_UNAVAILABLE`, `OPENCODE_RATE_LIMITED` (429) y `TURN_TIMEOUT` identifican modelo ausente, cuota agotada y deadline de 90 segundos.

Si Langfuse no está configurado, `degraded` es el resultado esperado, no un fallo del chat.

## 8. Arrancar el frontend

En una tercera terminal, desde la raíz, instala las dependencias una vez (o al cambiar el lockfile) y ejecuta Vite para desarrollo:

```powershell
npm ci
npm run dev
```

Abre `http://localhost:3000`. Vite enruta `/api/analista` a `http://127.0.0.1:8000` mediante proxy. Si falta `package-lock.json`, usa `npm install` en lugar de `npm ci`.

Para compilar y previsualizar la versión de producción, usa este modo en lugar de `npm run dev`:

```powershell
npm run build
npm run preview
```

La previsualización se publica normalmente en `http://localhost:4173`. Después de editar archivos, vuelve a ejecutar `npm run build`. En desarrollo y previsualización, el navegador solo llama al proxy `/api/analista`, nunca a OpenCode, MCP o Langfuse.

Comprobación rápida de que el proxy responde:

```powershell
Invoke-RestMethod -Uri 'http://localhost:3000/api/analista/health' | ConvertTo-Json -Depth 8
```

## 9. Prueba de humo real

La prueba debe usar OpenCode, MCP y el modelo reales. No se acepta una respuesta preparada.

### 8.1 Crear conversación

```powershell
$conv = Invoke-RestMethod `
  -Method Post `
  -Uri 'http://127.0.0.1:8000/api/analista/conversaciones'
$conv | ConvertTo-Json -Depth 6
$conversationId = $conv.conversation_id
```

### 8.2 Enviar un requerimiento

```powershell
$requestId = [guid]::NewGuid().ToString()
$payload = @{
  request_id = $requestId
  message = 'Como analista de Popular Seguros necesito que el sistema permita registrar una solicitud de póliza y avisar al cliente cuando esté lista. No está claro qué datos son obligatorios ni cuál es el plazo de respuesta.'
} | ConvertTo-Json

$response = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/analista/conversaciones/$conversationId/mensajes" `
  -ContentType 'application/json' `
  -Body $payload `
  -TimeoutSec 120

$response | ConvertTo-Json -Depth 10
```

Comprueba:

- `estado` es `completado`;
- `respuesta_markdown` es texto real del agente;
- las cuatro categorías de `analisis` aparecen, incluso vacías;
- `fuentes_consultadas` contiene solo fuentes ejecutadas;
- `duracion_ms` es un valor medido;
- no hay HTML crudo ni JSON crudo en el Markdown;
- la respuesta no contiene claves, rutas ni IDs de sesión OpenCode.

### 8.3 Cancelar un turno

En la terminal A, inicia un envío y deja que bloquee. En la terminal B, usa el mismo `conversationId` y `requestId`:

```powershell
$cancelBody = @{ request_id = $requestId } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/analista/conversaciones/$conversationId/cancelar" `
  -ContentType 'application/json' `
  -Body $cancelBody | ConvertTo-Json -Depth 6
```

Resultado esperado: `canceled: true` (o `false` con `NO_ACTIVE_TURN` si ya terminó). La terminal A debe recibir `409 TURN_CANCELLED` o una respuesta que la UI descarte; el contexto anterior se conserva y el turno cancelado no se usa en el siguiente mensaje.

### 8.4 Nuevo chat y eliminación

```powershell
# Nuevo chat: conserva el panel abierto, crea un ID nuevo
$reset = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/analista/conversaciones/$conversationId/reiniciar"
$reset | ConvertTo-Json -Depth 6
$newConversationId = $reset.conversation_id

# Eliminar: idempotente; el frontend cierra el panel
Invoke-RestMethod `
  -Method Delete `
  -Uri "http://127.0.0.1:8000/api/analista/conversaciones/$newConversationId"
```

Un `DELETE` repetido debe devolver 204.

## 10. Pruebas automatizadas

### 9.1 Backend

```powershell
& .\agentes\analista\.venv\Scripts\python.exe -m pytest .\agentes\analista\tests -q
```

La suite incluye contrato REST, validación, concurrencia, idempotencia, cancelación, timeout, MCP, parseo/reparación, prompt/hash, health, observabilidad y secretos. Los dobles de OpenCode solo existen en pruebas; en runtime no hay respuestas simuladas.

### 9.2 Frontend

```powershell
npm test
npm run build
node .\scripts\diagnostics\validate-feature-docs.mjs
```

`npm test` ejecuta Vitest en modo CI; el nombre del script definido en `package.json` es `test`. `build` verifica que Vite 5 compila sin TypeScript y sin romper las rutas existentes. El validador de documentos comprueba referencias locales, contratos y rutas implementadas. Para desarrollo de pruebas:

```powershell
npm run test:watch
```

### 9.3 Integración manual obligatoria

Con OpenCode, backend y frontend reales:

1. Recorre `/`, `/historias`, `/historias/nueva`, `/historias/:id`, `/historias/:id/editar` y `/ayuda`; el botón aparece en todas.
2. Abre/cierra el panel; el historial se conserva al cerrar.
3. Envía un mensaje real; verifica indicador inmediato, respuesta, análisis, preguntas, fuentes y readiness.
4. Cancela un turno; verifica que no entra al contexto y que se puede enviar otro.
5. Inicia **Nuevo chat**; el panel sigue abierto y el historial queda vacío.
6. **Eliminar** pide confirmación, borra el contexto y cierra el panel.
7. Recarga el navegador; el chat inicia vacío, sin recuperar la conversación anterior.
8. Fuerza un fallo de OpenCode (detén el servidor); el chat muestra error recuperable y no una respuesta inventada.
9. Deja que venza el timeout; el turno se aborta y no se acepta una respuesta tardía.
10. Revisa 360 px, 768 px y escritorio; sin overflow horizontal y sin cubrir la navegación.
11. Revisa teclado: Tab, Enter, Escape, foco al abrir/cerrar y `aria-live`.
12. Revisa Markdown con tablas GFM, enlaces, HTML crudo, `javascript:` e imágenes remotas; no debe ejecutarse nada.
13. Recorre Dashboard, listado, Stepper y Accordion; vuelve a probar todas las rutas, estilos
responsive y claves/datos ya existentes en `localStorage`. Confirma que el chat no crea claves ni
borra o muta los datos del prototipo.
14. Verifica que el tráfico del navegador no contiene claves, prompt ni llamadas a OpenCode/Langfuse.

El servidor MCP no requiere una terminal adicional: FastAPI inicia el proceso stdio local al ejecutar un turno y lo cierra al terminar la consulta. No arranques otra instancia MCP manualmente durante la aceptación.

## 11. Métricas PEAS

La evaluación PEAS no se ejecuta con la prueba de humo. Los cinco umbrales son criterios obligatorios de aceptación según Clarify; el protocolo está en `plan.md` (§ Medición PEAS). Debe:

- congelar el corpus y el hash del prompt;
- usar 3–5 requerimientos para la evaluación PEAS inicial; ampliar a N=10 para cumplir SC-005 (M1 y M5);
- reportar el tamaño real de la muestra;
- registrar `NOT_MEASURED` mientras no haya medición, entendiendo que ese estado no satisface la aceptación;
- no presentar 80 %, 70 %, −50 %, 4/5 ni “0 invenciones” como resultados logrados.

La evaluación inicial usa 3–5 casos. SC-005 solo se declara cumplido con N=10; con N<10 se reporta `PARTIAL`, que no satisface aceptación.

## 12. Cambiar el prompt

1. Edita `agentes/analista/prompts/sistema.md`.
2. El watcher del servidor OpenCode existente recarga la configuración de agente del proyecto; verifica `GET /api/agent` si cambió la configuración.
3. Reinicia únicamente el backend para cargar el nuevo snapshot de prompt.
4. Consulta `/api/analista/health`: el `prompt_hash` debe cambiar y `restart_required` debe ser `false`.

No inicies otro servidor OpenCode ni cambies el perfil habitual. Si el agente no refleja la configuración nueva, bloquea el envío y revisa el log local sin copiar prompts o credenciales.

## 13. Problemas frecuentes

| Síntoma | Causa probable | Acción |
|---|---|---|
| `OPENCODE_INCOMPATIBLE` | Versión distinta de la fijada o schema v2 inesperado | Verifica `GET /api/info`; compara con `contracts/opencode-v2.md` |
| `OPENCODE_AUTH_FAILED` | Basic Auth no coincide | Revisa usuario/contraseña en el `.env` local; no las compartas |
| `OPENCODE_UNAVAILABLE` | Servidor/proveedor no disponible | Revisa el listener 4096 y el proveedor/modelo; no inicies un segundo servidor |
| `OPENCODE_INCOMPATIBLE` o 503 de OpenCode | Versión/API distinta, proveedor no disponible o contrato local inesperado | Confirma OpenCode `2.0.27` con `GET /api/info`; revisa `contracts/opencode-v2.md` y proveedor/modelo; no aceptes respuestas simuladas |
| `PROMPT_INVALID` | Prompt ausente/vacío | Restaura `sistema.md`; reinicia el backend |
| `PROMPT_RESTART_REQUIRED` | Prompt editado desde el snapshot del backend | Reinicia el backend después de que OpenCode recargue el agente |
| `MCP_UNAVAILABLE` | Servidor MCP no arranca/faltan tools | Revisa `PYTHONPATH`, el paquete y el listado de tools |
| `TURN_IN_PROGRESS` | Segundo envío o reintento durante un turno | Espera o cancela; no dupliques |
| `CONVERSATION_NOT_FOUND` | Backend reiniciado, TTL o conversación eliminada | Inicia nuevo chat; el historial viejo no se recupera |
| `AGENT_OUTPUT_INVALID` | JSON inválido tras una reparación | Reintenta; revisa el prompt y el modelo |
| `TURN_TIMEOUT` | Se agotaron 90 s o OpenCode respondió 504 | Reintenta; revisa el timeout de OpenCode |
| `OPENCODE_RATE_LIMITED` | OpenCode devolvió 429/`provider.quota` | Espera cuota o configura otro modelo `opencode` autorizado |
| `MODEL_UNAVAILABLE` | Modelo o provider no listado/habilitado, o default de otro provider | Revisa `OPENCODE_PROVIDER_ID`, `OPENCODE_MODEL_ID`, `/api/model` y `checks.opencode.rejection_reason` en `/api/analista/health` |
| Health `degraded` por Langfuse | Claves ausentes o servicio caído | El chat funciona; configura Langfuse o acepta el aviso |
| `401` en `/api/info` | Basic Auth no coincide | Revisa usuario/contraseña en el `.env` local; no los pegues en el issue |
| `npm run dev` no llega al backend | Proxy Vite ausente/incorrecto | Revisa `vite.config.js` y que el backend esté en 8000 |
| Puerto ocupado | Otro proceso usa 3000/4096/8000 | `Get-NetTCPConnection -LocalPort 3000,4096,8000`; detén el proceso o cambia el puerto de forma coordinada |

No incluyas contraseñas, claves ni texto de requerimientos en capturas o issues.

## 14. Detener y limpiar

En cada terminal, `Ctrl+C`.

```powershell
Get-NetTCPConnection -LocalPort 3000,4096,8000 -ErrorAction SilentlyContinue
```

- Detener el backend borra todas las conversaciones en memoria.
- Detener OpenCode no borra el prompt ni los datos de fuentes.
- No se debe borrar `.env` con `git clean`; está ignorado y contiene secretos locales.
- Para reiniciar desde cero: detén los tres procesos, vuelve a arrancarlos y recarga el navegador. No hay recuperación de chat.

## 15. Seguridad y alcance

- Todo escucha en `127.0.0.1`; no se publica en LAN.
- Sin CORS abierto; el frontend usa el proxy de Vite.
- Sin secretos en el bundle; sin llamadas del navegador a OpenCode/Langfuse.
- Sin `localStorage`/`sessionStorage` para el chat.
- El agente es de solo lectura: no redacta ni aprueba historias de usuario.
- Los datos de fuentes son ficticios/anonimizados; no se usan datos reales de Popular Seguros.
- El chat no reemplaza el Stepper ni las pantallas existentes.

## 16. Orden recomendado de arranque

1. El servidor OpenCode existente, con el agente de proyecto v2 y Basic Auth local.
2. Backend con el health en `ready` o `degraded` aceptable.
3. Frontend con Vite.
4. Prueba de humo real.
5. Pruebas automatizadas y build.
6. Evaluación PEAS cuando el corpus y los evaluadores estén listos.
