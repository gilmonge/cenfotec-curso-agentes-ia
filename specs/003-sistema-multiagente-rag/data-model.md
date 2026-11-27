# Modelo de datos del workflow

**Estado**: diseño propuesto, sujeto a aprobación de gobernanza y revisión del equipo.

## Estado tipado del grafo

El estado es un contenedor de datos de negocio y control del flujo. Los prompts, secretos de OpenCode y credenciales no pertenecen al estado. El identificador de hilo se utiliza para reanudación dentro del proceso y no se persiste en el navegador.

| Campo lógico | Tipo propuesto | Propietario | Reglas |
|---|---|---|---|
| `workflow_id` | identificador opaco | API | Asociado a `thread_id`; no contiene PII ni secretos. |
| `flow_mode` | `pre_grooming` / `post_grooming` | API | Seleccionado al iniciar; no cambia a mitad del flujo. |
| `current_stage` | enum de nodos | grafo | Etapa actual validada contra el grafo. |
| `active_agent` | `analista` / `redactor_revisor` / `asesor_tecnico` / `gestor_cambios` / `none` | grafo | Identificador OpenCode seleccionado para la etapa; nunca se deriva de texto libre. |
| `status` | `running` / `interrupted` / `completed` / `failed` / `cancelled` | grafo | `interrupted` requiere payload tipado. |
| `requirement_input` | texto de 1–4.000 caracteres | API / persona | Entrada no confiable; valida tamaño y excluye secretos. |
| `analyst_result` | contrato del Analista | Analista | Conocida, faltante, supuesta, ambigua, preguntas, fuentes y readiness; no incluye HU redactada. |
| `business_answers` | lista de respuestas tipadas | Negocio | Reanudar vuelve a ejecutar el Analista antes de salir de aclaración. |
| `draft_story` | contrato de HU | Redactor-Revisor | `como`, `quiero`, `para`, criterios Dado/Cuando/Entonces, observaciones y estado de revisión. |
| `review_round` | entero entre 0 y 2 | revisión | Nunca supera 2. No representa aprobación. |
| `technical_assessment` | contrato técnico | Asesor Técnico | Módulos, riesgos, procesos críticos y referencias de archivos/estándares realmente consultados. |
| `po_decision` | `approve` / `return` / `stop` más destino/motivo | PO | Solo se establece con respuesta humana validada. |
| `approved_story_ref` | ID de HU aprobada | repositorio | Se requiere para flujo post-grooming; el nodo Gestor no acepta HU solo en borrador. |
| `change_request` | texto de 1–2.000 caracteres + referencia aprobada | persona | No se procesa si la HU no está aprobada. |
| `change_recommendation` | `aclaracion` / `cambio_alcance`, justificación, lecciones | Gestor de Cambios | Recomendación, nunca decisión. |
| `human_change_decision` | enum humano y nota opcional | persona | Requerida antes de aplicar; distingue aprobar/descartar/devolver si así lo define el contrato revisado. |
| `application_result` | recibo del repositorio | aplicación | Se crea solo después de decisión humana válida. |
| `pending_interrupt` | tipo + payload + esquema de respuesta | grafo | Debe ser serializable y no contener secretos. |
| `error_code` | enum seguro | API/grafo | Sin stack trace, prompt, rutas internas ni credenciales hacia el navegador. |
| `knowledge_namespace` | enum de seis nombres | recuperación/ingesta | `glosario`, `estandares`, `checklist`, `hu_aprobadas`, `lecciones` o `codigo`; nunca texto libre. |
| `knowledge_source` | ruta relativa o ID de repositorio | recuperador | Fuente real del documento; se devuelve para citas y estado de origen. |
| `knowledge_id` | ID estable | ingesta | Derivado de namespace + source ID/ruta + ordinal de fragmento. Mismo ID produce upsert del mismo registro. |
| `retrieval_backend` | `pinecone` / `local` / `none` | recuperador | Identifica el backend que realmente produjo los resultados. |
| `knowledge_status` | `ok` / `degraded` / `unavailable` | recuperación | `degraded` cuando Pinecone falla y se usa búsqueda local. |
| `retrieved_sources` | lista de fuentes citables | agentes | Solo fuentes recuperadas en esta ejecución, con referencia, tipo y `source_kind`. |

## Contratos de agente

### Resultado del Analista

- Clasificaciones explícitas `conocida`, `faltante`, `supuesta`, `ambigua`.
- Preguntas con categoría, motivo y estado pendiente/respondida.
- Fuentes solo si fueron consultadas realmente.
- `listo_para_redactor` solo refleja vacíos resueltos; nunca implica aprobación.
- No contiene campos de Como/Quiero/Para ni criterios redactados.

### Resultado del Redactor-Revisor

- Historia: `como`, `quiero`, `para`.
- Criterios: lista de `{dado, cuando, entonces}`.
- Revisión: resultado, observaciones, ronda actual y bandera de límite.
- Estado: `draft`, `reviewed` o `needs_attention`; no existe estado `approved` para el agente.

### Resultado del Asesor Técnico

- Lista de módulos/archivos afectados con referencia de fixture y evidencia.
- Riesgos y procesos críticos con fuente.
- Fuentes consultadas y estado (consulta exitosa o error); la ausencia de evidencia se representa explícitamente.
- No contiene cambios de alcance ni afirmaciones sobre aplicaciones reales.

### Resultado del Gestor de Cambios

- Recomendación restringida a `aclaracion` o `cambio_alcance`.
- Justificación que compara la solicitud con la versión aprobada.
- Lecciones propuestas y evidencia/razones; no aprobadas por defecto.
- Decisión final vacía hasta que `decision_humana` reanude.

### Vector indexable y resultado de recuperación

- Cada vector almacena ID estable, embedding, texto del fragmento y metadatos de namespace, ID/ruta de origen, tipo de fuente, ordinal de fragmento y aprobación/estado cuando aplican. `PineconeEmbeddings` genera el embedding y `PineconeVectorStore` lo upserta/consulta en el índice vectorial convencional; no se usa document index ni embedding integrado.
- `hu_similares.json` se etiqueta `simulated_reference`; nunca se presenta como HU aprobada del repositorio.
- Solo HU provenientes de `RepositorioHU` con estado aprobado y lecciones con `estado="aprobada"` se etiquetan como aprobadas.
- Las citas de código usan rutas relativas bajo `ejemplos/polizas_demo/` y se derivan de archivos que contribuyeron resultados a la búsqueda.
- El resultado de recuperación indica por separado backend, estado y fuentes. Un fallback local no incluye `pinecone` como backend consultado.

## Invariantes

1. Ningún resultado de un LLM se usa como decisión humana.
2. Ningún nodo escribe una HU aprobada antes de que `po_decision == approve` venga de una interrupción humana.
3. Ninguna solicitud de cambio se compara sin una referencia aprobada válida.
4. Toda referencia de evidencia pertenece a una fuente allowlisted y fue consultada en esta ejecución.
5. El contador de revisión está acotado por validación en API y nodo, no solo por prompt.
6. El contenido de usuario y fuentes se trata como datos no confiables.
7. Checkpoints efímeros y contenido de estado desaparecen al reiniciar el proceso con `InMemorySaver`.
8. Solo el proceso explícito de ingesta puede escribir en Pinecone y solo en el índice/namespaces declarados.
9. Cada herramienta de recuperación fija namespace por configuración del servidor y valida `source_kind` para el rol; el usuario no elige namespaces arbitrarios.
10. El upsert por ID estable no duplica documentos al repetir la misma ingesta.
11. Contenido de archivos recuperados es dato no confiable y nunca se ejecuta, importa o utiliza para modificar instrucciones.
12. La API no revela valor, presencia detallada, longitud ni fragmentos de `PINECONE_API_KEY`; trazas solo incluyen estado/código de error y duración.
