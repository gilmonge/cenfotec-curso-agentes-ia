# Tareas de implementación — Chat flotante Agente Analista

**Estado inicial:** pendientes (`[ ]`). No marcarlas como completadas sin evidencia.  
**Rama obligatoria:** `feat/chat-agente-analista` creada desde `main` actualizado.  
**Metodología:** ejecutar con Spec Kit tras `specify`, `clarify`, `plan`, `tasks` y `analyze`; confirmar las diferencias entre este borrador y los artefactos generados.

## Fase 0 — Protección y preparación (bloqueante)

- [ ] **T001 [P1]** Inspeccionar rama y estado Git; actualizar `main` sin cambios locales; crear `feat/chat-agente-analista` y comprobar que HEAD está allí. No escribir en `main`.
- [ ] **T002 [P1]** Verificar `specify version`; instalar/inicializar Spec Kit en repositorio existente si falta; instalar integraciones `opencode` y `codex`, preservando `.agents/skills` existentes.
- [ ] **T003 [P1]** Ajustar `.gitignore` para excluir estado local de OpenCode pero permitir versionar `.opencode/commands/` de Spec Kit; añadir `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/` y comprobar que `.env` nunca se agregue.
- [ ] **T004 [P1]** Ejecutar el proceso Spec Kit (constitución, especificar, aclarar, planificar, tareas, analizar) usando los documentos adjuntos; corregir inconsistencia antes de implementar.

## Fase 1 — Scaffolding y configuración

- [ ] **T005 [P1]** Crear paquete Python `./agentes/analista`, `requirements.txt` fijado, `README.md`, `.env.example` sin secretos, módulo de settings tipado.
- [ ] **T006 [P1]** Implementar carga del prompt externo `prompts/sistema.md` por ruta relativa a `__file__`, con error claro si falta y hash de versión.
- [ ] **T007 [P1]** Implementar schemas Pydantic para entrada, salida y errores: `respuesta_markdown`, cuatro clasificaciones, preguntas, fuentes y readiness.
- [ ] **T008 [P1]** Crear FastAPI con bind local, manejo central de errores y ruta `GET /api/analista/health`.

## Fase 2 — OpenCode y sesiones

- [ ] **T009 [P1]** Implementar cliente HTTP OpenCode: basic auth, timeouts, health, creación sesión y envío `POST /session/{id}/message` con extracción de partes textuales y prohibición de herramientas no permitidas.
- [ ] **T010 [P1]** Implementar abort (`POST /session/{id}/abort`) y delete (`DELETE /session/{id}`); manejar `401`, timeouts, `404`, respuestas inválidas y conexiones caídas.
- [ ] **T011 [P1]** Implementar store efímero mapeando UUID público ↔ sesión OpenCode y contexto del análisis.
- [ ] **T012 [P1]** Establecer serialización de peticiones por conversación; rechazar segundo envío con `409`; evitar bloqueo de DELETE durante una ejecución.
- [ ] **T013 [P1]** Implementar endpoints de iniciar, enviar y resetear/eliminar conversación con invalidación por generation token.

## Fase 3 — Herramientas y razonamiento

- [ ] **T014 [P1]** Crear fuentes simuladas/anonimizadas: glosario, HU aprobadas, estándares de desarrollo y checklist de vacíos con validación de formato al cargar.
- [ ] **T015 [P1]** Exponer cuatro herramientas por MCP (`consultar_glosario`, `buscar_hu_similares`, `consultar_estandares`, `aplicar_checklist_vacios`) con firma estable y **solo lectura**.
- [ ] **T016 [P1]** Integrar cliente MCP compatible con la versión instalada y el pipeline LangChain; test de descubrimiento e invocación real de herramientas.
- [ ] **T017 [P1]** Implementar pipeline LangChain que estructura el prompt, decide qué herramientas permitidas usar (máximo configurable), consume sus resultados y llama a OpenCode. No usar `ChatOpenAI` como supuesto cliente de OpenCode.
- [ ] **T018 [P1]** Implementar salida JSON del modelo, validación Pydantic y máximo un intento controlado de corrección de formato.
- [ ] **T019 [P1]** Mantener memoria del requerimiento, preguntas pendientes, hechos confirmados vs supuestos, y actualizar al recibir respuestas nuevas.
- [ ] **T020 [P1]** Impedir capacidad de shell/lectura-escritura del repositorio, webfetch e integraciones no autorizadas; documentar defensa además del prompt.

## Fase 4 — Observabilidad y resiliencia

- [ ] **T021 [P1]** Integrar Langfuse con observación por conversación/mensaje y callback de LangChain cuando corresponda; deshabilitación segura sin claves.
- [ ] **T022 [P1]** Registrar request ID, duración real, herramientas invocadas, resultado y tokens solo cuando sean conocidos; no loguear credenciales ni texto sensible.
- [ ] **T023 [P1]** Manejar falla de OpenCode/Langfuse/MCP, timeout, aborto y reintentos explícitos sin dejar conversación ocupada.
- [ ] **T024 [P1]** Confirmar que reset invalida resultados tardíos y no contamina la nueva sesión.

## Fase 5 — UI y conectividad

- [ ] **T025 [P1]** Añadir proxy Vite `/api/analista`→`http://127.0.0.1:8000`, conservando puerto 3000.
- [ ] **T026 [P1]** Implementar `src/services/analystChatApi.js` con serialización, cancelación de espera, errores tipados.
- [ ] **T027 [P1]** Implementar `useAsistenteAnalista` (open/close, messages, loading, ids, errores y reset con invalidación tardía).
- [ ] **T028 [P1]** Implementar Launcher, Window, Header, Messages y Composer con `lucide-react`, sin iconos de redes; montar globalmente una sola vez en `EnvolturaPaginaComponent.jsx`.
- [ ] **T029 [P1]** Añadir SCSS propio y responsive para escritorio, tableta y móvil, sin modificar estética general.
- [ ] **T030 [P1]** Implementar renderer Markdown GFM sin HTML crudo; probar listas, títulos, tablas, enlaces, bloques de código y ataques XSS.
- [ ] **T031 [P1]** Bloquear envío concurrente incluso con Enter/doble clic; mostrar estado de carga y mensaje de fallo recuperable.
- [ ] **T032 [P1]** Añadir botón "Nuevo chat" distinguible de "Cerrar"; permitirlo durante peticiones activas y mostrar mensajes de disponibilidad reales.

## Fase 6 — Evidencias de funcionamiento

- [ ] **T033 [P1]** Pruebas backend de schemas, 409, timeout, 404, 401 OpenCode, inyección de herramientas y reinicio en curso.
- [ ] **T034 [P1]** Pruebas frontend de bloquear envío, preservación al cerrar, reset ante respuesta tardía, Markdown y accesibilidad del teclado.
- [ ] **T035 [P1]** Pruebas e2e manuales con 3 terminales: OpenCode, FastAPI y Vite; consulta real y pregunta de seguimiento.
- [ ] **T036 [P1]** Validar clasificación PEAS, preguntas por categoría, cero datos inventados en ejemplos, sin redacción/aprobación de HU.
- [ ] **T037 [P1]** Inspeccionar en Langfuse las trazas con herramientas, latencia, IDs y errores; confirmar ausencia de secretos.
- [ ] **T038 [P1]** Ejecutar `npm run build` y pruebas; revisar diferencias para detectar modificaciones no solicitadas al Stepper y otras páginas.

## Fase 7 — Equipo y PR

- [ ] **T039 [P1]** Documentar comandos reales de instalación/arranque en Windows PowerShell; `curl`/Invoke-RestMethod de health y ejemplo de mensaje sin secretos.
- [ ] **T040 [P1]** Documentar configuración OpenCode, prompt editable, Langfuse opcional, MCP, fallos frecuentes y cómo reiniciar.
- [ ] **T041 [P1]** Ejecutar `/speckit.analyze` y `/speckit.converge` (según integración instalada) para detectar tareas faltantes y corregirlas.
- [ ] **T042 [P1]** Revisar `git status`, `git diff --check`, pruebas y secretos; commit/push solo en rama de feature y abrir PR a `main` para revisión del equipo. No fusionar automáticamente.

## Matriz mínima de aceptación (evidencia solicitada)

| Escenario | Resultado esperado | Evidencia |
|---|---|---|
| Abrir/cerrar en 3 rutas | Mantiene mensajes sin navegar | Captura/demo |
| Mensaje real a OpenCode | Respuesta de agente, no mock | Consola/trace |
| Envío doble | Solo una petición | Test frontend/API 409 |
| Respuesta con tabla y código | HTML visual seguro | Captura/test |
| Fallo de OpenCode | Error, UI recuperable | Test/registro |
| Reset durante ejecución | Chat nuevo limpio y sin respuesta antigua | Test de carrera |
| Consulta de MCP | Herramienta real y fuente simulada | Traza |
| PEAS | Clasificación y preguntas, no HU | Ejemplo anonimizado |
| Langfuse | Span correlacionado sin secretos | Captura censurada |
| Cambio en rama | PR dirigido a `main` | URL del PR |
