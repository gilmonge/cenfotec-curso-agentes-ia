# Especificación funcional — Chat flotante del Agente Analista

**Identificador propuesto:** 001-chat-flotante-analista  
**Proyecto:** StoryCraft AI — Popular Seguros (prototipo académico)  
**Estado:** Propuesta para revisión con Spec Kit; no implementada  
**Rama de trabajo recomendada:** `feat/chat-agente-analista` (desde `main`)  
**Fuente de requisitos:** Definición de Agentes Popular Seguros (22 de octubre de 2026), prototipo de historias de usuario y requisitos adicionales del equipo.

## 1. Objetivo

Permitir al usuario de la aplicación web interactuar mediante un chat flotante con el **Agente Analista de Requerimientos** implementado en Python, que se conecta al LLM a través de un servidor OpenCode local; emplea LangChain para la orquestación y herramientas, MCP para acceder a fuentes simuladas y Langfuse para observabilidad. El chat debe preservar el contexto hasta que el usuario inicie una conversación nueva.

Este cambio **añade** una capacidad real de IA; no modifica automáticamente el Stepper actual ni sustituye las simulaciones de generación de historias de usuario.

## 2. Usuarios y alcance

- Usuario principal: analista de requerimientos / Product Owner; demostración a cargo del profesor.
- Entrada: conversación libre en español sobre un requerimiento del dominio de seguros. Puede incluir descripción, minuta, notas anonimizadas y respuestas de Negocio.
- Salida: respuesta legible en Markdown y análisis estructurado según el contrato, que la interfaz renderiza visualmente.
- Entorno: aplicación local React; backend Python; OpenCode Server local; fuentes de conocimiento locales, simuladas o anonimizadas.
- Se mantienen las pantallas, rutas, navegación, estilos SCSS y datos mock existentes.

## 3. Historias de usuario (priorizadas)

### US-01 (P1) — Chat accesible sin abandonar la pantalla

Como usuario de StoryCraft AI quiero abrir, minimizar y volver a abrir un chat flotante en la esquina inferior derecha para consultar al agente sin interrumpir el flujo de trabajo actual.

**Escenarios:**
1. Dado que navego por cualquier ruta, cuando presiono el botón de chat, entonces se abre el panel sin cambiar de página.
2. Dado que el panel está abierto, cuando presiono **Cerrar**, entonces se oculta el panel sin perder la conversación.
3. Dado que estoy en móvil, cuando abro el chat, entonces la ventana es utilizable sin desbordar la pantalla ni cubrir permanentemente la navegación.

### US-02 (P1) — Solicitud real al agente

Como usuario quiero enviar una descripción o pregunta y recibir la respuesta de un agente Python para analizar requisitos reales de ejemplo sin respuestas simuladas.

**Escenarios:**
1. Con servicios disponibles, al enviar el primer mensaje no vacío, el frontend llama a la API Python y muestra la respuesta del agente.
2. Con una respuesta en proceso, no puedo enviar un segundo mensaje de esa conversación hasta completar, fallar o cancelar la solicitud.
3. Con OpenCode detenido, veo un mensaje de error útil y puedo volver a intentar cuando regrese el servicio.

### US-03 (P1) — Continuidad y reinicio seguro

Como usuario quiero hacer preguntas de seguimiento y también iniciar una conversación nueva, incluso ante una ejecución bloqueada, para conservar o descartar el contexto según me convenga.

**Escenarios:**
1. Dada una conversación existente, al responder una pregunta pendiente, el agente conserva el contexto de ese mismo requerimiento.
2. Al elegir **Nuevo chat** o **Eliminar conversación**, el frontend invalida el historial visible; el backend aborta la generación activa si la hubiera y elimina la sesión de OpenCode correspondiente cuando sea posible.
3. Si una respuesta anterior llega después del reinicio, no aparece en el chat nuevo.
4. Cerrar el panel no elimina su historial; iniciar un chat nuevo sí lo hace.

### US-04 (P1) — Markdown legible y seguro

Como usuario quiero ver títulos, listas, énfasis, tablas, enlaces y bloques de código renderizados visualmente, no las marcas Markdown originales.

**Escenarios:**
1. Cuando la respuesta contiene `**negrita**`, listas, tablas o bloques de código, se renderizan apropiadamente.
2. Cuando contiene HTML malicioso o URLs peligrosas, el frontend no ejecuta scripts ni inserta HTML arbitrario.

### US-05 (P1) — Análisis PEAS real del requerimiento

Como analista quiero que el agente identifique información conocida, faltante, supuesta y ambigua, consulte las fuentes pertinentes y formule preguntas de negocio, para descubrir vacíos antes del grooming.

**Escenarios:**
1. Ante información incompleta, el agente explicita lo desconocido y no lo presenta como hecho.
2. Ante respuestas que resuelven vacíos, el análisis se actualiza.
3. Cuando no quedan vacíos relevantes, el agente informa que el análisis puede pasar al Redactor-Revisor, **sin redactar ni aprobar** una historia.

### US-06 (P2) — Diagnóstico y observabilidad

Como integrante del equipo quiero trazas correlacionadas en Langfuse y estados claros para diagnosticar fallos sin ver contraseñas ni registrar datos privados.

**Escenarios:**
1. Cada mensaje tiene identificador de correlación y duración.
2. Langfuse recoge los pasos de LangChain, consultas a herramientas y generación de OpenCode, si está configurado.
3. Sin credenciales Langfuse, el modo local sigue funcionando con aviso de observabilidad degradada.

## 4. Requerimientos funcionales

- **RF-001**: Botón flotante fijo en la esquina inferior derecha, visible en todas las rutas React.
- **RF-002**: Panel de chat con título "Agente Analista", estado de disponibilidad real, controles cerrar y nuevo chat; sin iconos de redes sociales.
- **RF-003**: Apertura/cierre independientes de reinicio de conversación.
- **RF-004**: Diseño responsive para escritorio, tableta y móvil; teclado usable y foco accesible.
- **RF-005**: Visualización de mensajes enviados y recibidos en orden; autodesplazamiento controlado y estado de procesamiento.
- **RF-006**: Rechazo de mensajes vacíos o compuestos solo por espacios; longitud máxima configurable, inicial 4.000 caracteres.
- **RF-007**: Una sola solicitud en vuelo por conversación; botón Enviar deshabilitado durante la ejecución; doble clic no crea duplicados.
- **RF-008**: Solicitudes realizadas **solo** al backend Python por una ruta relativa `/api/analista/...`; nunca desde navegador a OpenCode ni a Langfuse.
- **RF-009**: Servicio Python dedicado y encapsulado bajo `./agentes/analista/`.
- **RF-010**: API con endpoints para health, iniciar conversación, enviar mensaje y reiniciar/eliminar sesión.
- **RF-011**: El backend utiliza OpenCode Server local con autenticación Basic Auth leída del entorno, sin exponerla al navegador.
- **RF-012**: El backend gestiona sesión e identificadores opacos por conversación; el historial se conserva durante la vida de la sesión.
- **RF-013**: El agente utiliza LangChain de forma efectiva en su pipeline de prompts, ejecución y herramientas; no es una dependencia sin uso.
- **RF-014**: Las herramientas `consultar_glosario`, `buscar_hu_similares`, `consultar_estandares` y `aplicar_checklist_vacios` consultan datos simulados/anonimizados expuestos a través de MCP.
- **RF-015**: El agente identifica información conocida, faltante, supuesta y ambigua; genera preguntas por categoría y actualiza el análisis ante nuevos mensajes.
- **RF-016**: El agente no aprueba ni redacta una HU, no inventa datos ni convierte supuestos en hechos.
- **RF-017**: El agente no dispone de shell, edición/escritura/lectura libre de archivos, internet o herramientas OpenCode innecesarias; aplica allowlist de herramientas desde Python y restricciones del lado de OpenCode.
- **RF-018**: Prompt de sistema editable en `./agentes/analista/prompts/sistema.md`, cargado por Python al iniciar o en cada petición según la configuración, sin hardcodear su contenido.
- **RF-019**: Respuesta backend validada contra esquema tipado que conserva `respuesta_markdown`, cuatro clasificaciones, preguntas y fuentes utilizadas. Si falla validación, se presenta error controlado; jamás renderizar JSON crudo en pantalla como chat.
- **RF-020**: El frontend utiliza renderer Markdown compatible con GFM, sin habilitar HTML arbitrario.
- **RF-021**: Restablecer sesión está permitido durante una generación activa: invalida turno pendiente, solicita aborto a OpenCode y evita insertar respuestas tardías.
- **RF-022**: Timeouts configurables con error recuperable; el usuario puede iniciar un chat nuevo sin refrescar la página.
- **RF-023**: Identificadores de solicitud y de conversación vinculados a registros y observaciones Langfuse; no incluir secretos, datos personales sin anonimizar ni texto completo en logs ordinarios.
- **RF-024**: Mantener navegación, páginas, Stepper y datos mock existentes sin regresiones.
- **RF-025**: Instrucciones verificables de instalación, configuración y arranque de **frontend + API Python + OpenCode + MCP** para compañeros que usan OpenCode y para Codex.

## 5. Reglas PEAS

| Elemento | Definición del agente |
|---|---|
| **P — Performance** | Vacíos detectados antes de redactar, utilidad de las preguntas, tiempo reducido, menos cambios después de grooming, satisfacción del analista y cero datos inventados. |
| **E — Environment** | StoryCraft AI web, analistas y Product Owner, fuentes simuladas, servicio Python, servidor OpenCode local. |
| **A — Actuators** | Consultar herramientas MCP permitidas, clasificar datos, generar preguntas, actualizar análisis; **sin aprobar/redactar HU ni escribir sobre sistemas reales**. |
| **S — Sensors** | Texto del usuario y respuestas de Negocio, correcciones, resultados de herramientas y contexto de sesión. |

**Métricas académicas propuestas (a validar, no resultados medidos):** vacíos válidos detectados ≥80%; preguntas útiles ≥70%; tiempo de análisis −50%; cambios posteriores −50%; satisfacción ≥4/5; hechos inventados = 0. Validación sobre 3–5 requerimientos históricos anonimizados con línea base humana.

## 6. Categorías de preguntas

`Reglas de negocio`, `Datos requeridos`, `Validaciones`, `Excepciones`, `Comportamiento esperado`. Incluir permisos, estados, vigencias, cálculo de riesgo, comparativo y otros aspectos únicamente cuando correspondan al requerimiento.

## 7. Criterios no funcionales

- **RNF-01**: Stack frontend existente React + JavaScript + SCSS (sin TypeScript, Tailwind, Bootstrap ni Material UI).
- **RNF-02**: Backend FastAPI/Pydantic y cliente HTTP compatibles con el Python acordado por el equipo; `python >=3.11` propuesto, verificar versiones locales.
- **RNF-03**: Servicio accesible exclusivamente por loopback durante la demostración local; proxy de Vite o CORS restrictivo.
- **RNF-04**: Manejo accesible del foco, controles etiquetados, `aria-live` para nuevos mensajes y estados, buen contraste.
- **RNF-05**: No persistir automáticamente conversaciones sensibles en `localStorage`; el cierre minimiza sin borrar, la recarga puede pedir nueva sesión si el backend reinicia.
- **RNF-06**: No incluir secretos en control de versiones, bundle de Vite, respuestas de API ni enlaces.
- **RNF-07**: Pruebas automatizadas focalizadas del backend y controles críticos del frontend, más prueba manual end-to-end; **esta ampliación deliberadamente sustituye la prohibición de pruebas del prototipo original**.
- **RNF-08**: Solicitud estándar con límite de ejecución inicial configurable (ejemplo, 90 s), máximo de pasos de herramienta por turno y errores de timeout recuperables.
- **RNF-09**: Prohibido inventar tiempo de respuesta, consumo de tokens o disponibilidad de servicios.

## 8. Fuera de alcance

- Implementar Redactor-Revisor, Asesor Técnico o Gestor de Cambios.
- Automatizar generación/aprobación de HU en el Stepper existente.
- Conectar con Azure DevOps, iTop, correo, repositorios de código reales, internet o bases productivas.
- Chat multusuario, autenticación productiva, persistencia histórica permanente, subida de adjuntos, voz, streaming token a token, sistema multiagente.
- Cambios directos a `main` o merges automáticos.

## 9. Condiciones de aceptación / Definition of Done

1. Frontend abre/cierra el chat en todas las rutas y el estado se conserva al minimizar.
2. La comunicación real **React → FastAPI → Python/LangChain → OpenCode → FastAPI → React** funciona con el servidor local iniciado.
3. Cuatro herramientas MCP consultan fuentes simuladas y dejan evidencia auditable.
4. Las preguntas y clasificaciones responden a ejemplos conocidos; no se redacta una HU.
5. Markdown GFM visible, sin Markdown crudo ni ejecución de HTML no confiable.
6. Dos envíos simultáneos no son aceptados.
7. Reset durante respuesta lenta deja chat limpio y no admite respuesta tardía.
8. Apagar OpenCode produce error explícito sin bloquear el UI permanentemente.
9. Langfuse recibe trazas al estar configurado; no bloquea chat si falla su exportación.
10. `.env` ausente de commits; `.env.example` sin credenciales; comandos de instalación y pruebas documentados.
11. Build `npm run build`, pruebas nuevas y validación manual completadas.
12. PR de la rama de feature hacia `main` revisado por el equipo; **ningún merge automático**.

## 10. Preguntas resueltas para esta propuesta

- Se permite implementar API Python: **sí**; el alcance del prototipo anterior ya no cubre la nueva fase de curso.
- Ubicación del agente: `./agentes/analista`.
- Estado del chat al cerrar: **conservar**; al reiniciar: **descartar**.
- Comunicación con OpenCode: **desde Python exclusivamente**.
- Formato del agente: **JSON estructurado validado**; incluye campo de texto Markdown que la web renderiza.
- Memoria inicial: **de sesión**, sin base de datos; fuente de verdad backend/OpenCode por conversación.
- Integraciones externas: solo el servicio local de OpenCode y Langfuse para observabilidad; herramientas del dominio solo simuladas.
