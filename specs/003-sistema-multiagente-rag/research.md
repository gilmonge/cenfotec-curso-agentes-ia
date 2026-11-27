# Investigación técnica — Feature 003

**Fecha**: 2026-11-19  
**Estado**: investigación para diseño; no autoriza implementación mientras la enmienda constitucional no esté aprobada.

## Decisiones y evidencia

### Decisiones definitivas acordadas para resolver diferencias con la guía original

La guía fuente citada por la constitución no está versionada en el repositorio; se registran aquí únicamente las diferencias aportadas por el equipo, sin atribuirle contenido adicional.

| Tema | Guía original | Decisión definitiva para feature 003 |
|---|---|---|
| Repositorio ficticio del Asesor | .NET | Python, bajo `ejemplos/polizas_demo/`, estático y allowlisted. |
| Pinecone | Índice vectorial con LangChain-Pinecone | Índice vectorial denso convencional; embeddings vía `PineconeEmbeddings` y almacenamiento/consulta por `PineconeVectorStore` de `langchain-pinecone`. No usar document index, campos de texto con embedding integrado ni `documents.upsert/search`. |
| Constitución | 1.1.0 (MINOR) | 2.0.0 (MAJOR), propuesta pendiente. La enmienda redefine incompatiblemente límites vigentes que excluían los agentes adicionales y el RAG; no entra en vigor hasta aprobación humana. |

El índice vectorial queda fijado como `historias-usuario`, denso, `1024` dimensiones, métrica `cosine`, serverless en AWS `us-east-1`, con `multilingual-e5-large` como modelo de embeddings. La aplicación obtiene vectores mediante `PineconeEmbeddings`, y después los upserta/consulta como vectores ordinarios. Este flujo no usa el esquema de documentos ni embeddings integrados de Pinecone. El pin compatible de `pinecone` y `langchain-pinecone` se validará en T005; no se declara una versión mínima del SDK asociada a document indexes.

### D-001 — Usar `StateGraph` tipado para el flujo

**Decisión propuesta**: representar las etapas como nodos, las condiciones como transiciones explícitas y el contexto de workflow como estado tipado. El usuario exige un grafo real y los dos flujos y ciclos están definidos en la especificación.

**Evidencia**: la documentación de LangGraph describe el Graph API con estado, nodos y aristas; documenta `StateGraph` como constructor principal, con estado tipado y transiciones fijas o condicionales ([Graph API de LangGraph](https://docs.langchain.com/oss/python/langgraph/graph-api)).

**Implicación**: usar nodos con límites de rol y contratos, en lugar de un `if/else` genérico que solo se presente como grafo. Verificar en pruebas el grafo compilado y las aristas autorizadas.

### D-002 — Usar `interrupt()` y reanudar con `Command(resume=...)`

**Decisión propuesta**: interrumpir en la espera de Negocio, aprobación PO y decisión humana post-grooming. Cada interrupción expone un payload serializable, su respuesta se valida como un modelo estructurado y la reanudación usa el mismo `thread_id` con `Command(resume=...)`.

**Evidencia**: la guía oficial explica que `interrupt()` pausa y guarda el estado con un checkpointer, que `Command(resume=...)` provee el valor a la llamada interrumpida, y que debe usarse el mismo ID de hilo para reanudar. También especifica que el nodo que contiene `interrupt()` vuelve a ejecutarse desde el inicio del nodo; por ello, efectos laterales antes de `interrupt()` deben evitarse o ser idempotentes ([Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)). La respuesta estructurada de interrupción se documenta para LangGraph `>=1.2.12`; el lock actual tiene `langgraph==1.2.18`.

**Implicación**: aislar en cada nodo cualquier efecto lateral y no escribir al repositorio antes de que la persona responda. Probar reanudaciones reales del grafo con `InMemorySaver` y mocks.

### D-003 — Aceptar la pérdida de checkpoints de `InMemorySaver` en la primera versión

**Decisión propuesta**: cumplir la restricción del usuario usando `InMemorySaver`, pero describirlo como memoria del proceso, no como persistencia durable. No migrar a PostgreSQL ni añadir un servicio.

**Evidencia**: la referencia oficial confirma que `InMemorySaver` guarda checkpoints en memoria. La misma documentación lo recomienda para debugging/testing y recomienda un checkpointer persistente para uso productivo ([InMemorySaver reference](https://reference.langchain.com/python/langgraph.checkpoint/memory/InMemorySaver), [Checkpointing](https://reference.langchain.com/python/langgraph/checkpoints)).

**Implicación**: el estado se pierde al reiniciar el proceso o la instancia Render. La UI, documentación y mensajes de recuperación deben explicarlo; no se presentará como fallo de reanudación recuperable. Esta limitación queda aceptada por el requerimiento para la primera versión.

### D-004 — LangGraph ya aparece en el lock, pero no como dependencia directa

**Hallazgo del repositorio**: `agentes/analista/requirements.lock` incluye `langgraph==1.2.18` y `langgraph-checkpoint==4.3.1`; `agentes/analista/requirements.txt` no declara LangGraph de forma directa. No se ejecutó pip ni se cambió lockfile.

**Decisión propuesta**: tras el gate, declarar LangGraph como dependencia directa y mantener versiones del lock validadas; no hacer upgrades incidentalmente. Asegurar que Python de despliegue soporte el lock.

### D-005 — Separar los dos repositorios

**Hallazgo del repositorio**: `agentes/analista/memory/repositorio.py` implementa el repositorio persistente de HU y lecciones, con escrituras controladas por API. El nuevo Asesor requiere consultar un repositorio ficticio Python.

**Decisión propuesta**: mantenerlos separados. El Asesor solo consultará fixtures versionados Python/estándares mediante una allowlist de lectura y citará los elementos realmente leídos. `memory/repositorio.py` se reutilizará para guardar HU tras aprobación explícita del PO y aplicar cambios después de una decisión humana. Ningún archivo Python de la app o repositorio real se presentará como fuente ficticia.

### D-006 — Reutilizar OpenCode y observabilidad existentes

**Decisión propuesta**: todas las llamadas de modelo pasan por `agentes/analista/core/opencode_client.py`; OpenCode permanece deny-all para herramientas. El backend Python aplica una allowlist MCP read-only por agente/rol y namespace y es el único que invoca esas herramientas. LangChain se usa realmente para construir prompts y validar/parsear salidas; el grafo coordina. `observability.py` añade spans por etapa sin contenido de prompts/respuestas ni secretos.

**Implicación**: conservar el contrato y rutas actuales del Analista; las nuevas salidas no se mezclan con respuestas del chat actual. Las pruebas automatizadas usan mocks y no consumen cuota ni llaman OpenCode.

### D-007 — Índice vectorial convencional con LangChain-Pinecone

**Decisión definitiva**: usar el paquete `langchain-pinecone`: `PineconeEmbeddings(model="multilingual-e5-large")` produce los vectores y `PineconeVectorStore` realiza upsert y búsqueda en el índice vectorial convencional. El índice es denso, dimensión `1024`, métrica `cosine`, serverless en AWS `us-east-1`. El servicio valida el nombre y los parámetros del índice antes de escribir o consultar y falla de forma controlada ante incompatibilidad.

**Evidencia**: la referencia oficial de LangChain documenta `PineconeVectorStore`, su parámetro de embeddings, el uso del cliente Pinecone para crear un índice con `dimension` y `metric`, y las operaciones de `add_documents`/`similarity_search` ([integración Pinecone de LangChain](https://reference.langchain.com/python/langchain-pinecone/vectorstores/PineconeVectorStore)). La referencia del mismo paquete documenta `PineconeEmbeddings` ([PineconeEmbeddings](https://reference.langchain.com/python/langchain-pinecone/embeddings/PineconeEmbeddings)). Pinecone define la dimensión y métrica en índices vectoriales convencionales y exige que coincidan con los vectores insertados ([configuración del índice](https://docs.pinecone.io/reference/api/2025-10/control-plane/configure_index)).

**Límite de arquitectura**: no usar document indexes, esquema `schema`, mapa de campos de texto con embeddings integrados, `documents.upsert`, `documents.search` ni el mínimo de versión `10.1.0` citado para ese otro flujo. Se fijarán versiones compatibles de `pinecone` y `langchain-pinecone` en T005. El índice existente nunca se elimina ni se recrea automáticamente.

### D-008 — Namespaces, vectores e IDs idempotentes

**Decisión propuesta**: un índice y seis namespaces allowlisted. Cada vector contiene un ID estable, embeddings y metadata de fuente/clase/cita; el texto fuente se conserva en metadata para recuperar fragmentos citables. Las consultas declaran namespace explícito. Identificadores se derivan determinísticamente de namespace, fuente/ID original y número de fragmento. Upsert al mismo ID reemplaza el vector, lo que permite ingestas repetidas sin duplicados.

**Evidencia**: la API `PineconeVectorStore` de LangChain acepta IDs, metadata, namespaces y `Embeddings`, y expone búsqueda por similitud. Los upserts son por ID; las pruebas verifican la actualización idempotente de los vectores bajo esos IDs ([integración Pinecone de LangChain](https://reference.langchain.com/python/langchain-pinecone/vectorstores/PineconeVectorStore)).

**Implicación**: las referencias de `hu_similares.json` llevan `source_kind=simulated_reference`, no se declaran aprobadas. Solo registros con origen `RepositorioHU` y aprobación comprobada pueden usarse como base para el Gestor de Cambios. Ingestar lecciones con estado `aprobada` únicamente.

### D-009 — Fallback local explícito con estado degradado

**Decisión propuesta**: preservar las herramientas MCP actuales, que implementan búsqueda léxica local, y llamar al backend de conocimiento solo cuando su configuración y consulta estén disponibles. Si Pinecone falla, el resultado local identifica su backend y marca `degraded`; un fallo de Pinecone nunca aparece como resultado/cita de Pinecone.

**Hallazgo del código**: `agentes/analista/mcp/tools.py` ya tiene `_matches` y búsqueda local para glosario, HU similares, estándares y checklist. El repositorio `RepositorioHU` ofrece búsquedas/listados locales. Las fixtures de código permiten búsqueda local con el mismo ranking léxico, con citas de ruta de fixture.

**Implicación**: considerar Pinecone y fallback como proveedores distintos en contrato/observabilidad. Un error que afecta Pinecone no borra el estado real de la consulta local.

### D-010 — Limitar fragmentos y no ejecutar código recuperado

**Decisión propuesta**: particionar JSON, Markdown y código fuente en fragmentos deterministas bajo el límite verificado del modelo de embeddings; la ingesta procesa texto estáticamente. Los resultados se delimitan como datos no confiables antes de pasarlos a OpenCode.

**Evidencia**: LangChain documenta el adapter de embeddings y el vector store por separado. El límite de tokens y el tamaño de lote se deben validar contra el modelo/API de embeddings seleccionado al fijar dependencias; no se asume el límite propio del endpoint de document-index. La API mock de Pinecone puede servir para probar requests/errores sin una cuenta, pero no sustituye los mocks unitarios ni verifica relevancia ([mock de API](https://docs.pinecone.io/guides/production/mock-the-api)).

**Implicación**: pruebas de recuperación/ingesta usan mocks del adapter, no Pinecone real ni Pinecone Local. La calidad semántica real se verificará únicamente en una aceptación manual autorizada separada; esta petición prohíbe llamadas reales durante pytest. El código recuperado nunca se importa, ejecuta, evalúa ni trata como instrucciones.

## Alternativas consideradas

| Alternativa | Evaluación |
|---|---|
| Un agente único con selección textual de rol | Rechazada: debilita separación de permisos, puntos de aprobación y trazabilidad de transiciones. |
| Cuatro servicios Render independientes | Rechazada: el usuario prohíbe servicios adicionales y la delegación se resuelve con nodos Python en el servicio actual. |
| Checkpointer durable en esta versión | Fuera de alcance por requerimiento explícito de `InMemorySaver`; debe proponerse en otra feature y gobernarse por separado. |
| Pinecone Local en pruebas | No usarlo: Pinecone lo retiró en octubre de 2026; las pruebas automatizadas usan un adapter mockeado como solicita la feature. |
| RAG sin Pinecone | Rechazado para este alcance actualizado: el usuario ahora requiere un índice Pinecone y el fallback local existente. |
| Acceso a repositorio real del proyecto | Rechazado: no cumple la condición del Asesor y ampliaría permisos. |

## Preguntas pendientes de diseño

- El Dockerfile actual usa Python 3.12; validar pins/lock contra esa imagen en T005, después del gate constitucional.
- Validar qué estructura de datos de `guardar_hu` espera el repositorio para registrar el resultado estructurado sin romper los endpoints actuales.
- Definir en revisión del equipo los límites de tamaño de la evidencia técnica y la política de expiración de IDs de workflow en memoria.
- La UI presentará etapa/estado y la intervención pendiente con controles de respuesta/reanudación; conservará Stepper, chat y simulaciones. El contrato informa checkpoint perdido y permite iniciar un flujo nuevo.
- Definir el splitter determinista y cómo reconciliar fragmentos obsoletos cuando cambia un archivo fuente, limitado al namespace/ID de esa fuente.
- Confirmar qué configuración del índice vectorial convencional devuelve `describe()` en los pins elegidos; un índice incompatible debe fallar sin borrarse.
- Definir el estado UI/API para diferenciar `pinecone`, `local` y `degraded` sin exponer stack traces ni configuración sensible.

Estas preguntas no cambian el gate constitucional; resolverlas forma parte del diseño previo a implementar.
