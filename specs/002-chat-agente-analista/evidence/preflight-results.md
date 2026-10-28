# Evidencia de compuertas T001 y T002

Fecha de ejecución: 2026-10-26. Entorno: Windows PowerShell, Python 3.12.10, rama `feat/chat-agente-analista`. Las pruebas usaron carpetas desechables bajo `%TEMP%`; no se leyeron ni guardaron secretos ni contenido del prompt.

## Historial: intento con OpenCode 0.2.27/API v1 (bloqueado y superado por la compuerta v2)

- El `opencode` disponible inicialmente reportó `v2.0.27`, incompatible con el pin contractual `0.2.27`; no se asumió compatibilidad ni se cambió el pin.
- Se descargó e invocó el binario oficial `opencode-windows-x64@0.2.27` únicamente bajo `%TEMP%`; `--version` reportó `0.2.27`.
- El servidor aislado se lanzó con `serve --hostname 127.0.0.1 --port 4096`, `OPENCODE_CONFIG` temporal y un prompt externo temporal. También se probó sin configuración en el puerto loopback `14096` para aislar el fallo.
- En ambos arranques, el proceso terminó con código 0 antes de abrir el puerto. El log del segundo intento llega a `models.dev refreshing`, `provider init` y `lsp shutdown`; no aparece listener. El endpoint `/global/health` no aceptó conexión.
- Diagnóstico adicional: `--help` y `serve --help` funcionan al redirigir `USERPROFILE`, `APPDATA` y `LOCALAPPDATA` a `%TEMP%`. Con el perfil normal, el binario intenta crear `C:\Users\gilbe\.config\opencode\providers` y falla con `EPERM`. Con perfil, datos, configuración y prompt aislados en `%TEMP%`, `OPENCODE_CONFIG` y credenciales sintéticas, el servidor fue ejecutado en primer plano y como proceso oculto; en ambos casos terminó con código 0 después de `models.dev refreshing`, `provider init` y `lsp shutdown`, sin abrir el puerto. Repetirlo con ejecución aprobada tampoco cambió el resultado.
- Por tanto, no se consultaron `/doc`, `/agent`, Basic Auth, permisos efectivos, resolución del prompt, generación, aborto ni eliminación. T001 queda sin marcar y bloquea T007–T009 y las integraciones que requieren OpenCode real hasta que pueda arrancarse el pin y completarse el preflight.
- Evidencia de versión y arranque: binario npm oficial `opencode-windows-x64@0.2.27`; logs sanitizados en `%TEMP%\spec002-t001-opencode\isolated\plain.stderr.log` y `%TEMP%\spec002-t001-opencode\isolated-profile\server.stderr.log`. No se copiaron logs, credenciales sintéticas ni prompt al repositorio.

## T002 — LangChain, MCP/FastMCP y Langfuse: PASS

Entorno desechable: Python 3.12.10, creado con `uv.exe venv`; paquetes instalados en el venv temporal con:

```powershell
uv.exe pip install --python <TEMP>\spec002-t002-preflight\.venv\Scripts\python.exe langchain==1.4.7 fastmcp==4.1.4 mcp==2.3.0 langfuse==5.0.4
```

Versiones observadas: `langchain 1.4.7`, `langchain-core 1.7.0`, `fastmcp 4.1.4`, `mcp 2.3.0`, `langfuse 5.0.4`, `pydantic 2.14.1` y `langgraph 1.2.18`.

- **LangChain:** importaron `ChatPromptTemplate`, `RunnableParallel`, `RunnableLambda`, `PydanticOutputParser` y `langchain.mcp.MCPAdapter`. Se ejecutó una composición paralela y parseo Pydantic sintético: PASS.
- **MCP/FastMCP:** un servidor FastMCP sintético arrancó por stdio. El cliente MCP listó la herramienta y esquema, obtuvo salida estructurada válida y rechazó argumentos inválidos: PASS. `MCPAdapter(Path(...))` abrió ese servidor stdio, listó la herramienta y ejecutó una llamada: PASS.
- **Langfuse:** un span sintético se procesó con `mask_otel_spans` y `InMemorySpanExporter`; el valor sensible sintético no apareció en los spans exportados y sí apareció el marcador de masking: PASS. Inicialización/flush/shutdown con tracing deshabilitado y sin claves: PASS; el SDK dejó el cliente deshabilitado.
- **Límites:** `langchain.mcp` emite advertencia de API beta; su uso queda sujeto a las pruebas de contrato backend T012. No se enviaron trazas a un servicio externo. El probe no sustituye las pruebas automatizadas del producto ni una integración E2E.
- **Comandos de probes:** `probe_imports.py`, `probe_mcp.py`, `probe_langchain_mcp.py` y `probe_langfuse.py`, todos creados y ejecutados bajo `%TEMP%\spec002-t002-preflight` con datos sintéticos.

T002 está marcada completa porque cada capacidad exigida en su preflight fue ejecutada y verificada. Los bloqueos posteriores de OpenCode no cambian el resultado de esta compuerta independiente.

## Diagnóstico adicional T001 — 2026-10-26

- Se añadió `scripts/diagnostics/opencode-t001-diagnose.ps1` para capturar versión binaria por hash, argumentos, PID, muestras del estado, escucha loopback, código de salida y logs sanitizados. Los artefactos se guardan en un directorio único bajo `%TEMP%`; no se guardan credenciales, valores de variables sensibles, prompt ni configuración personalizada.
- Ejecución del binario Windows oficial `opencode-windows-x64@0.2.27`: `serve --hostname 127.0.0.1 --port 60511`; SHA-256 `D5C9DEB17DD6269FDF727B42B0C90E02158E108DD762BAEAB30A3048E1CFE5FB`; PID `17028`; duración `0.749 s`; código de salida `0`; nunca aceptó conexión en loopback. El proceso estuvo vivo en la primera muestra y ya había terminado en la segunda. La salida estándar y stderr directas estaban vacías; el log interno aislado terminó en `models.dev refreshing`, `provider init`, `lsp shutdown`. No se heredaron credenciales ni se usó configuración/prompt personalizado en esta ejecución.
- **Causa del cierre con código 0:** en el tag fijado `v0.2.27`, `serve` obtiene `Provider.list()` y retorna `needs_provider` si no hay proveedores; solo después llama a `Server.listen()` y queda en espera. `Provider.list()` depende de claves de entorno reconocidas, autenticación local o proveedor configurado, y descarta proveedores sin modelos. Por ello este cierre no es un fallo del puerto: el proceso abandona la rama de servidor cuando su lista efectiva de proveedores queda vacía. Código del pin: [serve.ts](https://github.com/anomalyco/opencode/blob/v0.2.27/packages/opencode/src/cli/cmd/serve.ts#L339-L365) y [provider.ts](https://github.com/anomalyco/opencode/blob/v0.2.27/packages/opencode/src/provider/provider.ts#L1815-L1878).
- En el diagnóstico aislado no había credenciales/provider reales; las ejecuciones previas con valores sintéticos tampoco registraron un proveedor encontrado. No se puede afirmar que una generación real, Basic Auth, `/doc`, `/agent`, permisos, aborto o eliminación pasen sin una fuente local de autenticación/proveedor válida. No se leyó ni se copió el almacén local de autenticación.
- **Estado histórico de T001 en ese intento: BLOQUEADA.** Para continuar entonces hacía falta un proveedor real en el perfil aislado. Este bloqueo fue superado al reanudar el trabajo contra el servidor manual real; ver el resultado final al final del documento.
- Artefactos del diagnóstico actual (solo `%TEMP%`): `spec002-t001-diagnose-20261026-194408/diagnostic.json`, `stderr.log`, `stdout.log` y `xdg-data/opencode/log/2026-10-27T014409.log`. La ejecución actual no usó `--print-logs`; el script reutilizable ahora lo agrega y sanitiza también el log interno.

## Diagnóstico inicial previo a credencial local — 2026-10-26

- El servidor local responde en `http://127.0.0.1:4096` y entrega la interfaz de OpenCode. Las solicitudes `GET /global/health` y `GET /doc` respondieron `200 text/html` con el mismo shell de la interfaz; no devolvieron health JSON ni OpenAPI.
- El bundle servido publica rutas bajo `/api/`, incluyendo agente, proveedor, modelo, sesión, mensaje y `interrupt`. Esto difiere de las rutas v1 propuestas en `contracts/opencode-v1.md` y no demuestra que el contrato fijado `0.2.27` sea compatible.
- `GET /api/info`, `/api/agent`, `/api/provider`, `/api/model` y `/api/doc` exigen Basic Auth (`401`, realm `Secure Area`). Las credenciales configuradas localmente en `.env` fueron rechazadas (`401`); no se imprimieron ni copiaron. No hay credencial aceptada disponible en la configuración local actual.
- **No verificados por el bloqueo de autenticación/schema:** versión exacta del servidor, OpenAPI, proveedor y modelo configurados, generación real, permisos efectivos, cancelación y eliminación. No se crearon ni listaron sesiones del usuario.
- **Estado histórico de T001 antes de recibir la credencial: BLOQUEADA.** Se resolvió cuando la clave temporal se incorporó localmente a `.env` y se comprobó el contrato v2; ver el resultado final de T001 abajo.

## Resultado final T001 con el servidor existente — 2026-10-26

- No se inició ni reinició OpenCode. El listener `127.0.0.1:4096` pertenece al PID `34160`; el ejecutable real es `C:\Users\gilbe\AppData\Roaming\npm\node_modules\@opencode\cli\bin\opencode.exe`, y ese mismo binario reportó `opencode v2.0.27`.
- La contraseña temporal se introdujo localmente en configuración `.env` ignorada por Git. Basic Auth con usuario `opencode` pasó; no se imprimió ni registró la contraseña. `GET /api/info` devolvió `200`, `version=2.0.27` y el mismo PID.
- `/global/health` y `/doc` devuelven HTML de la interfaz y no se usaron como contrato API. La referencia se contrastó con [OpenCode API v2](https://dev.opencode.ai/v2/docs/api), [OpenAPI v2](https://dev.opencode.ai/v2/openapi.json), [agentes](https://dev.opencode.ai/v2/docs/agents/), [permisos](https://dev.opencode.ai/v2/docs/permissions/) y [configuración](https://dev.opencode.ai/v2/docs/config/).
- Descubrimiento autenticado: siete agentes integrados; dos proveedores (`opencode`, `ollama`); 46 modelos. El default `opencode/flint-40b-free` falla con `finish=error`, `provider.quota`, status `429`. Se comprobó generación real con `ollama/qwen3:4b-instruct-2507-q4_K_M`.
- El agente v2 temporal se registró desde `.opencode/agents/t001-preflight.md`; el cuerpo system y la regla `permissions: [{action:"*",resource:"*",effect:"deny"}]` aparecieron en la API. La sesión aceptó y devolvió las mismas reglas deny-all. El intento controlado de herramienta no produjo ejecución (`shell_tool_executed=false`).
- Generación: `POST /api/session/{id}/prompt` admitió el texto (`200`); `GET /api/session/{id}/message` devolvió el mensaje assistant v2 directamente en `data[]`, con `type`, `content`, `time.completed`, `model` y `finish=stop`; el marcador sintético estuvo presente. No se guardaron los textos ni los IDs.
- Cancelación: la admisión de un mensaje largo seguida de `POST /api/session/{id}/interrupt` devolvió `interrupted=true`. Eliminación: ambas sesiones temporales recibieron `DELETE 204` y luego `GET 404`; no se listaron sesiones ajenas.
- Diferencias de esquema confirmadas: `Model.Ref` de sesión usa `{id,providerID}`; mensajes assistant usan `content[]` directamente y no `{info,parts}`; `/prompt` es admisión durable, no generación síncrona; `/interrupt` devuelve `{interrupted}` directamente.
- Batería reutilizable: `node scripts/diagnostics/opencode-v2-t001.mjs`; resultado sanitizado `all_t001_checks_passed=true`. **T001: PASS HISTÓRICO para el protocolo y la generación con Ollama; no verifica la generación actual mediante `opencode`.** Ver el addendum del 2026-10-27. No se repitieron pruebas exitosas al actualizar esta evidencia.

## Configuración final del agente v2 (T007)

- `opencode.jsonc` se cargó en el location del proyecto sin reiniciar ni iniciar otro servidor. `GET /api/agent` confirmó `analista`, sustitución del prompt desde `agentes/analista/prompts/sistema.md` (contenido no vacío, con marcador del archivo), modelo `ollama/qwen3:4b-instruct-2507-q4_K_M` y deny-all.
- La ruta del prompt se validó con un marcador ASCII del propio archivo; la respuesta solo guardó booleanos, longitud, proveedor/modelo y deny-all, no el prompt.

## Revisión arquitectónica: separar evidencia histórica y requisito vigente — 2026-10-27

La evidencia anterior se conserva como registro de lo que ocurrió el 2026-10-26; sus resultados no satisfacen la arquitectura ahora obligatoria:

- **Con Ollama:** la única generación real exitosa registrada fue `ollama/qwen3:4b-instruct-2507-q4_K_M`. Esa llamada verificó que el servidor podía producir una respuesta, pero no verificó el proveedor autorizado `opencode`.
- **Contra OpenCode v2, sin acreditar generación:** se verificaron históricamente Basic Auth, versión/API, agente temporal, permisos deny-all, sesión, interrupt y eliminación. La selección de modelos consultó el API v2.
- **Con `providerID=opencode`:** el default histórico y los nueve modelos de costo cero enumerados en 2026-10-27 no produjeron una respuesta: ocho devolvieron 429 y uno no estuvo disponible. No se usaron modelos de pago. No hay generación confirmada con `opencode`.
- **Configuración corregida:** `opencode.jsonc` ya no fija modelo alguno; el cliente Python solo selecciona `opencode` y acepta un `OPENCODE_MODEL_ID` opcional o un default que pertenezca a ese proveedor. Pruebas aisladas validan esta política y el mapeo de errores; no se consideran evidencia de generación real.
- **Estado de tareas:** T001 permanece abierta hasta que un modelo `opencode` ya autorizado complete una generación real y se verifique su ciclo de vida. T007/T008 se comprueban por separado con la configuración corregida. El 429 bloquea generación y E2E, no las tareas independientes.

## Prueba adicional de modelos con precio cero — 2026-10-27

- La API v2 enumeró 45 modelos habilitados bajo `opencode`, de los cuales nueve publican costo cero para entrada, salida y caché. El cliente valida ese metadato antes de abrir una sesión.
- Se intentó una solicitud mínima aislada a cada uno de los cuatro modelos de costo cero que faltaban respecto de las pruebas anteriores: `nemotron-3.5-super-vl-free` → 429 `provider.quota`; `nemotron-3.5-lightning-free` → 429 `provider.quota`; `nemotron-3-ultra-free` → `OPENCODE_UNAVAILABLE`; `big-pickle` → 429 `provider.quota`.
- Sumadas al default gratuito y los otros cuatro gratuitos probados antes, los nueve modelos de costo cero listados no dieron respuesta: ocho 429 y uno no disponible. No se intentó ningún modelo con precio positivo. No se imprimieron respuestas, credenciales ni IDs de sesión; la limpieza de sesión corre en `finally`.
- **T001 continúa abierta.** No hay evidencia de generación exitosa mediante `opencode`; los modelos pagos listados no son candidatos autorizados y el cliente los rechaza antes de crear una sesión.

## Revalidación estructural sin generación — 2026-10-27

Se ejecutó `node .\scripts\diagnostics\opencode-v2-t001.mjs` contra el OpenCode existente. No se habilitó `T001_ALLOW_MODEL_GENERATION`, no se configuró `T001_MODEL_ID` para generación y no se enviaron prompts; no se consultó a los modelos gratuitos que ya habían respondido 429.

- `/api/info`: HTTP 200; OpenCode `2.0.27`, API v2, PID `34160`; Basic Auth aceptada.
- El agente temporal se cargó desde la ubicación de proyecto y su system contenía el marcador de prueba; permisos deny-all presentes.
- Los metadatos listaron 46 modelos y default `opencode/flint-40b-free`. Este identificador ya tenía un 429 documentado; la nueva ejecución no lo invocó.
- Se creó una sesión temporal sin enviar prompt, se reflejaron permisos deny-all y se eliminó la sesión (DELETE 204 y GET posterior 404).
- `structural_t001_checks_passed=true`; `model_generation_skipped=true`; `all_t001_checks_passed=false` porque la generación fue omitida. Esta corrida no revalidó interrupt de una generación activa.
- El script limpió el agente temporal en `finally`. No inició, detuvo ni reinició el servidor. No se guardaron secretos, prompt, respuestas ni IDs de sesión.

**Resultado:** evidencia estructural adicional para T001; T001 permanece abierta. El paso pendiente es una generación real con `providerID=opencode` autorizado y el ciclo de vida asociado, únicamente después de que haya evidencia de cuota disponible.
