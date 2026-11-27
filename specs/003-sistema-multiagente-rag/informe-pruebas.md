# Informe de pruebas — Feature 003

**Fecha:** 2026-11-22  
**Rama:** `feat/sistema-multiagente-rag`  
**Alcance:** validación automatizada local de backend, frontend, documentación, RAG offline y construcción Docker. No se desplegó, no se ejecutó una ingesta remota y no se inició OpenCode como servicio.

## Resultados

| Área | Comando | Resultado |
|---|---|---|
| Dependencias Python 3.12 | `py -3.12 -m pip install -r agentes/analista/requirements.txt` | Instalación completada. |
| Consistencia Python | `py -3.12 -m pip check` | `No broken requirements found.` |
| Backend completo | `py -3.12 -m pytest` | `314 passed, 1 skipped, 1 warning` en 16.04 s; se recolectaron 315 casos. |
| Frontend | `npm test -- --run` | `232 passed` en 37 archivos, 25.22 s. |
| Build React | `npm run build` | Correcto; 2,184 módulos transformados. |
| Documentación feature 003 | `node scripts/diagnostics/validate-feature003-docs.mjs` | Correcto; ocho documentos y enlaces internos validados, T001/T002 pendientes. |
| Docker | `docker build --tag feature003-ci .` | Correcto; imagen `feature003-ci` construida. |
| Smoke Docker | `docker run --rm feature003-ci python scripts/diagnostics/docker-fixture-smoke.py` | `docker_fixture_smoke=passed files=8`; los archivos se pudieron leer como usuario `app`. |
| Versiones en la imagen | Inspección ejecutable de imagen | Python `3.12.16`, Node `v22.23.5`, OpenCode `v2.1.2`. El servidor OpenCode no se inició. |

El único test omitido es `test_rejects_symbolic_link_outside_authorized_root`: Windows no permitió crear enlaces simbólicos en este entorno. No se deshabilitaron pruebas. La advertencia Python corresponde a la API beta `langchain.mcp`.

Una ejecución intermedia expuso un falso positivo intermitente del detector PII: un UUID aleatorio podía coincidir con el patrón de número telefónico. Se corrigió excluyendo UUID canónicos antes de evaluar secuencias numéricas y se añadió una prueba que conserva la detección de teléfonos; la suite final completa pasó.

## Dry-run RAG con SQLite temporal

`test_offline_dry_run_uses_valid_sqlite_schema_and_lists_sources_without_pinecone` pasó dentro de la suite Python. Creó un `RepositorioHU` temporal con el esquema vigente, una HU aprobada, una lección aprobada, una propuesta y una lección rechazada. El dry-run cargó las fuentes JSON allowlisted y los archivos ficticios del repositorio, sin construir el cliente Pinecone.

Se verificó `status=dry_run`, `index=not_contacted`, `errors=[]`, conteos no vacíos en los seis namespaces y un `batch_manifest` con namespace, `source_id`, `source_ref`, tipo de fuente, estado de aprobación y los IDs de cada fragmento. La HU y la lección de prueba quedaron marcadas `aprobada`; la referencia ficticia conservó estado nulo; propuesta, rechazo e historia borrador quedaron excluidos. El estado del repositorio no cambió.

## Cobertura revisada

- Analista, respuestas de Negocio, Redactor-Revisor, criterios estructurados y rondas limitadas: pruebas de workflow con OpenCode simulado.
- Asesor Técnico: evidencia consultada desde el fixture ficticio, referencias no recuperadas, límites de rol y lectura estática.
- Gestor de Cambios: ambas clasificaciones, evidencia literal de comparación, HU aprobada requerida y decisión humana separada.
- Aprobación PO: interrupción obligatoria, devoluciones con motivo y cero escrituras antes de una decisión humana válida. Los contratos rechazan campos de aprobación del agente.
- API FastAPI: TestClient, concurrencia, validación, errores y pérdida del checkpoint después de reiniciar runtime.
- React: API simulada, controles de interrupción humana, respuesta de Negocio, aprobación/devolución PO, workflows de cambio, 404 de checkpoint perdido, rutas, Stepper y chat.
- RAG: ingesta repetida con IDs estables, namespaces aislados, fallback local con procedencia `local`, citas, fallos Pinecone simulados y prompt injection como datos no confiables.

## Revisión de seguridad

- `tests/conftest.py` neutraliza `OPENCODE_API_KEY`, `OPENCODE_SERVER_PASSWORD`, claves Langfuse, `PINECONE_API_KEY`, `DATABASE_URL` y `ANALISTA_REPO_DB`; los valores vacíos impiden que `BaseSettings` reutilice credenciales del `.env` local. Una prueba confirma que OpenCodeSettings no carga claves reales. Los tests Pinecone usan adaptadores falsos y sustituyen el SDK antes de crear el cliente. No hubo llamadas reales a Pinecone o TiDB.
- Los tests del workflow usan dobles de OpenCode, MCP y repositorio. No se probó integración real con OpenCode.
- Git solo reportó `.env.example` como archivo de entorno versionado; no hay `.env` real versionado. Se corrigió el único requisito directo sin pin: `certifi` quedó fijado a `2026.11.20` en ambos archivos. Los 18 requisitos directos ahora coinciden con `requirements.lock`.
- Las fuentes RAG se validan por esquema/allowlist; el código ficticio se lee como texto y se rechaza traversal. Los tests comprueban namespaces por rol, metadata de aprobación, citas derivadas de fuentes y defensa ante instrucciones inyectadas.
- Los logs/trazas se revisan mediante pruebas que evitan incluir prompts/respuestas, PII y errores de conexión/credenciales; los errores públicos se sanitizan.
- El detector PII ya no clasifica bloques hexadecimales de UUID como teléfonos; una prueba de regresión comprueba también que los teléfonos reales sigan detectándose.
- Sin hallazgos que bloqueen las tareas T030/T031/T032/T053/T054 en el alcance automatizado revisado. No se declara revisión humana, recorrido manual ni integración externa real.

## Advertencias no bloqueantes

- Sass avisa que su API JavaScript legacy se eliminará en una versión futura.
- React Router emite avisos de compatibilidad de futuras opciones de v7.
- Vite advierte que el bundle JavaScript principal supera 500 kB sin minificar; el build completó.
- El test de enlaces simbólicos no pudo ejecutarse en Windows por permisos del entorno; seguirá ejecutándose en entornos que permitan crearlos.
- El workflow se validó como YAML y su trigger/permiso se comprobaron localmente; no se ejecutó en GitHub porque no se hizo push a la rama.

## Estado de ratificación

T001 y T002 permanecen pendientes de ratificación humana. Las pruebas automáticas no cuentan como aprobación formal. T044-T050 no se repitieron como una reimplementación; el dry-run fue repetido únicamente para comprobar SQLite válido y estados de aprobación, como se solicitó.
