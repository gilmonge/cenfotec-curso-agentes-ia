# Plan de implementación: Sistema multiagente para Historias de Usuario

**Rama**: `feat/sistema-multiagente-rag` | **Fecha**: 2026-11-21 | **Spec**: [spec.md](spec.md)
**Entrada**: Requisitos proporcionados por el usuario; constitución vigente; especificación `002-chat-agente-analista`.

> **Estado del gate**: La constitucion 2.0.0 esta presente en esta rama y la PR correctiva #4 esta fusionada. La verificacion de GitHub muestra que la PR no recibio reviews y la constitucion conserva `Ratification status: pending a human approval recorded in GitHub`; T001 sigue abierto. La spec se reviso contra el texto 2.0.0: la base de LangGraph, los cuatro roles, OpenCode deny-all y el aislamiento MCP son compatibles. Por instruccion explicita del usuario se implementa unicamente T005-T009 y T055-T060; no se avanza a etapas posteriores. El gate documental no se declarara cerrado hasta contar con ratificacion verificable en GitHub.

## Resumen

Extender el backend Python del Analista a dos flujos coordinados por un `StateGraph` tipado de LangGraph, y añadir recuperación de conocimiento con un índice Pinecone serverless y namespaces separados. Se conservan el Analista, OpenCode, LangChain, las cuatro herramientas MCP actuales, React y SCSS. Las esperas humanas interrumpen el grafo; `InMemorySaver` pierde checkpoints al reiniciar FastAPI/Render. Pinecone es una integración externa desde el servicio existente, no un servicio Render adicional.

## Contexto técnico

**Lenguaje/versión**: Python 3.12, confirmado por el Dockerfile actual; React/JavaScript/SCSS permanecen en frontend.
**Dependencias principales**: FastAPI, Pydantic, LangChain, `langchain-pinecone`, Pinecone Python SDK, OpenCode, MCP y Langfuse; `langgraph` se declara como dependencia directa. Validar y fijar versiones compatibles con Python 3.12 en implementación, sin actualizar dependencias ajenas.
**Persistencia**: `InMemorySaver` para checkpoints del grafo; `agentes/analista/memory/repositorio.py` para HU/lecciones aprobadas; un único índice Pinecone externo con namespaces; no confundir estos almacenes ni duplicar historia de workflow en Pinecone.  
**Pruebas**: pytest existente, mocks de OpenCode/MCP/repositorio, pruebas unitarias de nodos, contratos y transiciones; no se realizan llamadas reales a modelos.  
**Plataforma**: backend actual y despliegue actual; ningún servicio Render adicional.  
**Metas de desempeño**: no se fija SLA nuevo en ausencia de mediciones/requisitos; se reutilizan deadlines y errores controlados del backend existente donde apliquen.  
**Limites**: conservar el rol del Analista; la implementacion actual se limita a T005-T009 y T055-T060; Asesor solo lee evidencia permitida; agentes consultan Pinecone en modo read-only; la unica escritura a Pinecone ocurre por el comando de ingesta sobre fuentes permitidas; no crear servicios Render adicionales; no registrar secretos, codigo completo ni datos personales en observabilidad.

## Puerta constitucional

| Revisión | Resultado actual | Acción previa a implementación |
|---|---|---|
| Constitucion 2.0.0 y alcance | Texto 2.0.0 presente y alcance compatible; PR #4 fusionada sin review y el estado de ratificacion sigue pendiente | Obtener aprobacion humana registrada en GitHub antes de cerrar T001 |
| Stack | React/SCSS y Python se mantienen | Agregar cambios del frontend solo con JSX/SCSS existentes |
| OpenCode | Se mantiene como único motor de IA | Reutilizar `opencode_client.py`; no llamar proveedores directamente |
| Seguridad | Lectura de conocimiento en allowlist; escritura Pinecone confinada a ingesta explícita; secreto solo en entorno | OpenCode deny-all; el backend Python aplica allowlist MCP por agente/rol y namespace; índice fijo, validación de esquema y redacción de trazas |
| Checkpoint | `InMemorySaver` solicitado | Documentar pérdida al reiniciar; no llamarlo persistencia permanente |
| Spec Kit | Revision de `spec.md` contra el texto 2.0.0 completada; no se encontraron contradicciones en el alcance de esta fase | Registrar la ratificacion y cerrar T001/T002 en `tasks.md` |

## Decisiones técnicas propuestas (condicionadas a aprobación)

1. **Un grafo, responsabilidades separadas**: un `StateGraph` con nodos Python para `analista`, `espera_negocio`, `redactor`, `revision`, `asesor_tecnico`, `aprobacion_po`, `repositorio`, `gestor_cambios`, `decision_humana` y `aplicar_decision`. No se despliegan cuatro microservicios.
2. **Estado tipado**: `TypedDict`/esquema de estado del grafo con modelos Pydantic para entradas y resultados de agentes. Mantener datos normalizados en estado y generar prompts en cada nodo; validar antes de cualquier transición o escritura.
3. **Human-in-the-loop**: `interrupt()` en espera de Negocio, aprobación del PO y decisión de cambio. La API de reanudación valida el contrato humano y ejecuta `Command(resume=...)` con el mismo `thread_id`. Las devoluciones del PO incluyen etapa destino y motivo validados.
4. **Grafo pre-grooming**: `analista → espera_negocio → redactor → revision → asesor_tecnico → aprobacion_po → repositorio`. `espera_negocio` interrumpe si hay preguntas; al reanudar con respuestas vuelve a `analista`. Si no hay preguntas pendientes, continúa a `redactor`. `revision` puede devolver a `redactor` hasta completar dos rondas de corrección; después expone observaciones al PO sin aprobar. El PO puede retornar a Analista, Redactor o Asesor según su instrucción, aprobar explícitamente o detener.
5. **Grafo post-grooming**: `gestor_cambios → decision_humana → aplicar_decision`. El Gestor solo recibe HU aprobada. El nodo de decisión interrumpe; el nodo de aplicación registra únicamente la decisión humana, reutilizando el repositorio existente y sin escribir en sistemas externos.
6. **Repositorio ficticio técnico**: fuentes Python y estándares simulados/anonimizados con identificador de fuente, ruta permitida y evidencia consultada. El Asesor no lee el filesystem libre ni repositorios remotos. Su evidencia no se mezcla con el repositorio persistente de HU.
7. **OpenCode y LangChain**: reutilizar el cliente OpenCode y la construcción de prompts/parsing del orquestador existente. LangChain se usa funcionalmente en cadenas y parseo tipado de las salidas; LangGraph coordina estados y transiciones. No se asume un endpoint OpenAI de OpenCode.
7a. **Agentes y herramientas**: registrar en `opencode.jsonc` los cuatro agentes con identificadores distintos y prompts externos individuales. Mantener todos los permisos de herramientas OpenCode en deny-all, incluida MCP. El backend Python aplica una allowlist read-only por agente/rol y namespace y es el único que invoca MCP. `OpenCodeClient` recibe y valida el agente seleccionado en cada llamada; las pruebas con OpenCode/MCP simulados verifican selección, denegación total en OpenCode y aislamiento del backend.
8. **Memoria**: una instancia `InMemorySaver` enlazada al grafo. La reanudación está disponible solo mientras vive el proceso; un reinicio del servicio Render pierde checkpoints. No implementar almacenamiento permanente nuevo en esta fase.
9. **Observabilidad**: reutilizar `observability.py`, correlacionar operación/etapa con IDs existentes y registrar nombre de agente, duración, estado y herramienta; nunca prompt, respuesta completa, secretos ni datos personales. Fallas de Langfuse no deben convertir un resultado incompleto en éxito.
10. **API y frontend**: extender FastAPI con endpoints de inicio/avance/reanudación tipados y extender la UI actual con vistas/controles de estado, pregunta humana, devolución, aprobación y decisión. Mantener contratos existentes del Analista y rutas/pantallas; no añadir TypeScript, bibliotecas UI o persistencia de estado en el navegador.
11. **Índice vectorial y embeddings**: usar un índice vectorial denso convencional `historias-usuario`, `1024` dimensiones, métrica `cosine`, serverless en AWS `us-east-1`. `PineconeEmbeddings(model="multilingual-e5-large")` genera los vectores y `PineconeVectorStore` de `langchain-pinecone` realiza upsert/búsqueda por vector. No usar document index, esquema integrado, campos de texto con embedding integrado ni APIs `documents.*`. Validar el índice antes de upsert/búsqueda y nunca borrar/recrear uno incompatible. Leer `PINECONE_API_KEY` solo del entorno.
12. **Namespaces cerrados**: `glosario`, `estandares`, `checklist`, `hu_aprobadas`, `lecciones`, `codigo`. Cada consulta e ingesta escoge namespace desde una enum allowlisted, nunca desde texto libre del usuario.
    - Analista: `glosario`, `estandares`, `checklist` y referencias de `hu_aprobadas`.
    - Redactor-Revisor: `estandares`, `checklist` y referencias/HU aprobadas de `hu_aprobadas`.
    - Asesor Técnico: `estandares` y `codigo`.
    - Gestor de Cambios: solo HU aprobadas de `hu_aprobadas` y lecciones aprobadas de `lecciones`.
13. **Fuentes y procedencia**: JSON de `agentes/analista/fuentes/` se asigna por fuente; HU aprobadas y lecciones aprobadas provienen de `RepositorioHU`; `.py`/`.md` de `ejemplos/polizas_demo/` se procesan estáticamente. `hu_similares.json` no contiene estado de aprobación, se ingresa como referencia simulada y queda distinguible de historias aprobadas por metadatos de origen.
14. **Esquema de indexación**: fragmentos deterministas con ID estable de namespace + fuente/ID original + ordinal de fragmento; upsert reemplaza el vector con el mismo ID. Reconciliar IDs obsoletos solo dentro de la fuente y namespace de la ingesta. Fragmentar bajo el límite del modelo de embeddings validado en T005.
15. **CLI y permisos**: `python -m agentes.conocimiento.ingesta --fuente todas` crea/valida el índice e ingiere fuentes permitidas. Solo este comando escribe Pinecone. Herramientas MCP existentes siguen disponibles; nuevas herramientas de código/RAG consultan solamente y registran namespace/fuente realmente usada.
16. **Degradación**: si Pinecone no está disponible o la configuración no valida, las búsquedas usan las fuentes locales de `mcp/tools.py`, `RepositorioHU` y fixtures de código locales, con `source_backend="local"` y estado `degraded`. Las respuestas no atribuyen resultados a Pinecone.
17. **Inyección y ejecución**: indexación nunca importa ni ejecuta los `.py` del ejemplo. El recuperador delimita los fragmentos como datos no confiables y los agentes no pueden convertirlos en instrucciones, tools ni acciones.
18. **Configuración de despliegue**: añadir defaults no secretos de index/cloud/region/dimension/metric/model y `PINECONE_API_KEY` con `sync: false` a `.env.example` y `render.yaml`. No insertar una clave ni añadir un servicio Render.

## Reutilización y límites de impacto

- `agentes/analista/core/opencode_client.py`: única conexión al motor OpenCode.
- `opencode.jsonc` y `agentes/analista/prompts/`: registrar los cuatro agentes con herramientas de OpenCode en deny-all y sus prompts individuales; el backend Python aplica la allowlist MCP por rol y OpenCodeClient selecciona explícitamente el agente para cada nodo.
- `agentes/analista/core/orchestrator.py`: reutilizar utilidades de prompts, ejecución y validación LangChain; separar la coordinación del grafo sin cambiar el contrato actual del Analista.
- `agentes/analista/core/models.py`: conservar modelos actuales y añadir contratos tipados del workflow sin romper el API actual.
- `agentes/analista/memory/repositorio.py`: guardar HU únicamente después de aprobación humana; registrar cambio/lecciones solo después de la decisión humana.
- `agentes/analista/mcp/tools.py`: preservar herramientas permitidas del Analista y exponer acceso read-only, allowlisted a fixtures técnicos.
- `agentes/analista/core/observability.py`: añadir spans seguros por nodo sin registrar contenido.
- `agentes/analista/mcp/tools.py`: conservar `consultar_glosario`, `buscar_hu_similares`, `consultar_estandares` y `aplicar_checklist_vacios`; añadir búsquedas read-only que delegan en conocimiento y fallback local.
- `agentes/analista/fuentes/*.json`: ingesta de todas las fuentes existentes; `hu_similares.json` retiene `source_kind=simulated_reference`.
- `agentes/analista/memory/repositorio.py`: usar solo APIs existentes para listar HU/lecciones, filtrar aprobadas y transformar campos sin introducir SQL de ingestión nuevo.
- Nuevo `agentes/conocimiento/`: settings/cliente Pinecone, esquema de índice, contratos/documentos, chunking, IDs estables, ingesta CLI y recuperación/fallback.
- Nuevo `ejemplos/polizas_demo/`: módulos Python y Markdown ficticios, completos y claramente rotulados como demostración; nunca se importan ni ejecutan durante la ingesta.
- Frontend: React/JSX/SCSS existentes; aprobación y decisión humanas requieren controles visibles y accesibles. El Stepper simulado y pantallas actuales permanecen.

## Estructura propuesta

```text
agentes/analista/
├── api/routes/                 # rutas actuales + workflow y reanudación
├── core/
│   ├── models.py               # contratos y estado tipado
│   ├── orchestrator.py         # compatibilidad con Analista y utilidades LangChain
│   ├── workflow_graph.py       # StateGraph, nodos y rutas
│   └── agents/                 # redactor_revisor, asesor_tecnico, gestor_cambios
├── mcp/                        # herramientas actuales + allowlist de fixtures
├── prompts/                    # prompts individuales por agente externos a Python
└── tests/                      # nodos, contratos, grafo, API y reanudación
agentes/conocimiento/
├── client.py                   # adapter Pinecone + validación de índice
├── documents.py                # modelos de fuente, fragmentos e IDs estables
├── ingestion.py                # pipelines allowlisted y repositorio
├── retrieval.py                # búsqueda por namespace y fallback local
└── ingesta.py                  # python -m agentes.conocimiento.ingesta
ejemplos/polizas_demo/
├── modelos.py
├── servicios/                  # pólizas, primas, coberturas, renovaciones, pagos, validaciones
└── mapa_dependencias.md
src/                            # interfaz existente React/JSX/SCSS
specs/003-sistema-multiagente-rag/
```

Esta estructura es propuesta de plan y no implica que ya se hayan creado módulos o fixtures funcionales.

## Riesgos y controles

- **Cambio constitucional rechazado o aún pendiente**: no iniciar implementación; solicitar decisión del equipo por el flujo de Governance.
- **Analista regresiona o redacta HU**: probar sus contratos y rol antes/después; mantenerlo como nodo independiente con transición de salida explícita.
- **Reanudar en una etapa incorrecta**: guardar etapa y estado tipado en checkpoints; pruebas con `thread_id`, interrupciones y destinos de devolución.
- **Aprobación accidental**: aceptación explícita, autenticidad/validez de respuesta humana en backend, y escritura posterior a decisión; nunca deducir aprobación de `listo_para_redactor` o de revisión satisfactoria.
- **Evidencia técnica inventada**: lista cerrada de archivos fixture, resultados de lectura tipados, y referencias de fuente obligatorias en el contrato.
- **Persistencia efímera mal entendida**: mostrar el límite antes de suspender y documentar pérdida tras reinicio del servicio.
- **Índice preexistente incompatible**: describir el recurso y comparar nombre, deployment, cloud/region, dimensión, métrica y modelo; detenerse sin eliminar/recrear ni escribir si algo difiere.
- **Namespaces mezclados**: validar namespace en un enum backend y filtrar por `source_kind`; el Gestor de Cambios solo lee `approved_repository_story` y lecciones aprobadas.
- **Fallback engañoso**: distinguir `pinecone`, `local` y `degraded` en contratos; tests fuerzan todas las fallas y prohíben reportar Pinecone si no se completó consulta.
- **Ingesta parcial o fuentes obsoletas**: validar entradas por archivo/registro, devolver conteos y errores sin secreto; IDs estables y reconciliación limitada al origen/namespace.
- **Prompt injection en código/datos recuperados**: marcado de datos no confiables, sin ejecución/import/eval/shell y pruebas adversariales sobre texto recuperado.
- **Costo de embeddings**: la carga y búsqueda solo ocurren en comandos/integración autorizados; pruebas automáticas usan mocks y no consumen cuotas de embeddings/Pinecone.
- **Confusión de repositorios**: separar el repositorio ficticio de código Python del repositorio de HU del proyecto.
- **Regresión del frontend**: conservar rutas, Stepper, mocks y estilos; cubrir los contratos de UI sin cambios funcionales no especificados.

## Estrategia de verificación posterior al gate

Cuando se apruebe la enmienda y el plan actualizado, ejecutar pytest del backend focalizado en: nodos, transiciones, loop de preguntas, dos rondas máximo, interrupciones/reanudaciones, decisión humana, contratos, inyección de instrucciones, fallback local, errores Pinecone, validación de índice/namespaces, recuperación y doble ingesta con IDs iguales. Usar mocks de OpenCode, MCP, Pinecone y repositorio. No llamar Pinecone real en pruebas automáticas. Después ejecutar el conjunto Python solicitado y registrar el resultado real. No se afirma prueba ni implementación de la feature en este borrador.

## Artefactos de diseño

- [research.md](research.md) — decisiones y fuentes técnicas.
- [data-model.md](data-model.md) — estado tipado y entidades.
- [contracts/workflow-api.md](contracts/workflow-api.md) — contratos propuestos del backend.
- [quickstart.md](quickstart.md) — arranque y verificación previstos en PowerShell.
- [tasks.md](tasks.md) - alcance, dependencias y evidencia de la fase actual; T001 continua abierto.

## Seguimiento de complejidad

| Complejidad | Motivo | Alternativa simple considerada |
|---|---|---|
| Grafo multiagente con tres interrupciones | Necesario para reanudar aclaraciones y exigir decisiones humanas en los dos ciclos | Un agente único no mantiene separación de roles ni puntos explícitos de aprobación |
| Checkpoint en memoria, sin base nueva | Primera versión requerida; preserva despliegue actual | Una base persistente agregaría alcance, servicio/costos y política de retención no autorizados |
| Asesor sobre fuentes ficticias | Permite evidencia reproducible sin acceso a código productivo | Acceso a repositorio real contradice límites de seguridad y requisito de no inventar sistemas conocidos |
