# Plan técnico — Chat flotante / Agente Analista

**Estado:** Arquitectura propuesta; requiere `/speckit.plan` y revisión por el equipo.  
**Rama:** `feat/chat-agente-analista`.  
**Principio:** El navegador nunca maneja credenciales de OpenCode ni Langfuse.

## 1. Inventario verificado en `main`

- Vite 5, React 18, React Router 6, JavaScript y SCSS.
- `src/App.jsx` anida rutas dentro de `src/layouts/MainLayout.jsx`: ubicación apropiada para montar un solo componente flotante global.
- `src/pages/NewUserStory.jsx` usa análisis y generación simulada mediante `setTimeout`; **no alterar** en esta funcionalidad.
- `vite.config.js` expone el frontend en puerto 3000; añadir proxy `/api/analista` hacia el backend local, conservando la configuración actual.
- `.gitignore` ya excluye `.env` y `.env.*`, con excepción `.env.example`, pero en el árbol revisado **no** excluye `.venv/`, `__pycache__/`, `*.pyc` y `.pytest_cache/`: añadir estas exclusiones para proteger el trabajo Python.
- `.gitignore` también excluye **toda** la carpeta `.opencode/`: habrá que añadir excepciones concretas o cambiar ese patrón para poder versionar los comandos de Spec Kit para los compañeros.
- La rama `main` no contiene aún `agentes/analista`, backend, ni scaffolding `.specify/`.

## 2. Arquitectura lógica

```text
Navegador (StoryCraft AI, React:3000)
  ├─ ChatLauncher / ChatWindow / ChatMessage / ChatComposer
  ├─ hook useAnalystChat: estado, abort controller, requestId, generación actual
  ├─ ReactMarkdown + remark-gfm (sin rehype-raw)
  └─ fetch('/api/analista/...')
        │ (proxy Vite:3000 -> FastAPI:8000)
        ▼
Python — FastAPI, 127.0.0.1:8000
  ├─ router: salud, sesión, mensajes, reset
  ├─ conversation_store: memoria efímera, estado y locks por conversación
  ├─ analyzer_agent: flujo LangChain real con límites de pasos
  ├─ opencode_client: HTTP Basic Auth, /global/health, /session, /session/{id}/message,
  │                  /session/{id}/abort, DELETE /session/{id}
  ├─ mcp_bridge: llamadas MCP permitidas desde LangChain
  │      └─ local tools: glosario / HU similares / estándares / checklist
  ├─ parser: validación Pydantic del resultado
  └─ telemetry: Langfuse (observaciones y callback LangChain)
        ▼
OpenCode Server, 127.0.0.1:4096 (LLM local por HTTP)
```

> No asumir que OpenCode expone el protocolo OpenAI Chat Completions. La API del servidor OpenCode usa sesiones y mensajes propios; por ello **no** conectar `ChatOpenAI` directamente a `http://localhost:4096` sin comprobar compatibilidad explícita. Usar cliente/adaptador que implemente el contrato de OpenCode.

## 3. Propuesta de estructura

```text
agentes/
└── analista/
    ├── README.md
    ├── requirements.txt
    ├── .env.example
    ├── api/
    │   ├── main.py
    │   ├── routes.py
    │   └── schemas.py
    ├── core/
    │   ├── agent.py
    │   ├── opencode_client.py
    │   ├── mcp_tools.py
    │   ├── session_store.py
    │   ├── prompt_loader.py
    │   ├── observability.py
    │   └── settings.py
    ├── mcp/
    │   └── server.py
    ├── fuentes/
    │   ├── glosario_seguros.json
    │   ├── historias_aprobadas.json
    │   ├── estandares_desarrollo.md
    │   └── checklist_vacios.json
    ├── prompts/
    │   └── sistema.md
    └── tests/
        ├── test_api.py
        ├── test_sesiones.py
        ├── test_prompts.py
        ├── test_seguridad.py
        └── test_integracion_mock_opencode.py
src/
├── components/analista/
│   ├── AnalystChat.jsx
│   ├── AnalystChatHeader.jsx
│   ├── AnalystChatMessages.jsx
│   ├── AnalystChatComposer.jsx
│   └── AnalystMarkdown.jsx
├── hooks/useAnalystChat.js
├── services/analystChatApi.js
└── styles/_analyst-chat.scss
```

**Nota:** se permiten ajustes menores de nombres por la implementación real, manteniendo límites de responsabilidad y ubicación `./agentes/analista`.

## 4. Contrato HTTP propuesto

### `GET /api/analista/health`

Respuesta 200 cuando API disponible, incluso si los servicios dependientes están degradados:

```json
{
  "status": "ready",
  "dependencies": { "opencode": "ready", "mcp": "ready", "langfuse": "ready" }
}
```

`ready | degraded | unavailable`: la UI no simula estar "online" sin comprobarlo. No revelar secretos, IDs internos de OpenCode o datos personales.

### `POST /api/analista/conversaciones`

Respuesta 201:

```json
{"conversation_id":"<uuid-generado-por-servidor>", "status":"ready"}
```

La aplicación puede crear la sesión de OpenCode aquí o diferirla hasta el primer mensaje. El UUID público **no debe ser** el ID interno de OpenCode.

### `POST /api/analista/conversaciones/{conversation_id}/mensajes`

Entrada:

```json
{
  "request_id": "<uuid-del-cliente>",
  "mensaje": "Negocio solicita modificar la cobertura de una póliza activa..."
}
```

Respuesta 200 (ejemplo de forma; **contenido generado dinámicamente, no hardcodeado**):

```json
{
  "conversation_id": "<uuid>",
  "request_id": "<uuid>",
  "turn_id": "<uuid>",
  "respuesta_markdown": "### Análisis inicial\nFalta confirmar la vigencia...",
  "analisis": {
    "conocida": [],
    "faltante": ["Fecha de vigencia no proporcionada"],
    "supuesta": [],
    "ambigua": []
  },
  "preguntas": [
    {"categoria":"Reglas de negocio", "pregunta":"¿Cuándo debe entrar en vigencia?", "estado":"pendiente"}
  ],
  "fuentes_consultadas": ["aplicar_checklist_vacios"],
  "listo_para_redactor": false,
  "duracion_ms": 1834
}
```

- `respuesta_markdown` es texto Markdown **no HTML**.
- `analisis` y `preguntas` se validan con Pydantic, reglas estrictas y tipos cerrados.
- `fuentes_consultadas` se deriva de invocaciones MCP efectivas, no de afirmaciones libres del modelo.
- `duracion_ms` se mide realmente (valor anterior es demostrativo del formato).
- El backend usa el `request_id` para idempotencia mientras la petición siga activa (o responde 409) y para correlación de registros.
- Un solo mensaje en vuelo: **409 Conflict** si ya hay una solicitud de esa conversación.

### `DELETE /api/analista/conversaciones/{conversation_id}`

- Debe funcionar aunque la conversación esté ocupada.
- Marcar sesión como invalidada **antes** de intentar abortar llamada a OpenCode.
- Pedir `POST /session/{id}/abort` y `DELETE /session/{id}` a OpenCode con timeouts independientes; retirar la sesión del store; registrar errores no sensibles si OpenCode no responde.
- Retornar 204 cuando el contexto del backend quede invalidado. Registrar eliminación pendiente si OpenCode no pudo completarla; limpiar cuando sea posible.
- El UI incrementa `generationToken`, limpia mensajes y referencias y puede iniciar otra sesión inmediatamente; una respuesta vieja se descarta por `request_id`, `conversation_id` y token.

### Errores tipados

- 400/422: entrada inválida.
- 404: conversación inexistente o caducada.
- 409: ya se ejecuta una petición en esta conversación.
- 503: OpenCode / MCP no disponible.
- 504: tiempo límite excedido.
- 500: error controlado, sin trazas Python ni contraseñas al navegador.
- Respuesta homogénea: `{"error":{"code":"OPENCODE_UNAVAILABLE","message":"No se pudo contactar con el agente local.","request_id":"..."}}`.

## 5. Cadena real de procesamiento

1. FastAPI valida payload, estado y longitud y abre registro correlacionado.
2. Carga `prompts/sistema.md` mediante un lector dedicado; conserva versión/hash del prompt.
3. Obtiene contexto de la conversación y prepara el prompt con LangChain (por ejemplo `ChatPromptTemplate`/`RunnableLambda`, parsers tipados, composición de runnables; no importar LangChain decorativamente).
4. Un planificador controlado solicita al modelo —mediante `OpenCodeClient`— la selección de fuente(s) requerida(s), sujeta a allowlist y límite de pasos (propuesto: máximo 4 herramientas por turno). No usar `create_agent` con un cliente no compatible con tool-calling de LangChain.
5. Ejecución de herramientas **mediante MCP real**; fuentes almacenadas solo en archivos de ejemplo locales, sin acceso genérico a sistema de archivos. En versiones compatibles, utilizar `langchain.mcp.MCPAdapter` o una interfaz equivalente verificada; fijar versiones para evitar conflictos de protocolos MCP.
6. Compone el resultado final del modelo y valida el JSON con Pydantic. Si requiere reparar formato, limitar a **un** intento y dejar traza; jamás devolver datos inventados como relleno.
7. Devuelve `respuesta_markdown` más estructuras tipadas y actualiza memoria de la sesión.
8. Envía span y observaciones a Langfuse sin bloquear el resultado del chat ante fallos de telemetría.

**Observación crítica de compatibilidad (octubre de 2026):** el SDK oficial MCP v2 cambió `FastMCP` por `MCPServer`, y el soporte MCP se movió al namespace `langchain.mcp`. No copiar imports de tutoriales de MCP v1 sin fijar versiones y ejecutar un smoke test. Si se usa el paquete externo `fastmcp`, documentar cuál es y la versión.

## 6. Memoria y concurrencia

- `conversation_id` apunta en el backend a un `OpenCode session id`, historia y estado transitorio. Un modelo de `conversation_store` en memoria es suficiente para una demo de una instancia.
- Se reutiliza una sesión OpenCode por conversación para memoria conversacional. No reenviar indiscriminadamente todo el historial en cada turno si OpenCode ya lo retiene: evitar memoria duplicada.
- El historial tipado en Python sirve para mostrar/validar estado y entregar contexto normalizado de preguntas; el historial de LLM permanece en OpenCode.
- Al reiniciar, invalidar primero por generación, abortar sesión en curso y borrar el identificador. El cliente usa AbortController pero **eso solo cancela la espera del navegador**, no el proceso remoto: también debe existir aborto del lado Python/OpenCode.
- Un `asyncio.Lock` por conversación para enviar; la ruta DELETE debe quedar fuera de ese lock para poder cancelar. Control de carrera mediante token `generation` y `closed`.
- Estado en memoria: se pierde si Python reinicia. Al recibir 404, presentar "La sesión expiró. Inicie un chat nuevo".

## 7. UX y Markdown

- Montar `<AnalystChat />` una vez en `src/layouts/MainLayout.jsx`, fuera de `<Outlet />`.
- Icono Lucide `MessageCircle`; encabezado con nombre, botón `X` para cerrar y `Trash2` o `RotateCcw` con etiqueta para nuevo chat.
- Sin avatar de identidad real, sin redes sociales y sin leyenda "online" si el health check no lo confirma.
- Tamaño escritorio sugerido 380–420px ancho / 500–620px alto, limitado por viewport; móvil `calc(100vw - 24px)` y altura adaptativa; respetar safe areas.
- Enviar con Enter; Shift+Enter agrega salto; textarea accesible. Mientras espera puede escribir borrador, pero no enviar. Indicar cargando y feedback de errores.
- `react-markdown` + `remark-gfm` (tablas, listas) con soporte de bloques de código. No instalar `rehype-raw`; si se habilita HTML en el futuro, sanitizar con allowlist estricta.
- Estilos dedicados `_analyst-chat.scss` usando variables SCSS existentes; no modificar el tema global.

## 8. Configuración y seguridad

Ejemplo **sin secretos** para `agentes/analista/.env.example`:

```env
OPENCODE_SERVER_URL=http://127.0.0.1:4096
OPENCODE_SERVER_USERNAME=opencode
OPENCODE_SERVER_PASSWORD=CAMBIAR_EN_ENTORNO_LOCAL
ANALISTA_HOST=127.0.0.1
ANALISTA_PORT=8000
ANALISTA_REQUEST_TIMEOUT_SECONDS=90
ANALISTA_MAX_TOOL_CALLS=4
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

- El archivo `.env` real jamás se versiona ni se usa en `import.meta.env` del frontend.
- El script de arranque de OpenCode utiliza `OPENCODE_SERVER_PASSWORD`; verificar health (`GET /global/health`) y probar un mensaje mínimo.
- No abrir CORS `*` ni bind `0.0.0.0` por defecto.
- OpenCode tiene herramientas potencialmente capaces de leer/escribir archivos. Desactivar explícitamente todas las ajenas a su tarea en el mensaje y en la configuración de permisos del servidor; no depender solo del prompt.
- Traces Langfuse: session ID, request ID, duración, categorías, herramientas, errores, tokens solo cuando el proveedor lo informa; evitar texto de usuario no anonimizado y rotar credenciales de ejemplo que hayan quedado expuestas.

## 9. Paquetes a evaluar y fijar en el lockfile

- Python: `fastapi`, `uvicorn`, `httpx`, `pydantic`, `pydantic-settings`, `python-dotenv`, `langchain`, `langfuse`, `mcp`/`fastmcp` según versión y conector MCP, `pytest`, `pytest-asyncio`, `respx` (o httpx MockTransport).
- React: `react-markdown`, `remark-gfm`; iconos reutilizados de `lucide-react`.
- Evitar `langchain-openai` **como cliente de OpenCode** por defecto: no equivale al protocolo de sesiones OpenCode.
- Antes de fijar versiones, ejecutar la prueba mínima entre MCP y LangChain de **la versión concreta seleccionada**.

## 10. Estrategia de pruebas

**Backend:** modelo de respuesta Pydantic; parsing; validaciones; rechazo concurrente; falta de configuración; timeout; 401 de OpenCode; sesión inválida; reset durante bloqueo; limitación de herramientas; sólo lectura; correlación Langfuse, fallos opcionales de telemetría.

**Frontend:** abrir/cerrar; Enter vs Shift+Enter; sin duplicar envío; carga; render Markdown/GFM seguro; Error UI; reset con respuesta tardía; responsive y teclado.

**Integración real controlada:** tres terminales (OpenCode, FastAPI, Vite), mensaje corto, seguimiento, respuesta con Markdown, fallo inducido, reset, observación en Langfuse. No usar datos empresariales reales.

## 11. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Versión OpenCode diferente del prototipo | Usar OpenAPI del servidor real (`/doc`); clientes de sesión actuales; test 200/401/404/405. |
| Modelo bloqueado | Timeout + cancelación HTTP + abort remoto + invalidación de generación. |
| LangChain no llama realmente al LLM | Prueba de integración con adaptador y traza de la cadena; no fingir `create_agent` si no hay `bind_tools`. |
| Incompatibilidad MCP 1/v2 | Fijar dependencias, smoke test y usar SDK/adapter compatible. |
| HTML inseguro en Markdown | No permitir HTML crudo, validar enlaces y realizar prueba XSS. |
| Variables sensibles expuestas | Secretos solo en Python `.env` local; revisar `git status`, `.gitignore`, build JS y salida de errores. |
| `.opencode/` ignorado | Versionar comandos Spec Kit pero seguir ignorando estado local de OpenCode. |
| Confusión de roles de agentes | El Analista solo aclara y pregunta; no genera/aprueba HU. |
| Backend en memoria reinicia | Respuesta 404 y botón de chat nuevo; persistencia definitiva fuera de alcance. |

## 12. Orden recomendado

1. Preparar rama + Spec Kit + principios.
2. API de salud y puente OpenCode.
3. Servicio de herramientas MCP y pipeline LangChain.
4. Esquema estructurado, memoria, límites, reset, Langfuse.
5. Frontend y estilos, Markdown.
6. Tests + auditorías, documentación y pull request.
