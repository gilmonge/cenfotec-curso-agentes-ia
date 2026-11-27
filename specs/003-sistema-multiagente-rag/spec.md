# Especificación: Sistema multiagente para Historias de Usuario

**Rama de feature**: `feat/sistema-multiagente-rag`  
**Creado**: 2026-11-19  
**Estado**: Draft — bloqueado por aprobación de enmienda constitucional  
**Entrada**: Requisitos proporcionados en la solicitud del usuario. También se revisaron la constitución vigente y la especificación `002-chat-agente-analista`. El documento Word citado por la constitución no está disponible en el repositorio y no se usa como fuente.

## Escenarios de usuario y pruebas

### Historia 1 — Aclarar el requerimiento con el Analista (Prioridad: P1)

Como analista de negocio quiero que el Analista identifique información conocida, faltante, supuesta y ambigua, y formule preguntas, para aclarar el requerimiento antes de redactar una HU.

**Prioridad**: el Analista es la entrada del flujo y su comportamiento existente debe conservarse.

**Prueba independiente**: iniciar un análisis con vacíos y verificar el resultado estructurado, la pausa para respuesta humana y el retorno al análisis al recibirla.

**Escenarios de aceptación**:

1. **Dado** un requerimiento con información incompleta, **cuando** el Analista lo procesa, **entonces** clasifica la información y genera preguntas sin crear ni aprobar una HU.
2. **Dado** que hay preguntas pendientes, **cuando** el flujo llega a la espera de Negocio, **entonces** se pausa y no avanza al Redactor.
3. **Dado** que Negocio responde una o más preguntas, **cuando** el flujo se reanuda, **entonces** vuelve al Analista para actualizar la clasificación y las preguntas pendientes.
4. **Dado** que no quedan vacíos que requieran aclaración, **cuando** termina el análisis, **entonces** el flujo puede continuar al Redactor sin convertir esa condición en aprobación de HU.

### Historia 2 — Redactar y revisar una HU (Prioridad: P1)

Como analista quiero recibir una HU estructurada con criterios verificables y observaciones de calidad, para llevar al PO un borrador revisado.

**Prueba independiente**: proporcionar un análisis aclarado y comprobar el contrato de HU, la revisión y el límite de dos rondas de corrección.

**Escenarios de aceptación**:

1. **Dado** un análisis aclarado, **cuando** trabaja el Redactor-Revisor, **entonces** produce una historia con Como/Quiero/Para y criterios Dado/Cuando/Entonces.
2. **Dado** un borrador, **cuando** la revisión detecta problemas, **entonces** devuelve observaciones concretas y permite corregir como máximo dos rondas.
3. **Dado** que persisten observaciones después del límite, **cuando** termina la revisión, **entonces** el borrador permanece sin aprobar y las observaciones se presentan al PO para que decida si lo devuelve o lo detiene.
4. **Dado** un resultado del Redactor-Revisor, **cuando** se valida, **entonces** cumple el contrato estructurado y no contiene una decisión de aprobación.

### Historia 3 — Consultar evidencia técnica ficticia (Prioridad: P1)

Como analista quiero que el Asesor Técnico señale módulos, riesgos y procesos críticos con evidencia de fuentes ficticias consultadas, para informar al PO sin atribuir conocimiento a sistemas reales.

**Prueba independiente**: ejecutar el asesor con fixtures de estándares y archivos Python ficticios, y verificar la evidencia y los límites de rol.

**Escenarios de aceptación**:

1. **Dado** el borrador de HU, **cuando** consulta el Asesor Técnico, **entonces** devuelve módulos afectados, riesgos y procesos críticos con rutas/nombres de archivos efectivamente consultados.
2. **Dado** que un archivo o estándar no fue consultado, **cuando** se crea el resultado, **entonces** no aparece como evidencia.
3. **Dado** que las fuentes son ficticias, **cuando** el asesor presenta hallazgos, **entonces** identifica su carácter simulado, no inventa código ni afirma conocer sistemas reales y no decide alcance.

### Historia 4 — Aprobar o devolver el borrador (Prioridad: P1)

Como PO quiero aprobar explícitamente una HU o devolverla a la etapa correcta, para mantener la decisión de producto en manos humanas.

**Prueba independiente**: pausar en la decisión del PO, reanudar con aprobación o devolución y verificar el destino y el registro resultante.

**Escenarios de aceptación**:

1. **Dado** el análisis, el borrador y la asesoría técnica, **cuando** el flujo llega al PO, **entonces** se interrumpe y espera una decisión humana explícita.
2. **Dado** que el PO aprueba, **cuando** se reanuda el flujo, **entonces** la HU se registra como aprobada en el repositorio existente.
3. **Dado** que el PO devuelve por una aclaración, contenido de HU o evidencia técnica, **cuando** se reanuda, **entonces** vuelve respectivamente al Analista, Redactor o Asesor Técnico e incluye el motivo humano.
4. **Dado** que no existe una aprobación humana válida, **cuando** se intenta guardar la HU aprobada, **entonces** se rechaza la operación.

### Historia 5 — Recomendar cómo tratar una solicitud nueva (Prioridad: P1)

Como PO quiero comparar una solicitud nueva con una HU aprobada y recibir una recomendación razonada, para decidir personalmente si es aclaración o cambio de alcance.

**Prueba independiente**: dar una HU aprobada y solicitudes de prueba, comprobar clasificación, razones, lecciones sugeridas, pausa humana y aplicación solo después de la decisión.

**Escenarios de aceptación**:

1. **Dado** un identificador de HU aprobada y una solicitud nueva, **cuando** trabaja el Gestor de Cambios, **entonces** compara ambos contenidos y recomienda `aclaracion` o `cambio_alcance` con justificación y lecciones propuestas.
2. **Dado** el resultado del Gestor, **cuando** termina su recomendación, **entonces** no modifica ni aprueba la HU y se interrumpe para una decisión humana.
3. **Dado** que una persona decide, **cuando** reanuda el flujo, **entonces** se aplica y registra exactamente la decisión humana en el alcance autorizado.
4. **Dado** que la HU indicada no está aprobada o no existe, **cuando** se solicita el análisis de cambio, **entonces** el flujo no compara ni registra cambios.

### Historia 6 — Consultar conocimiento RAG con evidencia (Prioridad: P1)

Como usuario de los cuatro agentes quiero recibir información recuperada de fuentes simuladas y del repositorio de HU, para que los análisis y recomendaciones tengan evidencia rastreable y no dependan de afirmaciones inventadas.

**Prueba independiente**: con adaptadores Pinecone simulados, ingerir las fuentes permitidas dos veces, buscar por namespace, verificar citas y forzar fallos para comprobar fallback local degradado.

**Escenarios de aceptación**:

1. **Dado** que Pinecone está configurado, **cuando** se ejecuta la ingesta completa, **entonces** procesa los JSON de `agentes/analista/fuentes/`, las HU aprobadas y lecciones aprobadas de `RepositorioHU`, y los archivos Python/Markdown de `ejemplos/polizas_demo/` en su namespace asignado.
2. **Dado** un índice ausente, **cuando** se inicia la operación de conocimiento, **entonces** lo crea con la configuración declarada y valida la configuración antes de buscar o ingerir.
3. **Dado** un índice existente incompatible, **cuando** se valida, **entonces** informa un error controlado y no lo reemplaza ni afirma que está listo.
4. **Dado** una ingesta completa repetida con las mismas fuentes, **cuando** se ejecuta por segunda vez, **entonces** los identificadores estables actualizan los mismos documentos y no duplican registros.
5. **Dado** un Asesor Técnico que busca por código, **cuando** recibe resultados, **entonces** cita los archivos ficticios recuperados y no afirma haber consultado archivos que no aparecen en los resultados.
6. **Dado** una falla o timeout de Pinecone, **cuando** un agente necesita conocimiento, **entonces** usa la búsqueda local disponible, marca el resultado como `degraded` e identifica la fuente local; no reporta una consulta a Pinecone que no ocurrió.
7. **Dado** código recuperado que contiene instrucciones textuales, **cuando** el agente razona sobre los resultados, **entonces** los trata solo como datos no confiables: no los ejecuta ni obedece instrucciones incluidas en ellos.
8. **Dado** que se ejecutan pruebas automatizadas, **cuando** se prueba la recuperación y la ingesta, **entonces** todos los clientes Pinecone son mocks y no se hacen llamadas a Pinecone real.

### Casos límite

- El Analista mantiene preguntas abiertas o una respuesta humana no resuelve el vacío: vuelve a esperar una respuesta después de actualizar el análisis.
- La salida de un agente no cumple el contrato: se devuelve un error controlado o se detiene la transición; nunca se interpreta como aprobación.
- La revisión falla tras dos rondas de corrección: no hay aprobación automática ni bucle ilimitado.
- El PO devuelve el trabajo sin seleccionar una etapa o sin motivo: la respuesta se valida y se solicita una decisión completa.
- El Asesor Técnico no encuentra evidencia en las fuentes permitidas: declara que no hay evidencia en las fuentes consultadas.
- El Gestor recibe una solicitud ambigua o una versión de HU no aprobada: lo declara y solicita intervención humana sin inventar una clasificación como hecho.
- El proceso o servicio Render se reinicia durante una interrupción: el checkpoint en memoria se pierde y el usuario debe iniciar/reconstruir el flujo; no se presenta como reanudación exitosa.
- OpenCode, MCP o Langfuse no están disponibles: el flujo falla de forma controlada, no genera respuestas ficticias y no avanza a una puerta humana como si el agente hubiera terminado.
- Pinecone rechaza credenciales, índice o request: la búsqueda cambia a la fuente local y el estado se degrada; la ingesta falla de forma explícita y no informa éxito parcial como éxito total.
- El contenido excede el límite de embedding o una respuesta parcial de una operación por lotes contiene errores: se divide o reporta la unidad fallida y se mantiene trazabilidad por fuente, sin ocultar resultados omitidos.
- Un índice existente tiene el nombre esperado, pero dimensión, métrica, región o modelo distintos: no se cambia ni se elimina automáticamente.
- Una fuente JSON o registro de repositorio no cumple el esquema esperado o incluye datos personales detectables: se excluye o se detiene su ingesta con error seguro; no se indexa silenciosamente.

## Requisitos

### Requisitos funcionales

- **FR-001**: El sistema DEBE exponer cuatro responsabilidades separadas: Analista de Requerimientos, Redactor-Revisor, Asesor Técnico y Gestor de Cambios.
- **FR-002**: El Analista DEBE conservar sus capacidades existentes para clasificar información conocida, faltante, supuesta y ambigua, consultar las fuentes permitidas, formular preguntas y esperar respuestas humanas. NO DEBE redactar ni aprobar HU.
- **FR-003**: Con preguntas pendientes, el flujo DEBE interrumpirse para Negocio y, al recibir una respuesta, regresar al Analista antes de continuar.
- **FR-004**: El Redactor-Revisor DEBE generar HU con Como/Quiero/Para, criterios Dado/Cuando/Entonces, observaciones y una salida validable como contrato estructurado. NO DEBE aprobar.
- **FR-005**: La revisión DEBE limitarse a un máximo de dos rondas de corrección. Si persisten problemas, el resultado DEBE seguir marcado como no aprobado y quedar a decisión del PO.
- **FR-006**: El Asesor Técnico DEBE consultar estándares y un repositorio ficticio de código Python, identificar módulos afectados, riesgos y procesos críticos, y declarar evidencia de fuentes realmente consultadas. NO DEBE inventar código, afirmar conocimiento de sistemas reales ni decidir alcance.
- **FR-007**: Antes del grooming, el flujo DEBE seguir Analista → espera de Negocio → Redactor → revisión → Asesor Técnico → aprobación del PO → repositorio de HU; las decisiones condicionales DEBEN preservar esa secuencia y sus bucles definidos.
- **FR-008**: La aprobación del PO DEBE requerir una intervención humana explícita. Una devolución DEBE volver a la etapa indicada por la persona con su motivo; la falta de decisión no equivale a aprobación.
- **FR-009**: Solo una HU aprobada explícitamente por una persona DEBE guardarse como HU aprobada.
- **FR-010**: Después del grooming, el Gestor de Cambios DEBE comparar una solicitud con una HU aprobada, recomendar exclusivamente `aclaracion` o `cambio_alcance`, explicar su recomendación y proponer lecciones.
- **FR-011**: El Gestor de Cambios NO DEBE aprobar ni decidir. El flujo DEBE interrumpirse para una decisión humana y aplicar únicamente esa decisión tras reanudar.
- **FR-012**: Las salidas entre etapas DEBEN usar contratos estructurados validados. Una salida inválida, incompleta o una falla de herramienta DEBE detener o enrutar de forma controlada, sin inferir aprobación.
- **FR-013**: El historial necesario para reanudar una intervención DEBE usar almacenamiento de checkpoints en memoria en la primera versión; la interfaz y documentación DEBEN informar que un reinicio de Render pierde esos estados.
- **FR-014**: Todo backend y agente DEBE permanecer en Python. La interfaz existente DEBE conservar React y SCSS, mostrar las salidas estructuradas y permitir intervenciones humanas sin eliminar las pantallas ni simulaciones existentes.
- **FR-015**: OpenCode DEBE seguir como motor generativo. Pinecone se limita a generar embeddings y recuperar vectores de conocimiento; el sistema NO DEBE crear servicios Render adicionales.
- **FR-016**: El sistema NO DEBE acceder a secretos, imprimirlos, registrarlos, incluirlos en trazas ni enviarlos al navegador. La clave Pinecone se lee exclusivamente del entorno de ejecución.
- **FR-017**: El backend DEBE crear automáticamente, si falta, y validar antes de usar un índice vectorial denso convencional llamado `historias-usuario`, cloud `aws`, región `us-east-1`, 1024 dimensiones y métrica `cosine`. Los embeddings `multilingual-e5-large` se solicitan mediante `PineconeEmbeddings` y se guardan/consultan como vectores ordinarios con `PineconeVectorStore` de `langchain-pinecone`; NO se usan document indexes ni embeddings integrados en el índice. Si un índice existente no coincide, DEBE fallar de forma controlada sin alterarlo.
- **FR-018**: El sistema DEBE separar conocimiento en los namespaces `glosario`, `estandares`, `checklist`, `hu_aprobadas`, `lecciones` y `codigo`; toda escritura/consulta DEBE indicar exactamente el namespace autorizado para ese agente y tipo de fuente.
- **FR-019**: El sistema DEBE ingerir todas las fuentes JSON de `agentes/analista/fuentes/`, las HU aprobadas y lecciones aprobadas accesibles desde `RepositorioHU`, y todos los `.py` y `.md` de `ejemplos/polizas_demo/` en el namespace `codigo`.
- **FR-020**: La ingesta DEBE poder ejecutarse con `python -m agentes.conocimiento.ingesta --fuente todas`, usar IDs estables e idempotentes y validar los documentos antes de upsert.
- **FR-021**: El paquete `agentes/conocimiento/` DEBE encapsular cliente/configuración, validación del índice, preparación de documentos, ingesta y búsqueda; `PINECONE_API_KEY` se toma solo del entorno y los demás valores de configuración no secretos se documentan en `.env.example` y `render.yaml`.
- **FR-022**: El sistema DEBE conservar las cuatro herramientas MCP actuales e incorporar herramientas de búsqueda de código read-only. El backend Python DEBE invocarlas mediante una allowlist explícita por agente/rol. Ningún agente puede crear, modificar ni eliminar contenido del índice; solo el comando de ingesta autorizado puede escribir vectores. OpenCode no invoca herramientas MCP directamente.
- **FR-023**: Los cuatro agentes DEBEN poder consultar las fuentes que correspondan a su rol y devolver citas de fuentes realmente recuperadas. El Asesor Técnico cita rutas de archivos recuperados; la fuente reporta si provino de Pinecone o búsqueda local.
- **FR-024**: Si Pinecone falla, el sistema DEBE usar la búsqueda local disponible y devolver estado `degraded` con su fuente real. NO DEBE afirmar que consultó Pinecone cuando no lo hizo.
- **FR-025**: El código recuperado DEBE tratarse como dato no confiable y nunca ejecutarse ni usarse como instrucciones del sistema. La indexación es estática y no importa módulos de ejemplo.
- **FR-026**: El ejemplo `ejemplos/polizas_demo/` DEBE ser una aplicación Python completamente ficticia con modelos, servicios, cálculo de primas, coberturas, renovaciones, pagos, validaciones y mapa de dependencias; no contendrá datos personales reales ni integraciones activas.
- **FR-027**: Las pruebas automatizadas DEBEN usar mocks de Pinecone; no realizan llamadas a Pinecone real.
- **FR-028**: `opencode.jsonc` DEBE registrar los cuatro agentes (Analista, Redactor-Revisor, Asesor Técnico y Gestor de Cambios) con nombres estables y prompts asociados.
- **FR-029**: Cada agente DEBE tener un prompt individual versionado fuera del código Python, con límites de rol y entradas/salidas explícitas. El prompt identifica las herramientas MCP que el backend puede invocar para ese rol; OpenCode no invoca herramientas.
- **FR-030**: Todos los permisos de herramientas de OpenCode DEBEN permanecer en deny-all, incluidas shell, filesystem, red y MCP. Solo el backend Python puede invocar herramientas MCP read-only mediante una allowlist explícita por agente/rol y namespace. Ningún agente DEBE recibir shell, acceso libre al filesystem, escritura ni acceso de red general. Cambiar esta arquitectura requiere justificación de seguridad explícita, revisión humana y validación de aislamiento antes de autorizarse.
- **FR-031**: `OpenCodeClient` DEBE seleccionar el agente configurado que corresponde al nodo/rol invocado y fallar de forma controlada si el agente o prompt no coincide; no debe usar implícitamente el agente `analista` para todos los roles.
- **FR-032**: Las pruebas DEBEN ejecutar el enrutamiento de cada agente y demostrar selección y prompt correctos, denegación total de herramientas en OpenCode, allowlist MCP efectiva en el backend Python y aislamiento de salidas, herramientas y namespaces por rol mediante OpenCode/MCP simulados.
- **FR-033**: Los contratos DEBEN limitar el requerimiento de entrada a 4.000 caracteres, la solicitud de cambio a 2.000 caracteres y permitir como máximo una operación activa por workflow; rechazos no deben cambiar el checkpoint.

### Entidades principales

- **Análisis aclarado**: requerimiento, clasificaciones, preguntas y respuestas humanas, fuentes consultadas y estado de preparación.
- **Borrador de HU**: Como/Quiero/Para, criterios, observaciones, revisión y número de rondas.
- **Evidencia técnica**: módulos afectados, riesgos, procesos críticos y referencias exactas a archivos o estándares ficticios consultados.
- **Documento de conocimiento**: namespace, fuente/ID original, contenido por fragmento, ID estable, clase/tipo de fuente y referencias para cita. El contenido recuperado permanece marcado como no confiable.
- **Estado de recuperación**: backend utilizado (`pinecone` o `local`), disponibilidad/degradación y fuentes realmente recuperadas.
- **Decisión del PO**: aprobar, devolver a una etapa con motivo o detener el flujo.
- **Solicitud de cambio**: HU aprobada de referencia, texto nuevo, recomendación, justificación, lecciones propuestas y decisión humana.
- **Estado del flujo**: estado tipado compartido, etapa actual, contador de revisiones, interrupción pendiente y resultados de agentes.

## Criterios de éxito

- **SC-001**: En todos los casos de prueba del contrato, el Analista no entrega una HU y ninguna de las otras tres responsabilidades ejecuta una decisión reservada a una persona.
- **SC-002**: Las pruebas de transiciones cubren el recorrido nominal y cada devolución admitida; no hay transiciones fuera del grafo especificado.
- **SC-003**: La revisión ejecuta como máximo dos rondas de corrección y no produce aprobación automática si falla.
- **SC-004**: Cada HU marcada aprobada tiene una decisión humana explícita asociada; una ausencia o rechazo de esa decisión no crea una HU aprobada.
- **SC-005**: Cada evidencia técnica reportada corresponde a una fuente permitida realmente consultada, y toda fuente ficticia se identifica como tal.
- **SC-006**: La reanudación por intervención humana conserva la etapa y el estado esperados durante la vida del proceso; un reinicio del proceso no se presenta como checkpoint recuperado.
- **SC-007**: Las pruebas del flujo y contratos se ejecutan con mocks, sin llamadas de generación a OpenCode ni uso de presupuesto externo.
- **SC-008**: En mocks de SDK, índice ausente se crea con la configuración exacta y un índice incompatible se rechaza antes de ingerir o buscar.
- **SC-009**: Una ingesta idéntica repetida produce el mismo conjunto de IDs por namespace, sin documentos duplicados.
- **SC-010**: Las seis namespaces contienen solo sus clases de fuentes permitidas, y ninguna consulta devuelve conocimiento de otra namespace.
- **SC-011**: En todos los fallos simulados de Pinecone, la respuesta usa fuente local con estado `degraded` y no atribuye recuperación a Pinecone.
- **SC-012**: Las pruebas adversariales confirman que instrucciones presentes en contenido recuperado no cambian rol, permisos ni transiciones y que ningún archivo se ejecuta.
- **SC-013**: Las pruebas simuladas confirman que cada responsabilidad selecciona su propio agente/prompt, OpenCode no puede invocar herramientas, y el backend Python solo ejecuta herramientas MCP y accede a namespaces permitidos para ese rol.

## Supuestos y dependencias

- Los requisitos de esta especificación provienen de la solicitud del usuario y de los artefactos presentes; el documento Word citado en la constitución está ausente y no se infiere su contenido.
- El Analista actual y sus contratos se conservan y se reutilizan. La implementación se apoya en los módulos existentes citados en el plan.
- La propuesta de enmienda constitucional `docs/constitution-multiagent-system-proposal.md` debe ser revisada y aprobada por el equipo antes de cualquier código funcional.
- La aprobación de la enmienda y la revisión coherente de spec, plan y tareas son puertas previas a la implementación.
- El repositorio ficticio del Asesor Técnico será un conjunto versionado de fixtures Python/estándares, distinto del repositorio existente de HU aprobadas.
- `hu_similares.json` no declara estado de aprobación. Se indexará como referencia simulada en `hu_aprobadas` con metadatos de origen que la distingan; el Gestor de Cambios consultará exclusivamente HU marcadas como aprobadas y provenientes de `RepositorioHU`.
- Del repositorio existente, se indexan únicamente HU aprobadas y lecciones con estado `aprobada`, en línea con el modelo documentado de `RepositorioHU`.
- Se usará un índice vectorial convencional mediante `langchain-pinecone`; el flujo no usa la API de document indexes ni embeddings integrados.
- La memoria de conversación y los checkpoints de LangGraph no serán persistencia histórica; se perderán al reiniciar el servicio.
