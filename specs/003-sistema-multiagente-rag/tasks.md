# Tareas: Sistema multiagente para Historias de Usuario

**Spec**: [spec.md](spec.md)  
**Plan**: [plan.md](plan.md)  
**Estado**: T005-T029, T037-T050 y T055-T060 implementadas; T030-T032 y T053-T054 verificadas con automatizacion local y reporte reproducible. T001 sigue abierto: PR #4 fue fusionada, pero GitHub indica que no tiene reviews y la constitucion mantiene la ratificacion pendiente. T002 se contrasto contra el texto 2.0.0, pero no se puede cerrar como ratificacion final mientras T001 siga abierto. La implementacion experimental no declara aceptacion formal de la feature.

> T005-T009 y T055-T060 se implementaron primero. Por instrucción posterior se implementó T010-T018 en modo experimental; también se creó el fixture T038 por requisito explícito del Asesor. La evidencia de GitHub no permite cerrar T001: PR #4 fue fusionada sin reviews y la constitución aún declara ratificación pendiente. T002 se revisó contra el texto 2.0.0, pero queda pendiente su cierre formal. Este avance técnico no representa aceptación formal.

## Fase 0 — Puertas de gobernanza (aceptación formal pendiente)

- [ ] T001 La [PR correctiva #4](https://github.com/gilmonge/cenfotec-curso-agentes-ia/pull/4) esta fusionada, pero GitHub registra `No reviews` y `.specify/memory/constitution.md` conserva `Ratification status: pending a human approval recorded in GitHub`. Falta aprobacion humana verificable; no se marca como completada.
- [ ] T002 Se reviso `spec.md` frente al texto constitucional 2.0.0 y no se detectaron contradicciones para esta fase; el cierre formal depende de la ratificacion verificable de T001.
- [x] T003 Ejecutar análisis de consistencia Spec Kit sobre spec, plan y tareas; corregir hallazgos documentales y registrar decisiones técnicas en `research.md` y el reporte de análisis. La discrepancia constitucional queda bloqueada por T001.
- [x] T004 Confirmar Python 3.12 desde el Dockerfile actual; fijar en el contrato requerimiento ≤4.000 caracteres, solicitud de cambio ≤2.000 y una operación activa por workflow; documentar la presentación/reanudación de interrupciones y la pérdida de checkpoint tras reinicio.

## Fase 1 - Fundamentos (alcance ejecutado por instruccion expresa; ratificacion T001 pendiente)

- [x] T005 Anadir LangGraph, `pinecone` y `langchain-pinecone` con pins compatibles con Python 3.12; validar construccion de `PineconeEmbeddings` + `PineconeVectorStore` con catalogo/indice simulados y sin red, y regenerar el lock preservando los 106 pins previos; se anadieron solo paquetes faltantes. Evidencia: `requirements.txt`, `requirements.lock`, `tests/unit/test_vector_store_dependency_contract.py`.
- [x] T006 Escribir primero pruebas unitarias de contratos tipados, serializacion del estado, ruteo y flujo nominal con dobles. Evidencia: `tests/unit/test_workflow_foundation.py`, `tests/integration/test_workflow_agent_isolation.py`.
- [x] T007 Definir estado `WorkflowState` y contratos Pydantic serializables para workflow, HU en borrador, evidencia tecnica y recomendacion de cambio; se conservan los modelos actuales del Analista. Evidencia: `core/workflow_models.py`.
- [x] T008 Implementar `StateGraph` compilado con `InMemorySaver`, ruteo explicito por modo y `WorkflowRuntime`; los IDs `thread_id` quedan internos al runtime en memoria y no se devuelven en snapshots. Evidencia: `core/workflow_graph.py` y pruebas de checkpoint.
- [x] T009 Reutilizar `core/observability.py` para spans correlacionados de etapa/agente, con metadatos operativos sin prompts o respuestas; probar backend deshabilitado y fallo de exportacion sin detener el flujo.

## Fase transversal — Configuración y aislamiento de agentes OpenCode

- [x] T055 Anadir primero pruebas con OpenCode simulado para los cuatro agentes, agente desconocido, deny-all y aislamiento de contexto/herramientas. Evidencia: `tests/unit/test_opencode_agent_selection.py`, `test_agent_registry.py` y `test_orchestrator.py`.
- [x] T056 Registrar los cuatro identificadores en `opencode.jsonc` con prompt externo, modo y permisos explicitos deny-all; prueba de estructura JSON/config en `test_agent_registry.py`.
- [x] T057 Mantener intacto el prompt del Analista y anadir prompts versionados para Redactor-Revisor, Asesor Tecnico y Gestor de Cambios con contratos, limites y herramientas backend indicadas; OpenCode permanece deny-all.
- [x] T058 Mantener deny-all en OpenCode y aplicar `MCP_TOOL_ALLOWLIST`/`AGENT_NAMESPACE_ALLOWLIST` desde el backend antes de invocar MCP; probar permisos por rol y namespace, incluidos shell/filesystem y namespaces cruzados.
- [x] T059 Extender `OpenCodeClient` para cargar/verificar el prompt del agente seleccionado y usar ese ID al crear sesion; agente desconocido o discrepancia produce error controlado sin fallback.
- [x] T060 Probar seleccion/prompt, deny-all, allowlist MCP, rechazo de acciones no autorizadas y separacion de checkpoints/contextos; pytest usa dobles, no servicios reales.

## Fase 2 — Analista y espera de Negocio (US1)

- [x] T010 Añadir pruebas de no regresión del Analista existente y pruebas de loop de preguntas, pausa y reanudación por `Command(resume=...)`. Evidencia: pruebas existentes de `run_turn` más `tests/integration/test_workflow_analyst_writer.py`.
- [x] T011 Adaptar el Analista existente como nodo sin cambiar su responsabilidad ni salida contractual. El nodo llama `orchestrator.run_turn` y valida su `AgentTurnResponse` existente.
- [x] T012 Implementar `espera_negocio` con `interrupt()` y `BusinessAnswerSubmission`; `WorkflowRuntime.resume` usa `Command(resume=...)` y vuelve a ejecutar Analista antes de decidir si continúa.

## Fase 3 — Redactor y revisión (US2)

- [x] T013 Probar Como/Quiero/Para, criterios Dado/Cuando/Entonces, salida estructurada y ausencia de decisión de aprobación. Evidencia: `tests/unit/test_redactor_revisor.py`.
- [x] T014 Integrar el prompt externo existente y nodo Python Redactor-Revisor, usando OpenCode a través del cliente existente y LangChain para prompt/parsing.
- [x] T015 Implementar revisión con contador limitado a dos rondas y observaciones estructuradas; al agotar rondas la historia queda `needs_attention` y espera al PO, sin aprobarse. Evidencia de integración con OpenCode simulado en `tests/integration/test_workflow_analyst_writer.py`.

## Fase 4 — Asesor Técnico (US3)

- [x] T016 Crear fixtures versionados de estándares y repositorio ficticio Python `ejemplos/polizas_demo/` en allowlist read-only; excluir filesystem libre y repositorios reales. El fixture de aplicación es `1.0.0` e incluye modelos, pólizas, coberturas, primas, renovaciones, pagos, validaciones y mapa de dependencias.
- [x] T017 Añadir pruebas unitarias y de integración con OpenCode/MCP simulados para evidencia consultada, falta de evidencia, referencias no recuperadas y ausencia de decisión de alcance. Evidencia: `tests/unit/test_technical_advisor.py`, `tests/integration/test_workflow_technical_advisor.py` y `tests/contract/test_technical_mcp_stdio.py`.
- [x] T018 Implementar herramientas MCP read-only y nodo LangGraph del Asesor; OpenCode usa `asesor_tecnico` y su prompt independiente. Resultado estructurado identifica módulos, dependencias, riesgos, procesos críticos, fuentes consultadas e incertidumbre; se rechazan citas no recuperadas.

## Fase 5 — Aprobación del PO y repositorio de HU (US4)

- [x] T019 Probar primero interrupción PO, aprobación humana, devoluciones a Analista/Redactor/Asesor con motivo, rechazo/detención, decisiones inválidas y cero escrituras sin aprobación. Evidencia: `tests/integration/test_workflow_po_approval.py`.
- [x] T020 Implementar `aprobacion_po` con `interrupt()`, decisión humana Pydantic y reanudación con `Command(resume=...)` sobre el mismo `thread_id`; solo enrutar a `repositorio` ante `aprobar` explícito.
- [x] T021 Implementar `repositorio` con `RepositorioHU.guardar_hu`, payload conforme al contrato real, UUID del workflow como clave idempotente y resultado de persistencia estructurado; pruebas usan un doble, sin tocar TiDB.

> Baseline previa a T019-T021 (2026-11-21): desde la raiz, `agentes/analista/.venv/Scripts/python.exe -m pytest agentes/analista/tests` ejecuto 189 pruebas, todas aprobadas (1 advertencia de LangChain MCP beta). Verificacion posterior a T019-T021: 199 pruebas aprobadas. Verificacion posterior a T022-T024 (2026-11-21): 213 pruebas aprobadas, 1 advertencia; incluye dobles y SQLite temporal, sin secretos, servicios externos ni TiDB real.
> Verificación posterior a T025-T026 (2026-11-21): `agentes/analista/.venv/Scripts/python.exe -m pytest agentes/analista/tests` ejecutó 221 pruebas; todas aprobadas, 1 advertencia de LangChain MCP beta. Las pruebas nuevas usan TestClient y dobles; no contactan OpenCode, MCP, TiDB ni servicios externos reales.
> Verificación de T027-T029 (2026-11-21): `npm test -- --run` ejecutó 232 pruebas en 37 archivos, todas aprobadas; `npm run build` completó (avisos Sass legacy y bundle >500 kB); `agentes/analista/.venv/Scripts/python.exe -m pytest .\agentes\analista\tests -q` ejecutó 221 pruebas, todas aprobadas y 1 advertencia LangChain MCP beta. `node .\scripts\diagnostics\validate-feature-docs.mjs` pasó. Los tests UI simulan API workflows; no contactan servicios externos.

## Fase 6 — Gestor de Cambios y decisión humana (US5)

- [x] T022 Anadir primero pruebas para HU inexistente/no aprobada, fragmentos comparativos verificables, ambas clasificaciones, impacto y justificacion, lecciones propuestas, decision humana obligatoria, reanudaciones invalidas/duplicadas y cero escrituras antes de decidir. Evidencia: `tests/integration/test_workflow_change_management.py`, `tests/unit/test_repositorio.py`.
- [x] T023 Implementar `gestor_cambios` con OpenCode `agent_id=gestor_cambios`, prompt externo y lectura solo desde `RepositorioHU.obtener_hu`; Pydantic restringe `aclaracion`/`cambio_alcance`, valida comparaciones contra texto literal de la HU y solicitud, e incluye impacto, incertidumbres y lecciones propuestas. No aprueba ni aplica cambios.
- [x] T024 Implementar `decision_humana` con `interrupt()` y reanudacion validada por `Command(resume=...)` en el mismo hilo; aplicar/rechazar/devolver con controles idempotentes. Las aclaraciones solo se registran, los cambios de alcance y devoluciones disparan un nuevo analisis que espera aprobacion PO, y las lecciones requieren decision humana explicita. Evidencia: `tests/integration/test_workflow_change_management.py`.

## Fase 7 — API, frontend y documentación

- [x] T025 Añadir pruebas de contrato con FastAPI TestClient, WorkflowRuntime real y dobles OpenCode/MCP/RepositorioHU: pre/post-grooming, consulta, respuestas de Negocio, decisiones PO/cambio, validación de cuerpo/tamaño, concurrencia simultánea, reanudación incorrecta/duplicada, checkpoint perdido, timeouts/fallos de dependencias y ausencia de escritura sin decisión humana. Evidencia: `agentes/analista/tests/integration/test_workflow_api.py`.
- [x] T026 Exponer `POST /api/workflows`, `GET /api/workflows/{workflow_id}` y `POST /api/workflows/{workflow_id}/resume`; compartir `WorkflowRuntime`/`InMemorySaver` por lifespan, verificar IDs de interrupción, serializar resultados Pydantic seguros, aplicar guardia de operación activa y mapear errores al sobre FastAPI existente. Contrato: `contracts/workflow-api.md`; montaje en `agentes/analista/api/main.py`.
- [x] T027 Integrar `workflowApi.js` y controles humanos React para respuestas de Negocio, aprobación/devolución/rechazo PO, recomendación y decisión del Gestor, resultados de Redactor/Asesor y manejo de errores; conservar rutas, Stepper, pestañas/SCSS y flujo manual. Evidencia: `src/services/__tests__/workflowApi.test.js`, `src/components/Comun/__tests__/WorkflowInterruptionForm.test.jsx`, `WorkflowIntegracion.test.jsx`, `WorkflowSolicitudCambio.test.jsx`; `npm test` 232 aprobadas.
- [x] T028 Explicar que los checkpoints son en memoria, no guardar `workflow_id` en `localStorage`, manejar HTTP 404 como checkpoint perdido y ofrecer un workflow nuevo sin fingir recuperación. Evidencia: UI de creación/cambio y pruebas 404 en `workflowApi.test.js` y `WorkflowIntegracion.test.jsx`.
- [x] T029 Actualizar README, `agentes/analista/README.md`, `quickstart.md` y guía PowerShell con instalación, arranque, health, pruebas, apagado y comportamiento real de UI/workflows, sin secretos. Evidencia: `npm run build`, `validate-feature-docs.mjs` y revisión de rutas documentadas.

## Fase 9 — Contrato Pinecone y configuración segura

- [x] T033 Añadir pruebas unitarias primero para creación/validación del índice Pinecone, configuración coincidente e índice existente incompatible, usando un adapter mockeado. Evidencia: `agentes/analista/tests/unit/test_pinecone_client.py` cubre índice ausente, creación explícita, compatibilidad, incompatibilidades, errores de API y ausencia del cliente SDK real.
- [x] T034 Implementar `agentes/conocimiento/` con cliente Pinecone inyectable, settings no secretos y lectura de `PINECONE_API_KEY` exclusivamente desde el entorno; nunca imprimir/loggear la clave. Evidencia: `config.py`, `client.py`, `errors.py`; la clave queda fuera de `repr` y se lee desde `os.environ` sin dotenv.
- [x] T035 Crear/validar un índice vectorial denso convencional con nombre `historias-usuario`, serverless, AWS `us-east-1`, 1024 dimensiones y métrica `cosine`; usar embeddings de `PineconeEmbeddings(model="multilingual-e5-large")` y `PineconeVectorStore`. No crear document index ni configurar integrated embedding. Evidencia: `contract.py`, adaptador SDK con `ServerlessSpec`/`vector_type="dense"` y fábrica LangChain; la validación incompatible no modifica ni elimina el índice.
- [x] T036 Añadir valores no secretos de Pinecone a `agentes/analista/.env.example` y `render.yaml`; declarar solo el nombre de la clave con `sync: false`, sin crear servicios Render adicionales ni incorporar valores secretos.

## Fase 10 - Fuentes ficticias y documentos de conocimiento

- [x] T037 Probar lectura y esquema de los cuatro JSON reales, su asignación a `glosario`, `estandares`, `checklist` y `hu_aprobadas`, rechazo de fuentes/namespaces ajenos y conservación de las cuatro herramientas MCP. `hu_similares.json` queda marcado como `simulated_reference`, sin estado aprobado.
- [x] T038 Crear `ejemplos/polizas_demo/` en Python con modelos de póliza, servicio de pólizas, cálculo de primas, coberturas, renovaciones, pagos, validaciones y mapa de dependencias Markdown; usar escenarios completamente ficticios sin datos personales. Fixture 1.0.0, entregado como requisito explícito de T016.
- [x] T039 Leer estáticamente solo `.py` y `.md` bajo `ejemplos/polizas_demo/`; normalizar citas relativas y rechazar traversal, rutas absolutas, extensiones ajenas y enlaces fuera de la raíz. Pruebas verifican que el código no se importa ni ejecuta.
- [x] T040 Convertir JSON y archivos ficticios a documentos LangChain con metadata validada; la preparación admite registros de `RepositorioHU`, y `hu_similares.json` queda separado como fuente simulada.
- [x] T041 Fragmentar determinísticamente bajo el máximo de 507 tokens de `multilingual-e5-large`, asignar IDs estables y limitar la reconciliación a coincidencias exactas de namespace y fuente.
- [x] T042 Verificar con adaptador de memoria (sin llamadas Pinecone) repetición idempotente, IDs sin duplicados, sustitución/cancelación de fragmentos, aislamiento de namespaces y fallo parcial con error sanitizado.
- [x] T043 Leer HU con `listar_hu`/`obtener_hu` y lecciones con `listar_lecciones(estado="aprobada")`; SQLite temporal verifica exclusión de borradores, propuestas, rechazos y PII, sin escrituras desde la fuente.

## Fase 11 - Ingesta y recuperacion para agentes

- [x] T044 Implementar CLI `python -m agentes.conocimiento.ingesta --fuente todas`, que solo admite fuentes allowlisted, crea/valida el índice y reporta conteos/errores sanitizados. Evidencia: `agentes/conocimiento/ingesta.py`; `test_knowledge_ingesta.py` prueba `main()`/dry-run, índice mockeado, IDs repetibles, reconciliación exacta, fallos parciales y ausencia de secretos. No se ejecutó ingesta real.
- [x] T045 Añadir pruebas primero de búsqueda semántica mockeada por los seis namespaces y prueba de que una consulta de un rol no accede a namespaces no autorizados. Evidencia: `test_knowledge_retrieval.py` comprueba los seis espacios, aislamiento, resultados vacíos, orden, límite y namespaces arbitrarios.
- [x] T046 Implementar retrieval read-only con mapeo agente→namespace y citas desde metadata validada; conservar `consultar_glosario`, `buscar_hu_similares`, `consultar_estandares` y `aplicar_checklist_vacios`. Evidencia: `agentes/conocimiento/retrieval.py`; las cuatro herramientas originales conservan nombre/contrato funcional y agregan estado, backend y citas validadas.
- [x] T047 Añadir herramientas MCP de búsqueda de código que solo consultan Pinecone/fuentes locales; devolver la ruta exacta del archivo recuperado. Evidencia: `consultar_codigo_demo` recupera solo `codigo`, valida la ruta con `AuthorizedSourceLoader` y devuelve contenido no confiable sin importar ni ejecutar archivos.
- [x] T048 Integrar recuperación en los cuatro agentes, manteniendo los límites de rol y `source_kind`; el Gestor solo consume HU aprobadas/lecciones aprobadas. Evidencia: Analista usa las cuatro herramientas originales; Redactor y Gestor reciben evidencia mediante `workflow_graph.py`; Asesor consulta su MCP técnico. `test_knowledge_agent_integration.py` verifica namespaces y decisiones humanas pendientes.
- [x] T049 Implementar fallback a búsqueda local con `status=degraded`, `backend=local` cuando Pinecone falle; asegurar que errores o resultados locales nunca se etiqueten como consulta Pinecone. Evidencia: `KnowledgeRetriever.search()` devuelve fuentes con su backend real o resultado vacío `degraded/none`; pruebas simulan fallo y disponibilidad local/ausente.
- [x] T050 Añadir pruebas de errores de Pinecone (auth, timeout, rate limit, index incompatible), fallback local y procedencia verdadera de cada fuente. Evidencia: `test_knowledge_retrieval.py` y `test_knowledge_ingesta.py` cubren clave ausente, autenticación, timeout, rate limit, índice ausente/incompatible, fallo parcial, citas, namespaces y aislamiento.

### Verificacion de T044-T050 (2026-11-22)

- T044: CLI ejecutada con los JSON y archivos de código allowlisted reales, y un repositorio de HU/lecciones aprobado simulado, usando `--fuente todas --dry-run`; exit code `0`, estado `dry_run`, 148 lotes preparados y conteos no vacíos en los seis namespaces (`glosario` 37, `estandares` 130, `checklist` 20, `hu_aprobadas` 4, `lecciones` 1, `codigo` 23 documentos validados). Reportó `index=not_contacted`; no se ejecutó la ingesta real.
- T045-T046: recuperación mockeada devolvió un resultado por namespace permitido y rol (`glosario`, `estandares`, `checklist`, `hu_aprobadas`, `lecciones`, `codigo`); las citas y el backend se derivaron de metadata validada. La suite verifica aislamiento, límites, resultados vacíos y rechazo de namespaces arbitrarios.
- T047-T048: `consultar_codigo_demo` valida rutas bajo `ejemplos/polizas_demo/`; las pruebas de integración cubren Analista, Redactor-Revisor, Asesor Técnico y Gestor de Cambios, incluida la exclusión de referencias simuladas para el Gestor y la interrupción para decisión humana.
- T049-T050: timeout simulado devolvió `status=degraded`, `backend=local` y fuentes con `backend=local`; los tests cubren credenciales ausentes, autenticación, timeout, rate limit, índice ausente/incompatible, fallos parciales, citas inventadas y cruces de namespace.
- Verificación de código actual: `.venv` Python 3.12 ejecutó `pytest agentes/analista/tests` con `311 passed, 1 skipped`; `npm test` terminó con `232 passed`; `npm run build` terminó correctamente. Estas ejecuciones no realizaron llamadas reales a Pinecone.

## Fase 12 - Inyeccion y documentacion

- [x] T051 Añadir pruebas adversariales de prompt injection en JSON, Markdown y código recuperado; verificar que el contenido no cambia rol/permisos/transiciones y no se ejecuta. Evidencia: `tests/integration/test_prompt_injection_boundaries.py` usa clientes y repositorio dobles; comprueba contenido no confiable, allowlists, interrupciones humanas y ausencia de escrituras.
- [x] T052 Actualizar guía PowerShell, `.env.example`, `render.yaml` y documentación del paquete con índice/namespaces, comando de ingesta, estado degradado y manejo seguro de secretos. Evidencia: README del paquete y guías actualizados; `validate-feature-docs.mjs` pasó. El dry-run devolvió `index=not_contacted`, 146 lotes preparados y `partial_failure/SOURCE_INVALID` para `repositorio` porque la SQLite local no tenía esquema; no se ejecutó ingesta real.

## Fase 13 - Aceptacion final (despues de integrar Pinecone)

- [x] T030 Ejecutar pruebas Python del backend, incluida feature 003 con mocks; `py -3.12 -m pytest` terminó con 314 aprobadas y 1 omitida por limitación de enlaces simbólicos del entorno. Evidencia: [informe de pruebas](informe-pruebas.md).
- [x] T031 Ejecutar build y pruebas frontend existentes; Vitest aprobó 232 pruebas en 37 archivos y cubrió rutas, Stepper y chat mediante pruebas de regresión/componentes; `npm run build` terminó correctamente. No se registran recorridos manuales.
- [x] T032 Revisar secretos, PII en logs/trazas, acceso y transiciones: los tests aíslan credenciales, usan adaptadores/mocks, validan allowlists y decisiones humanas; el escaneo Git no encontró `.env` real versionado. Evidencia: [informe de pruebas](informe-pruebas.md).
- [x] T053 Ejecutar pytest completo del backend con mocks: `314 passed, 1 skipped`; `tests/conftest.py` neutraliza credenciales externas, incluso las de `.env`, y los tests Pinecone sustituyen SDK/adaptadores, sin llamadas reales. Evidencia: [informe de pruebas](informe-pruebas.md).
- [x] T054 Revisar citas/evidencia, namespaces, dependencias, PII/secretos, aislamiento y regresión del Analista: los 18 pins directos coinciden con `requirements.lock`, `pip check` pasó y las suites correspondientes cubren estos contratos. No se afirma integración real con Pinecone ni OpenCode. Evidencia: [informe de pruebas](informe-pruebas.md).

### Verificación automatizada final (2026-11-22)

- Docker: `docker build --tag feature003-ci .` aprobado; smoke dentro del contenedor leyó ocho archivos de `ejemplos/polizas_demo/`. La imagen conserva Python 3.12, Node 22, React compilado y OpenCode 2.1.2.
- CI: creado `.github/workflows/feature003-ci.yml`, activado solo por push a esta rama, con permiso `contents: read`, sin secretos, servicios reales, deploy, release ni merge.
- RAG offline: la prueba `test_offline_dry_run_uses_valid_sqlite_schema_and_lists_sources_without_pinecone` usó SQLite temporal con esquema válido. Validó todos los namespaces, `status=dry_run`, `index=not_contacted`, errores vacíos, manifiesto de fuente/lotes y estados de aprobación; excluyó propuesta y rechazo.
- Aprobación: T001/T002 siguen pendientes de ratificación humana. No se simuló su cierre ni se declararon pruebas manuales realizadas.
- Detalle de comandos, resultados, warnings y hallazgos de seguridad: [informe de pruebas](informe-pruebas.md).

## Dependencias

- La ratificacion formal T001/T002 sigue pendiente; se completaron experimentalmente T005-T024, T037-T038, T039-T043 y T055-T060 por instruccion expresa en esta rama, sin declarar aceptacion formal.
- Fases 2–6 dependen de fundamentos T005–T009.
- T055–T060 deben preceder la ejecución de los nodos multiagente; T055 y T060 prueban selección y aislamiento con OpenCode simulado.
- La publicación de una HU depende de T019–T021; decisiones de cambio dependen de T022–T024.
- La ratificacion formal de T001/T002 sigue pendiente. T010-T024 y el fixture T038 se implementaron por instruccion expresa en modo experimental, limitada a esta rama; T037 y T039-T050 ya tienen código y pruebas, sin que esto equivalga a aceptación formal. Las pruebas usan clientes simulados; la ingesta real sigue sin ejecutarse.
- T037–T043 preceden a T044; T044–T050 ya están implementadas en esta rama; T051–T052 documentan la integración; T030–T032 y T053–T054 son aceptación final después de T050.
