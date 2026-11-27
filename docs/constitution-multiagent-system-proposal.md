# Propuesta de enmienda constitucional: sistema multiagente con RAG

**Rama requerida**: `docs/constitution-multiagent-system` (separada de `feat/sistema-multiagente-rag`, creada desde `main`).

**Estado**: propuesta publicada en esta rama para revisión humana; no aprobada ni vigente. La constitución vigente sigue en 1.0.1 hasta la aprobación por PR.

**Cambio propuesto**: versión **2.0.0 (MAJOR)**. La propuesta constitucional completa está en `.specify/memory/constitution.md` dentro de esta rama.

## Motivación y diferencias acordadas

La propuesta es una enmienda **2.0.0 (MAJOR)**: la constitución 1.0.1 excluye explícitamente el sistema multiagente y redefine límites de arquitectura para admitir la feature 003. La guía fuente citada por la constitución no está versionada; la tabla refleja solo las decisiones registradas en los artefactos del proyecto y no le atribuye contenido adicional.

| Tema | Guía original | Decisión para feature 003 |
|---|---|---|
| Repositorio ficticio del Asesor | .NET | Python, con fixtures ficticios allowlisted bajo `ejemplos/polizas_demo/`. |
| Pinecone | Índice vectorial con LangChain-Pinecone | Índice denso convencional. `PineconeEmbeddings` genera vectores y `PineconeVectorStore` de `langchain-pinecone` los upserta/consulta. No se usa document index ni embedding integrado. |
| Versión constitucional | 1.1.0 (MINOR) | 2.0.0 (MAJOR), por redefinir de forma incompatible exclusiones de alcance y reglas de arquitectura. |

## Autorización propuesta

La feature 003 queda autorizada, sujeta a aprobación de esta enmienda y a los gates Spec Kit, para:

- Mantener cuatro responsabilidades Python: Analista de Requerimientos, Redactor-Revisor, Asesor Técnico y Gestor de Cambios.
- Orquestar el flujo con un `StateGraph` real de LangGraph, estado tipado y transiciones/interrupciones explícitas.
- Usar Pinecone para embeddings y RAG sobre un índice vectorial convencional, con fallback local controlado.
- Conservar herramientas MCP read-only, invocadas solo por el backend Python mediante allowlist explícita por agente/rol. OpenCode mantiene todos sus permisos de herramientas en deny-all, incluidas herramientas MCP; cualquier cambio exige justificación de seguridad, aprobación humana y pruebas de aislamiento explícitas.
- Usar como fuente de análisis técnico una aplicación de pólizas totalmente ficticia, implementada en Python, versionada y de solo lectura.
- Desplegar exactamente un Docker Service en Render, sin servicios Render adicionales.
- Exigir aprobación humana explícita del PO antes de guardar una HU como aprobada y decisión humana para cambios; ninguna salida de agente equivale a aprobación.
- Conservar el Analista existente, su misión, capacidades, contratos y comportamiento; los otros roles se agregan sin sustituirlo.

## Impacto en principios y artefactos

- **Principio IV — Agentes Python**: permite responsabilidades separadas dentro del backend/servicio existente, sin requerir cuatro servicios o contenedores.
- **Principio VI — Fidelidad del Analista y decisión humana**: preserva al Analista y extiende las puertas de aprobación explícita a todo el flujo multiagente.
- **Principio VII — Integraciones**: conserva OpenCode como motor generativo, LangChain para prompts, parseo tipado y vector store; LangGraph real para orquestación; MCP controlado por Python; RAG con LangChain-Pinecone.
- **Principio VIII — Seguridad Read-Only**: conserva todas las restricciones vigentes y mantiene OpenCode deny-all; el backend aplica la allowlist MCP. Solo un comando backend de ingesta puede escribir vectores desde fuentes allowlisted.
- **Principio XII — Orquestación Multiagente y Conocimiento con Control Humano Explícito**: fija las responsabilidades, puntos de control humano, recuperación vectorial y límites de despliegue.
- El índice autorizado es `historias-usuario`, denso, dimensión 1024, métrica `cosine`, serverless en AWS `us-east-1`, con vectores de `multilingual-e5-large`; los namespaces son `glosario`, `estandares`, `checklist`, `hu_aprobadas`, `lecciones` y `codigo`.
- La feature afectada es `specs/003-sistema-multiagente-rag/`; la implementación permanece bloqueada hasta aprobar la enmienda y validar los artefactos Spec Kit.

## Migración y límites

No hay migración de código ni datos en esta enmienda. Tras aprobarla, revisar la feature 003 contra la constitución vigente antes de iniciar T005. OpenCode mantiene todas las herramientas en deny-all. El backend Python invoca las herramientas MCP read-only mediante allowlist por agente/rol y `OpenCodeClient` selecciona el agente explícitamente. Pinecone usa la interfaz vector store de LangChain y no la API de document indexes. Las pruebas usan mocks y nunca llaman Pinecone real.

El Analista conserva su misión. Redactor-Revisor puede corregir hasta dos rondas, pero no aprobar. Asesor Técnico solo informa evidencia de estándares y fixtures Python ficticios. Gestor de Cambios recomienda `aclaracion` o `cambio_alcance`; la decisión final es humana. Toda aprobación del PO es explícita. `InMemorySaver` pierde estado al reiniciar el servicio.

## Versión y procedimiento

La propuesta es 2.0.0 (MAJOR) por cambios incompatibles de alcance/principios, no una expansión menor. Requiere PR en esta rama, revisión y aprobación humana conforme a Governance. El informe temporal de impacto se retiró de `.specify/memory/constitution.md`. La propuesta no se considera aprobada por estar preparada o por el resultado del análisis documental.
