# Evidencia de avance ? 002-chat-agente-analista

Fecha: 2026-10-27  
Rama observada: `feat/chat-agente-analista`

## Arquitectura y OpenCode

- OpenCode Server `2.0.27` / API v2 es la unica interfaz autorizada de generacion. `opencode.jsonc` carga el prompt externo y mantiene permisos deny-all sin fijar proveedor ni modelo.
- FastAPI selecciona exclusivamente `providerID=opencode`. `OPENCODE_MODEL_ID` es opcional; si no se configura, se acepta solo el modelo default del proveedor autorizado y con precio cero publicado para input, output y cache.
- El API v2 enumero 45 modelos habilitados para `opencode`, de los cuales nueve publicaban costo cero; el total habilitado entre proveedores era 46. Se probaron esos nueve con peticiones minimas: ocho respondieron 429 `provider.quota` y uno no estuvo disponible. No se intento ningun modelo de pago.
- **T001 sigue abierta para generacion real autorizada.** [preflight-results.md](preflight-results.md) conserva la evidencia historica: la generacion que tuvo exito fue con Ollama y no verifica el proveedor autorizado `opencode`. La evidencia estructural actual y las comprobaciones sin generar se separan de ese resultado.
- **T007 verificada** con configuracion corregida: agente cargado por API v2, prompt exacto y permisos deny-all, sin generar.
- **T008 verificada** con pruebas aisladas y seleccion API v2: el cliente solo elige `opencode`, rechaza precio positivo o desconocido antes de crear una sesion y mapea 401/403, 429, 504, 503 y modelo no disponible. Esto no acredita generacion real.

## Avance implementado y pruebas

- 40 de 53 tareas verificadas en `tasks.md`. T001, E2E, evaluaciones PEAS y criterios de aceptacion medidos siguen pendientes.
- Backend: `pytest agentes/analista/tests -q` ? **67 aprobadas**; advertencia conocida de `langchain.mcp` beta.
- Frontend: `npm test -- --run` ? **6 archivos, 65 pruebas aprobadas**. Incluye regresion, validacion de contrato, Markdown seguro, cancelar/reiniciar/eliminar, timeout visual, respuesta tardia y cancelacion `pagehide`.
- Build: `npm run build` ? aprobado; Vite transformo 1.767 modulos. Sass reporta la deprecacion conocida de su API JS heredada.
- Documentos: `node scripts/diagnostics/validate-feature-docs.mjs` ? aprobado; once documentos, enlaces locales y rutas de implementacion.
- `git diff --check` aprobado. Las pruebas con mocks son unitarias/aisladas y no se presentan como generacion real.
- T027, T033 y T035 tienen pruebas aisladas de carreras y continuidad con dobles de OpenCode; esos dobles solo verifican estado y nunca se cuentan como generacion real.
- T037 congela prompt `1.0.0` con SHA-256 `f34b4e2f8d05cca703f462ec637a194bd07fde5bdde464a2ede2c64e37a1a1c9`, valida sus politicas y el reinicio requerido si cambia; T038 valida la allowlist MCP y deny-all efectivo del agente.
- Contexto: mantiene un resumen determinista del an?lisis/preguntas de hasta 2.000 caracteres y hasta seis turnos; recorta historia antigua antes del mensaje actual y compacta resultados MCP/estado bajo 24.000 caracteres.
- Continuidad: la fusion conserva IDs, turnos creados/actualizados y preguntas respondidas; retiene pendientes omitidos, deduplica texto normalizado y rechaza mas de 50 preguntas. Readiness se vuelve a derivar del analisis y preguntas consolidadas.
- El ciclo de vida del servidor rechaza `ANALISTA_CONVERSATION_TTL_SECONDS` menor o igual al deadline, limita la capacidad a 32, elimina sesiones al cancelar/expirar y conserva la pol?tica sin almacenamiento en navegador.
- Deadline total configurable mediante `ANALISTA_TURN_TIMEOUT_SECONDS` (90 s por defecto, limite de configuracion 300 s). Su vencimiento marca turno expirado, no guarda contexto, intenta interrumpir/eliminar la sesion y devuelve 504. Health publica ese mismo deadline; React cancela y aborta la peticion, conserva el mensaje fallido en la conversacion y deja el composer vacio. La cancelacion explicita sigue restaurando el borrador.
- Markdown: diez cargas maliciosas distintas quedaron inertes; detalle en [markdown-security.md](markdown-security.md).
- T007, T008, T037 y T038 se verificaron con la configuracion corregida sin repetir generacion. No se modificaron credenciales ni configuracion global, no se instalaron proveedores, y no se hicieron commits ni pushes.

## Bloqueos restantes y certificacion E2E

Hace falta un modelo ya autorizado en OpenCode (`providerID=opencode`) que tenga costo cero publicado y acceso/cuota funcional. No se debe seleccionar un modelo de pago sin autorizacion expresa. Cuando haya un modelo que responda, ejecutar T042 por React ? Vite proxy ? FastAPI ? LangChain/MCP ? OpenCode ? React; revisar fuentes, health y masking, y completar las pruebas integradas/error, estabilidad, aceptacion y PEAS que dependen de esa generacion. Los mocks no sustituyen esa evidencia.

## Reanudación y verificaciones sin generación — 2026-10-27

- **Tareas:** siguen 40/53 verificadas y 13 pendientes. T001 permanece abierta aunque su subgrupo estructural pasó; T036 y T042 no se verifican sin comportamiento/respuesta del modelo. T043–T045 y T047–T053 no se marcan por dependencias de aceptación pendientes; T051 requiere cinco usuarios.
- **T001 estructural:** ejecución actual del diagnóstico contra OpenCode v2; Basic Auth, `/api/info`, agente temporal/system, deny-all, sesión y limpieza pasaron. No se envió prompt ni se probó un modelo; la interrupción activa no fue revalidada. Detalle sanitizado en [preflight-results.md](preflight-results.md).
- **Backend:** `& .\agentes\analista\.venv\Scripts\python.exe -m pytest .\agentes\analista\tests -q` desde la raíz: **67 passed**, una advertencia conocida por `langchain.mcp` beta. Ejecutar desde `agentes/analista` no es equivalente: resuelve el paquete local `mcp` y no encuentra el namespace `agentes`; el comando documentado desde la raíz sí pasa.
- **Frontend:** `npm test`: **6 archivos, 65 pruebas aprobadas**, incluidos regresión de rutas/datos locales, accesibilidad/teclado, errores, respuesta segura y límites de scroll de 80 px.
- **Build:** `npm run build`: aprobado; 1.767 módulos transformados. Permanece el aviso conocido de API JS heredada de Sass.
- **Documentos:** `node .\scripts\diagnostics\validate-feature-docs.mjs`: aprobado; 11 documentos, enlaces locales y 11 rutas de implementación. `git diff --check`: sin errores (solo avisos Git sobre conversión LF/CRLF).
- **Responsive:** las pruebas confirman reglas CSS para ≤768 px, ≤600 px, ancho `100vw - 1.5rem`, scroll y movimiento reducido. No hubo inspección visual real a 360/768/escritorio: Computer Use rechazó vincularse a la ventana de Edge existente. El rechazo se registra; no se reintentó sobre esa ventana.
- **Seguridad/privacidad:** continúa la evidencia T046 de diez cargas Markdown; en la suite reejecutada pasan los tests de respuesta segura, que no muestran HTML/JSON crudo como respuesta. Los tests backend de observabilidad pasan, incluyendo masking de atributos sensibles, spans sin contenido y degradación ante exportación fallida. El análisis estático no encontró `console.*`, `localStorage` ni `sessionStorage` en el runtime del chat; su único `fetch` va a `/api/analista`.
- **Documentación T052:** se corrigió el comando frontend a `npm test`, se añadió el validador documental y se aclaró que FastAPI inicia MCP stdio por turno. Se amplió README con arquitectura, puertos, lockfile y comandos. T052 queda pendiente porque sus dependencias T042/T043 no se han satisfecho.
- **Certificación futura:** [manual-acceptance-checklist.md](manual-acceptance-checklist.md) contiene el protocolo de T001, T036, T042–T045 y T047–T053. Es una lista de pasos, no evidencia de aceptación.

No se hicieron commits ni pushes; la rama observada sigue siendo `feat/chat-agente-analista`. No se editaron `.env` ni configuración global de OpenCode.

## Correcciones de envío, health y entrega — 2026-10-27

- El composer se limpia al aceptar el envío y el mensaje queda en el historial. Un fallo se conserva en esa misma burbuja con su explicación y acción de reintento; 429 no rellena el composer ni duplica el mensaje. Fallos HTTP terminales usan un `request_id` nuevo al reintentar; fallos de red inciertos y `TURN_IN_PROGRESS` conservan la identidad idempotente. La cancelación explícita sigue restaurando el borrador; límites de 4.000 puntos de código y una sola operación en vuelo se mantienen.
- La interfaz informa por separado backend conectado/desconectado, OpenCode conectado/desconectado y capacidad de generación. Health HTTP 200 deja generación como `sin verificar`; éxito real la confirma y los errores distinguen modelo no disponible, cuota 429 y timeout configurado (90 s por defecto). No se ejecutó generación durante estas verificaciones ni se usó Ollama.
- `npm test`: **6 archivos, 72 pruebas aprobadas**, incluyendo limpieza inmediata, reintento de 429 y de red sin burbuja duplicada, y estados diferenciados.
- `& .\agentes\analista\.venv\Scripts\python.exe -m pytest .\agentes\analista\tests -q`: **67 pruebas aprobadas**; una advertencia conocida de API beta `langchain.mcp`. Se aisló de `.env` la prueba de selección de proveedor para evitar depender de configuración privada local.
- `npm run build`: aprobado, **1.767 módulos**; sigue el aviso conocido de Sass sobre la API JS heredada. El validador documental: aprobado, **11 documentos**, enlaces y rutas de implementación. `git diff --check`: aprobado; Git solo mostró avisos LF/CRLF.
- Responsive y accesibilidad: suites RTL verifican rutas, teclado, foco, roles, labels, scroll, y CSS contempla breakpoints ≤768 px/≤600 px y ancho desde 360 px. La inspección visual manual no pudo ejecutarse porque esta sesión no expuso navegador `iab` ni Edge controlable; no se presenta como verificación visual completada.
- Documentación sincronizada en `README-EJECUCION-LOCAL.md`, `agentes/analista/README.md` y este quickstart: `.env`, OpenCode, FastAPI, `npm run dev`, `npm run build`, `npm run preview`, health, errores y apagado. Sin secretos reales.
- El estado queda en **40/53 tareas verificadas**. No se cierran T001/T036/T042–T045/T047–T053: dependen de generación real, integración, evaluación, estabilidad o usuarios; T052 conserva además su dependencia declarada de T042/T043.

## Tiempo de recuperación de cuota y compatibilidad OpenCode 2.1.2 — 2026-10-27

- El contrato 2.1.2 expone `retryAfterMs` en `Session.StructuredError` y `provider.free-limit` cuando OpenCode recibe `FreeUsageLimitError` con tiempo de reinicio. Se amplió el cliente para aceptar explícitamente `2.0.27` y `2.1.2`; las versiones no verificadas se rechazan.
- FastAPI deriva `retry_at` de la duración recibida anclándola a `time.completed` del mensaje. React muestra que el tiempo fue informado por OpenCode, actualiza una cuenta regresiva local, no hace llamadas al terminarla y conserva el reintento manual en la misma burbuja.
- 2.1.2 se inspeccionó desde `%TEMP%\opencode-2.1.2-isolated` con perfil y password Basic de prueba efímeros. Se verificaron `/api/info`, OpenAPI, descubrimiento, sesión, deny-all, listado de mensajes, interrupt sin ejecución y borrado. No se envió prompt ni se generó texto. La instalación oficial actual continúa en 2.0.27 y no se modificó.
- `pytest agentes/analista/tests -q`: **85 aprobadas**. `npm test`: **89 aprobadas**. `npm run build`: **aprobado**, 1.768 módulos. Persisten solo los avisos ya conocidos de LangChain beta, React Router futuro y Sass legacy JS API.
- No se verificó un error real de cuota con `retryAfterMs`, una generación real ni cancelación durante generación. T001, T042 y las demás tareas pendientes conservan su estado; las pruebas simuladas no se reportan como aceptación integrada.
