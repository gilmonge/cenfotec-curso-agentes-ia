# Contratos HTTP — Workflow multiagente

**Estado**: contrato implementado experimentalmente en T025–T026. La feature completa sigue pendiente de ratificación formal T001/T002.

## Agentes OpenCode

`opencode.jsonc` registra los identificadores estables `analista`, `redactor_revisor`, `asesor_tecnico` y `gestor_cambios`. Cada agente carga su propio prompt externo. OpenCode mantiene todos los permisos de herramientas en deny-all, incluidas MCP. El backend Python aplica una allowlist MCP read-only por agente/rol y namespace, y es el único componente que invoca esas herramientas. Ningún agente tiene shell, acceso libre al filesystem, escritura ni acceso general a la red.

`OpenCodeClient` recibe el identificador del rol/agente para cada invocación y valida que esté configurado. No usa el agente `analista` como fallback para otra responsabilidad. Las pruebas con OpenCode/MCP simulados deben confirmar que cada invocación usa el agente y prompt correctos, que OpenCode no invoca herramientas y que el backend solo ejecuta la allowlist y namespaces de ese rol.

## Iniciar un workflow

`POST /api/workflows`

Entrada discriminada por modo:

- `pre_grooming`: `requirement` y `request_id` de correlación (opcional; el backend genera uno si se omite).
- `post_grooming`: `approved_story_id` y `change_request`.

```json
{ "mode": "pre_grooming", "request_id": "a7811a1d-750d-4f2e-89ac-4b92401a0d0e", "requirement": "Consultar vigencia de una póliza" }
```

```json
{ "mode": "post_grooming", "approved_story_id": "HU-001", "change_request": "Precisar la fecha final de vigencia" }
```

Validaciones: `requirement` de 1–4.000 caracteres para `pre_grooming`, `change_request` de 1–2.000 caracteres para `post_grooming`, modo permitido, referencia de HU aprobada para post-grooming, máximo de una operación activa por workflow y rechazo de campos desconocidos. Una solicitud concurrente recibe conflicto y no modifica el checkpoint.

Respuesta del runtime (resumen; los campos de `results` dependen de la etapa):

```json
{
  "workflow_id": "opaque-id",
  "mode": "pre_grooming",
  "status": "interrupted",
  "stage": "espera_negocio",
  "results": {
    "analyst": { "preguntas": [] },
    "story": null,
    "technical_assessment": null
  },
  "interrupt": {
    "interrupt_id": "langgraph-interrupt-id",
    "kind": "business_answers",
    "payload": { "questions": [], "max_answer_chars": 1000, "max_total_chars": 3500 },
    "response_schema": { "type": "object" }
  }
}
```

`POST /api/workflows` ejecuta el grafo hasta su primera interrupción o resultado final y responde `201`. Se envía `mode=pre_grooming` con `requirement` de 1–4.000 caracteres, o `mode=post_grooming` con `approved_story_id` y `change_request` de 1–2.000 caracteres. El modelo Pydantic rechaza campos adicionales y combinaciones de modo inválidas.

## Consultar estado

`GET /api/workflows/{workflow_id}`

Devuelve etapa, estado, resultados estructurados disponibles, interrupción activa o resultado final. No devuelve estado interno no autorizado, prompt, stack trace, credenciales ni trazas.

## Reanudar intervención

`POST /api/workflows/{workflow_id}/resume`

El cuerpo contiene el `interrupt_id` exacto que devolvió el runtime, `kind` y el objeto `response` tipado. Si el ID o tipo no corresponde a la interrupción activa, se responde `409` y el checkpoint no cambia:

```json
{
  "kind": "po_approval",
  "interrupt_id": "langgraph-interrupt-id",
  "response": { "decision": "aprobar" }
}
```

- `business_answers`: respuestas a preguntas pendientes; reanuda hacia Analista.
- `po_approval`: decisión explícita `aprobar`, devolución con destino permitido y motivo, rechazo o detención.
- `change_decision`: decisión humana `aplicar`, `rechazar` o `devolver` (esta última requiere motivo).

El servicio comprueba el ID de interrupción emitido por LangGraph y resuelve ese workflow al mismo checkpoint con `Command(resume=respuesta_validada)` y el mismo `thread_id` privado. Solo una operación de escritura puede estar activa por workflow. Una reanudación incorrecta o duplicada se rechaza sin modificar el checkpoint. Las aprobaciones solo aparecen en resultados después de una decisión humana explícita.

## Errores públicos

| HTTP | Código | Uso |
|---|---|---|
| 400 | `INVALID_INPUT` | Respuesta válida como JSON pero incompatible con la interrupción o sus preguntas pendientes. |
| 422 | `INVALID_REQUEST` | Cuerpo no válido según Pydantic, campos desconocidos o texto fuera de límites. |
| 404 | `WORKFLOW_NOT_FOUND` | Workflow ausente o checkpoint perdido tras reinicio. El cliente debe iniciar un flujo nuevo. |
| 409 | `WORKFLOW_NOT_WAITING` | Existe una etapa en ejecución o no hay interrupción pendiente para reanudar. |
| 422 | `CONTRACT_INVALID` | Salida estructurada del agente no satisface el modelo esperado. |
| 503 | `DEPENDENCY_UNAVAILABLE` | OpenCode/MCP no disponible; el flujo no continúa a la siguiente etapa. |
| 504 | `WORKFLOW_TIMEOUT` | Límite de operación alcanzado; resultado incompleto no se presenta como éxito. |

Los errores reutilizan el sobre Pydantic de `agentes/analista/api/errors.py` y no incluyen stack traces, tokens, rutas internas, texto completo de prompts ni datos personales. Las rutas `/api/workflows` usan el mismo middleware de autenticación Basic que la API de Analista.

## Contratos de recuperación de conocimiento

El backend de conocimiento expone herramientas MCP read-only. La ingesta es un comando Python separado, no una herramienta invocable por los agentes.

### Búsqueda por rol

La solicitud incluye consulta y un `agent_role` de enum interno. El backend mapea ese rol a namespaces permitidos; el request del navegador nunca elige un namespace arbitrario.

Namespaces disponibles: `glosario`, `estandares`, `checklist`, `hu_aprobadas`, `lecciones`, `codigo`.

Salidas mínimas:

```json
{
  "status": "ok",
  "backend": "pinecone",
  "namespace": "codigo",
  "sources": [
    {
      "source_id": "stable-source-id",
      "source_kind": "fictional_python_file",
      "source_ref": "ejemplos/polizas_demo/servicios/primas.py",
      "chunk": 0,
      "score": 0.83,
      "text": "fragmento recuperado como dato no confiable"
    }
  ]
}
```

Valores permitidos de `backend`: `pinecone`, `local`, `none`. Una caída de Pinecone con búsqueda local disponible produce `status="degraded"`, `backend="local"`, fuentes únicamente locales y un error controlado sin detalles internos. Si no hay resultados locales, se devuelve `degraded` con una lista vacía. No se informa Pinecone como fuente si no completó la búsqueda.

La herramienta de código devuelve rutas relativas dentro de `ejemplos/polizas_demo/`. Los resultados de JSON y RepositorioHU incluyen archivo/ID original y `source_kind`; contenido de referencia simulada queda distinguido de contenido aprobado.

### Contrato de ingesta

Comando: `python -m agentes.conocimiento.ingesta --fuente todas`.

El comando acepta solo fuentes preconfiguradas. Su salida informa conteos leídos, validados, upserted y excluidos por namespace, IDs estables y errores sanitizados; nunca incluye la clave Pinecone, texto completo sensible, ni un estado de éxito total si hubo fallas.

El cliente lee `PINECONE_API_KEY` del entorno y limita operaciones al índice vectorial denso convencional `historias-usuario` y los seis namespaces. Se usa `PineconeEmbeddings(model="multilingual-e5-large")` para producir vectores y `PineconeVectorStore` de `langchain-pinecone` para upsert y búsqueda. La configuración del índice es serverless en AWS `us-east-1`, dimensión `1024` y métrica `cosine`. No se usa document index, mapa de campos de texto, embedding integrado ni API `documents.*`. Si el índice existente no coincide, la ingesta/búsqueda falla sin borrarlo ni recrearlo.

Upserts usan ID determinístico por namespace, origen y número de fragmento; repetir exactamente la ingesta reemplaza el mismo ID. Fuentes aprobadas provienen solo de `RepositorioHU` (HU aprobadas/lecciones aprobadas); código solo de `.py`/`.md` allowlisted bajo `ejemplos/polizas_demo/` y nunca se importa o ejecuta.

## Protección de contenido recuperado

- Todas las fuentes se delimitan como datos no confiables en el prompt del agente.
- No hay `exec`, `eval`, import dinámico, shell ni ejecución de código recuperado.
- Texto recuperado no altera sistema, permisos, namespace ni rutas del grafo.
- Citas se construyen desde metadatos validados por el backend, no desde texto libre generado por el modelo.
- Pruebas de errores Pinecone, namespaces, citación e inyección usan adapter/mocks y nunca una cuenta Pinecone real.

## Seguridad y ciclo de vida

- Backend valida cada cuerpo con Pydantic y aplica límites de longitud y tamaño.
- Configuración no secreta: índice vectorial `historias-usuario`, cloud `aws`, región `us-east-1`, dimensión `1024`, métrica `cosine`, modelo de embeddings `multilingual-e5-large` y namespaces fijos. Las llamadas de embeddings y las operaciones vectoriales son explícitas en la aplicación; el índice no almacena configuración de integrated embeddings.
- `PINECONE_API_KEY` procede solo del entorno; `.env.example` usa un valor vacío y Render la declara `sync: false` sin incluir credencial.
- El navegador no contacta OpenCode, Langfuse ni MCP directamente.
- IDs de workflow permanecen en memoria de la interfaz; no se guardan en localStorage/sessionStorage.
- Una respuesta de PO requiere identidad/autoridad humana según el mecanismo de sesión existente; no se acepta un campo del agente como sustituto.
- El checkpointer es `InMemorySaver`: reinicio de Render elimina estado/interrupciones y la consulta devuelve `WORKFLOW_NOT_FOUND`.
- No se realizan escrituras externas ni llamadas a sistemas reales. El repositorio de HU solo recibe escritura tras una decisión humana validada.
