# Feature 003: informe de pruebas E2E

Fecha: 2026-11-22  
Rama: `feat/sistema-multiagente-rag`

## Resultado

| Ejecución | Resultado |
|---|---:|
| Suite Python completa | 315 pasaron, 1 omitida |
| Suite React/Vitest | 232 pasaron, 37 archivos |
| Playwright headless | 4 pasaron |
| Build React | Pasó |
| Consistencia de dependencias Python | Pasó |
| Validador de feature 003 | Pasó; 8 documentos revisados |
| Build Docker | Pasó |
| Smoke Docker | Pasó; 8 fixtures ficticios |
| Diagnóstico de servicios reales | Desactivado; no abrió conexiones |

## Flujos cubiertos

- Cobertura E2E: un escenario HTTP integra el grafo y SQLite; cuatro escenarios Playwright recorren los flujos React y sus estados de error.
- El smoke HTTP levanta Uvicorn en loopback y hace solicitudes HTTP reales a FastAPI. Ejecuta el runtime LangGraph, el Analista, Redactor-Revisor, Asesor Técnico, Gestor de Cambios y el Repositorio `SQLite` temporal.
- OpenCode y Pinecone se sustituyen en el límite de proveedor con respuestas sintéticas. Las herramientas MCP locales del Analista se ejecutan en el smoke. TiDB no se configura ni se contacta.
- Pre-grooming: inicio, pregunta a Negocio, reanudación con `interrupt_id`, HU y criterios, evaluación técnica, aprobación explícita del PO y persistencia comprobada en SQLite.
- Post-grooming: recomendación del Gestor de Cambios, rechazo humano sin escritura, aplicación humana con persistencia única y repetición idempotente.
- Errores y recuperación: una respuesta sintética de OpenCode falla con timeout sanitizado; un segundo intento completa el flujo. IDs de interrupción obsoletos y resumes duplicados se rechazan sin escritura.
- Navegador: inicio pre-grooming y respuesta de Negocio; resultados y aprobación PO; recomendación y decisión post-grooming; error con continuación manual independiente; checkpoint perdido con HTTP 404.

## Flujos fallidos verificados

- OpenCode sintético falla con timeout y respuesta HTTP 504 sin filtrar el detalle; el reintento posterior avanza.
- Un `interrupt_id` obsoleto y un resume duplicado devuelven 409.
- Rechazar una solicitud de cambio termina sin insertar filas; un cambio sin decisión humana tampoco escribe.
- El error 503 del navegador permite continuar manualmente y registra por el endpoint manual, sin enviar resumes al workflow.
- El estado del checkpoint perdido devuelve 404 y la interfaz pide iniciar un workflow nuevo.

## Fallos observados y correcciones

- Vitest recogía el archivo de Playwright y fallaba al registrar sus pruebas. Se excluyó `e2e/` de Vitest, manteniendo ese archivo bajo Playwright.
- El primer intento local de Docker encontró bloqueado el archivo del contexto de Docker Desktop. El reintento de build y el smoke de ocho fixtures pasaron.
- Se ajustaron selectores del navegador para usar controles y textos accesibles presentes en la interfaz. Las cuatro pruebas Playwright terminaron verdes.

No quedaron fallos en las ejecuciones finales. Hay una prueba Python omitida y una advertencia de LangChain por el adaptador MCP beta.

## Integraciones no comprobadas y riesgos previos a despliegue

- OpenCode y Pinecone reales no se comprobaron. El diagnóstico opcional se ejecutó sin habilitarlo y reportó `disabled`; solo verifica conexiones cuando están configuradas las credenciales en un entorno de pruebas autorizado.
- Comando optativo: `python -m agentes.analista.diagnostics.check_real_services`. Requiere `FEATURE003_REAL_SERVICES=1` y `FEATURE003_TEST_ENV_AUTHORIZED=1`; OpenCode usa `OPENCODE_SERVER_PASSWORD` y Pinecone `PINECONE_API_KEY`.
- TiDB permanece sin comprobar y fuera de las pruebas. La integración E2E usa exclusivamente SQLite temporal.
- El checkpoint del workflow permanece en memoria. La prueba confirma que la UI reporta su pérdida con 404 y no afirma que pueda recuperarlo tras un reinicio.
- Las pruebas del navegador simulan las respuestas de la API para aislar React; el flujo HTTP y el grafo se comprueban por separado en el smoke Python.
- `npm install` reportó 11 alertas de auditoría de dependencias (5 moderadas, 3 altas y 3 críticas). No se aplicaron actualizaciones automáticas; revisar el detalle antes de un despliegue.
- El build React conserva una advertencia por un chunk de JavaScript superior a 500 kB.

Este resultado acredita las pruebas aisladas descritas. No declara OpenCode, Pinecone ni TiDB comprobados y no declara el sistema listo para producción.
