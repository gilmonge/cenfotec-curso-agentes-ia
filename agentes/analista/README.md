# Agente Analista de Requerimientos

Backend local de solo lectura para la feature `002-chat-agente-analista`.

## Arquitectura

React se comunica con FastAPI por el proxy local de Vite. FastAPI orquesta LangChain, las cuatro herramientas MCP stdio y OpenCode Server `2.0.27` o `2.1.2`/API v2. El proceso MCP se inicia por turno; no necesita una terminal ni un servicio aparte. Langfuse es opcional y el chat se degrada a `degraded` si no está configurado o falla.

La generación usa exclusivamente `providerID=opencode`. El cliente acepta `OPENCODE_MODEL_ID` si aparece en la lista del servidor y tiene costo publicado cero para entrada, salida y caché; costo positivo o desconocido se rechaza. No se usa Ollama ni una respuesta simulada en runtime. OpenCode y FastAPI deben escuchar solo en `127.0.0.1`.

## Requisitos y configuración

- Windows 10/11, PowerShell 5.1 o 7.
- Node.js 24.15.0 y npm 11.12.1 verificados en este entorno; se recomienda Node.js 20 o superior.
- Python 3.12.10 verificado; usa `agentes/analista/.venv`.
- OpenCode Server `2.0.27` o `2.1.2`/API v2 activo en `127.0.0.1:4096`. `2.1.2` aporta `retryAfterMs` para el aviso de cuota cuando el proveedor lo devuelve.
- Las credenciales locales van en `.env` de la raíz, creado desde `agentes/analista/.env.example`; nunca se copian al frontend ni al repositorio.

## Instalación y arranque

Ejecuta desde la raíz del repositorio. El [quickstart](../../specs/002-chat-agente-analista/quickstart.md) contiene la configuración `.env`, los health checks, el troubleshooting y la detención de procesos. No copies credenciales, tokens ni contraseñas a la documentación o al navegador.

```powershell
py -3.12 -m venv .\agentes\analista\.venv
& .\agentes\analista\.venv\Scripts\python.exe -m pip install -r .\agentes\analista\requirements.lock
if (-not (Test-Path .\.env)) { Copy-Item .\agentes\analista\.env.example .\.env }
```

Primero inicia OpenCode Server `2.0.27` o `2.1.2` en `127.0.0.1:4096` (si no está activo) y alinea su Basic Auth local con el `.env` de la raíz. No dupliques un proceso que ya ocupa el puerto.

```powershell
opencode serve --hostname 127.0.0.1 --port 4096
```

Después inicia FastAPI en otra terminal:

```powershell
& .\agentes\analista\.venv\Scripts\python.exe -m uvicorn agentes.analista.api.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Para desarrollo frontend, desde otra terminal:

```powershell
npm ci
npm run dev
```

Vite escucha en el puerto `3000` y pasa `/api/analista` a FastAPI en el puerto `8000`. Para previsualizar producción, ejecuta `npm run build` y luego `npm run preview` (normalmente puerto `4173`). OpenCode usa el puerto `4096`. El backend debe usar un solo worker porque conversaciones y turnos viven en memoria. No uses `--reload` durante la aceptación.

Verifica FastAPI con `Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/analista/health'`. Un HTTP 200 acredita que respondió el backend, no que el modelo pueda generar: la UI diferencia el estado del backend, OpenCode Server y capacidad de generación. La generación queda sin verificar hasta una respuesta real; 429, `MODEL_UNAVAILABLE` y timeout se muestran como estados distintos. MCP se inicia dentro de FastAPI por cada turno.

### Recuperación de cuota

Con OpenCode `2.1.2`, si el error estructurado incluye `retryAfterMs`, FastAPI publica `retry_at` y el chat muestra una cuenta regresiva local. OpenCode `2.0.27` sigue siendo compatible, pero no suele exponer ese dato. El contador no hace solicitudes ni reintenta automáticamente; el usuario conserva el botón manual. No se infiere una espera de 24 horas.

## Pruebas locales

```powershell
& .\agentes\analista\.venv\Scripts\python.exe -m pytest .\agentes\analista\tests -q
npm test
npm run build
node .\scripts\diagnostics\validate-feature-docs.mjs
```

Los tests usan dobles para aislar errores y contratos; no equivalen a una generación real. Consulta el [progreso y la evidencia](../../specs/002-chat-agente-analista/evidence/implementation-progress.md) para los resultados actuales y bloqueantes de aceptación.

Para detener servicios, usa `Ctrl+C` en sus terminales. El apagado del backend elimina las conversaciones que conserva en memoria.
