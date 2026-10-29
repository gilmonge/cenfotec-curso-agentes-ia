# Feature Specification: Chat flotante con Agente Analista de Requerimientos

**Feature Branch**: `feat/chat-agente-analista`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "Crear el feature 'Chat flotante con Agente Analista de Requerimientos'
para StoryCraft AI. El repositorio tiene React 18, Vite 5, JS, SCSS, React Router; no sustituir
pantallas existentes ni simular respuestas en el chat. Añadir botón flotante abajo a la derecha
global, panel responsive con abrir/cerrar conservando historial, reiniciar/eliminar chat por
separado, envío y recepción reales contra API Python, un mensaje en vuelo por conversación,
indicador de procesamiento, error recuperable, Markdown GFM renderizado de modo seguro (sin HTML
crudo), y reinicio mientras OpenCode sigue procesando sin aceptar respuestas tardías. El agente
está estructurado en ./agentes/analista, con system prompt editable en prompts/sistema.md,
contexto de sesión, conexión a OpenCode local, LangChain, Langfuse y herramientas MCP simuladas.
Su función: analizar solicitud de Negocio, clasificar conocida/faltante/supuesta/ambigua,
consultar glosario, HU similares, estándares y checklist, generar preguntas, actualizar con
respuestas. Prohibido inventar datos, redactar o aprobar HU, usar sistemas reales, internet o
shell. El formato de salida debe incluir Markdown visible + estructura validada para análisis y
preguntas. Basarse también en el borrador specs/001-chat-flotante-analista/spec.md y el documento
Word de definición de agentes. Describir historias priorizadas, criterios de aceptación medibles,
errores y fuera de alcance. No implementar código."

## Clarifications

### Architectural decision — 2026-10-27

- OpenCode Server API v2 is the only authorized interface for AI generation. FastAPI reaches models only through OpenCode; it never connects to model providers directly.
- The project uses OpenCode Server as its only generation interface. The default provider is `opencode`; `OPENCODE_PROVIDER_ID` and `OPENCODE_MODEL_ID` can explicitly select another provider/model listed and enabled by OpenCode. An explicit pair authorizes a model even when its published cost is positive or unknown. No fixed model with exhausted quota is a permanent requirement. A 429 blocks live generation evidence only, not independent implementation or isolated automated tests.
- No paid model may be called and no budget may be consumed without explicit authorization. Unit tests may use mocks but must not be reported as real generation.

### Session 2026-10-26

- Q: ¿Qué diferencia debe existir entre «Nuevo chat» y «Eliminar conversación»? → A: Nuevo chat
  descarta el contexto y mantiene el panel abierto; Eliminar solicita confirmación, elimina el
  contexto en el servicio y cierra el panel.
- Q: ¿Debe existir un control explícito para cancelar la solicitud en curso sin borrar el
  historial? → A: Sí; Cancelar aborta la solicitud, marca el turno como cancelado y lo excluye del
  contexto del agente, conservando los mensajes y el contexto anteriores.
- Q: Al recargar la página, ¿debe recuperarse la conversación o empezar una nueva? → A: Empezar
  una nueva; no se guarda contenido ni identificadores en el navegador y el contexto vive solo
  mientras la pestaña y el servicio estén activos.
- Q: ¿El tiempo máximo de 90 s debe ser total por mensaje y, al vencer, abortar el procesamiento
  en el servidor? → A: Sí; es un límite total por mensaje, se solicita el aborto al vencer y se
  descarta cualquier resultado posterior.
- Q: ¿Qué métricas PEAS deben quedar como criterios de aceptación obligatorios en esta fase? → A:
  Vacíos detectados ≥80 %, preguntas útiles ≥70 %, tiempo de análisis −50 %, satisfacción ≥4/5 y
  0 datos inventados. La evaluación PEAS inicial usa 3–5 requerimientos; SC-005 conserva su muestra
  específica de 10 para poder declararse cumplido. La reducción de cambios post-grooming se aplaza.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chat disponible en toda la aplicación sin interrumpir el trabajo (Priority: P1)

Como analista de requerimientos quiero abrir un chat flotante desde cualquier pantalla y cerrarlo
sin perder la conversación, para consultar al Agente Analista sin abandonar el flujo en el que
estoy trabajando.

**Why this priority**: sin acceso global y persistente, la capacidad no puede usarse durante el
levantamiento real ni demostrarse sin romper la navegación existente.

**Independent Test**: recorrer todas las rutas, abrir y cerrar el panel en cada una, redimensionar
a móvil y verificar que el historial y el estado se conservan.

**Acceptance Scenarios**:

1. **Given** que el usuario está en cualquier ruta de la aplicación, **When** la aplicación termina
   de cargar, **Then** ve un botón de chat fijo en la esquina inferior derecha que no cubre
   controles primarios ni la navegación.
2. **Given** que el panel está cerrado y tiene mensajes, **When** el usuario lo abre, **Then** ve
   los mensajes previos en el mismo orden y con su estado.
3. **Given** que el panel está abierto, **When** el usuario lo cierra, **Then** el panel se oculta
   sin borrar el historial y sin cancelar una solicitud en curso.
4. **Given** una pantalla móvil de 360 px de ancho, **When** el usuario abre el panel, **Then** el
   panel es utilizable, no genera desplazamiento horizontal y la navegación sigue siendo accesible.
5. **Given** que el usuario navega con teclado, **When** abre el chat y luego lo cierra, **Then**
   el foco entra al panel y regresa al botón que lo abrió.
6. **Given** que el usuario está al final del historial, **When** aparece un mensaje nuevo, **Then**
   el panel lo desplaza hasta el final; **Given** que está más de 80 px por encima del final,
   **When** aparece un mensaje, **Then** conserva la posición para que pueda leer mensajes
   anteriores, muestra el control accesible «Ir al último mensaje» y solo desplaza al final si lo
   activa. El usuario puede recorrer los mensajes anteriores con el scroll del panel.

---

### User Story 2 - Consulta real al Agente Analista (Priority: P1)

Como analista quiero enviar una descripción, minuta o notas de Negocio y recibir el análisis real
del agente, con un solo envío en vuelo y errores recuperables, para analizar requerimientos sin
respuestas simuladas ni duplicados.

**Why this priority**: es el valor central de la funcionalidad; una respuesta simulada invalidaría
la demostración y la evaluación del agente.

**Independent Test**: con el servicio del agente disponible, enviar un requerimiento y comprobar
que la respuesta proviene de una ejecución real; cancelar una solicitud en curso; luego detener el
servicio y comprobar el error recuperable; finalmente intentar un doble envío.

**Acceptance Scenarios**:

1. **Given** que los servicios están disponibles, **When** el usuario envía un mensaje válido,
   **Then** la aplicación obtiene y muestra una respuesta del agente real, no un texto predefinido.
2. **Given** que hay una solicitud en curso, **When** el usuario intenta enviar otra, **Then** el
   control de envío está deshabilitado y no se crea un segundo turno.
3. **Given** que el usuario hace doble clic o pulsa Enter repetidamente, **When** la solicitud aún
   no terminó, **Then** se procesa una sola solicitud y se muestra una sola respuesta.
4. **Given** que el usuario envía un mensaje vacío o compuesto solo por espacios, **When** intenta
   enviarlo, **Then** la aplicación lo rechaza sin llamar al agente y explica el motivo.
5. **Given** que el mensaje supera el límite configurado, **When** el usuario intenta enviarlo,
   **Then** la aplicación lo rechaza con un mensaje claro y conserva el texto para editarlo.
6. **Given** que el servicio del agente no responde, **When** el usuario envía un mensaje, **Then**
   ve un error comprensible, el indicador de procesamiento se detiene y puede reintentar sin
   recargar la página.
7. **Given** que la solicitud supera el tiempo máximo configurado, **When** el tiempo se agota,
   **Then** la aplicación informa el timeout, solicita el aborto, descarta cualquier respuesta
   posterior, habilita reintentar o iniciar un chat nuevo y no deja el panel bloqueado.
8. **Given** una solicitud en curso, **When** el usuario elige **Cancelar**, **Then** la solicitud
   se aborta, el turno queda marcado como cancelado, los mensajes y el contexto anteriores se
   conservan y el usuario puede enviar un mensaje nuevo sin reiniciar el chat.
9. **Given** que el usuario cancela justo cuando llega la respuesta, **When** la cancelación se
   procesa, **Then** la respuesta se descarta y el turno no contamina el contexto siguiente.

---

### User Story 3 - Lectura segura y estructurada de la respuesta (Priority: P1)

Como analista quiero ver el texto en Markdown enriquecido y, además, la clasificación y las
preguntas en una estructura clara, sin riesgo de ejecutar HTML ni ver JSON crudo, para leer y
usar el análisis con confianza.

**Why this priority**: el contenido proviene de un modelo y de fuentes no confiables; renderizarlo
de forma insegura o mostrar JSON crudo impediría su uso profesional.

**Independent Test**: enviar respuestas de prueba con encabezados, listas, tablas, código, HTML
malicioso y enlaces peligrosos; comprobar el render y que no se ejecuta contenido activo.

**Acceptance Scenarios**:

1. **Given** una respuesta con encabezados, negritas, listas, tablas, enlaces y bloques de código,
   **When** se muestra en el chat, **Then** se renderiza como Markdown GFM legible.
2. **Given** una respuesta con HTML crudo, etiquetas de script, manejadores de eventos o enlaces
   peligrosos, **When** se muestra, **Then** no se ejecuta código, no se inserta HTML arbitrario y
   el contenido se neutraliza o se muestra como texto.
3. **Given** una respuesta válida, **When** se muestra, **Then** el usuario distingue las cuatro
   clasificaciones (conocida, faltante, supuesta y ambigua), las preguntas con su categoría y
   estado, las fuentes realmente consultadas y la indicación de si está listo para el redactor.
4. **Given** una clasificación sin elementos, **When** se muestra, **Then** se indica vacía o con
   cero, sin omitir la categoría.
5. **Given** una respuesta con estructura inválida o incompleta, **When** la aplicación la recibe,
   **Then** muestra un error controlado y nunca presenta JSON crudo ni contenido parcial como si
   fuera un análisis válido.
6. **Given** que el agente no consultó una fuente, **When** se muestra la respuesta, **Then** esa
   fuente no aparece como consultada.

---

### User Story 4 - Reinicio y eliminación sin respuestas tardías (Priority: P1)

Como analista quiero reiniciar o eliminar la conversación incluso mientras el agente sigue
procesando, para descartar un contexto y empezar limpio sin que aparezcan respuestas viejas.

**Why this priority**: una respuesta tardía después de un reinicio contaminaría el análisis nuevo
y haría inseguro el uso del chat.

**Independent Test**: provocar una respuesta lenta, reiniciar el chat y verificar que el estado
queda limpio, que la respuesta tardía no aparece y que se puede iniciar otra conversación.

**Acceptance Scenarios**:

1. **Given** una solicitud en proceso, **When** el usuario elige **Nuevo chat**, **Then** el
   historial visible se limpia de inmediato, el panel sigue abierto y se inicia una conversación
   vacía utilizable.
2. **Given** una conversación con historial, **When** el usuario elige **Eliminar conversación** y
   confirma, **Then** el historial se limpia, se elimina el contexto en el servicio y el panel se
   cierra; al reabrirlo se muestra el estado vacío.
3. **Given** que el reinicio ocurrió mientras el agente seguía procesando, **When** llega la
   respuesta anterior, **Then** se descarta y nunca se inserta en la conversación nueva.
4. **Given** un reinicio durante una solicitud lenta, **When** transcurren 5 segundos, **Then** el
   chat está limpio y acepta un mensaje nuevo sin recargar la página.
5. **Given** que el usuario cierra el panel sin reiniciar, **When** la solicitud termina, **Then**
   la respuesta se conserva y aparece al reabrir el panel.
6. **Given** que se pulsa **Eliminar conversación**, **When** el usuario no confirma, **Then** no
   se borra nada y la conversación continúa.
7. **Given** que el servicio perdió la sesión, **When** el usuario envía o recibe un error de sesión
   inexistente, **Then** ve un mensaje claro y puede iniciar un chat nuevo sin refrescar.
8. **Given** que el usuario recarga la página, **When** vuelve a abrir el chat, **Then** encuentra
   una conversación vacía, sin mensajes previos ni contexto recuperado.

---

### User Story 5 - Continuidad del análisis y actualización con respuestas (Priority: P1)

Como analista quiero dar seguimiento al mismo requerimiento y registrar las respuestas de Negocio,
para que el agente conserve el contexto y actualice los vacíos hasta dejar el análisis listo para
el redactor.

**Why this priority**: el agente pierde su valor si cada mensaje se analiza aislado y no incorpora
lo ya aclarado.

**Independent Test**: enviar un requerimiento incompleto, responder una de las preguntas y
comprobar que el análisis cambia y conserva el contexto del mismo requerimiento.

**Acceptance Scenarios**:

1. **Given** una conversación con un requerimiento analizado, **When** el usuario envía una
   pregunta de seguimiento, **Then** el agente responde usando el contexto de ese requerimiento.
2. **Given** una pregunta pendiente, **When** el usuario registra la respuesta de Negocio, **Then**
   el análisis se actualiza y el vacío correspondiente deja de figurar como faltante.
3. **Given** información confirmada por Negocio, **When** el agente actualiza el análisis, **Then**
   la ubica como conocida y no como supuesta.
4. **Given** una conversación reiniciada por Nuevo chat, Eliminar o recarga de la página, **When**
   el usuario envía un mensaje, **Then** el agente no usa el contexto de la conversación anterior.
5. **Given** que aún quedan vacíos relevantes, **When** el agente responde, **Then** indica que el
   análisis no está listo y mantiene las preguntas pendientes.
6. **Given** que ya no quedan vacíos relevantes, **When** el agente responde, **Then** indica que
   puede pasar al Redactor-Revisor, sin redactar ni aprobar la Historia de Usuario.

---

### User Story 6 - Rigor y límites del rol Analista (Priority: P1)

Como responsable del proceso quiero que el agente solo analice y pregunte, sin inventar datos ni
redactar o aprobar Historias de Usuario, para que el resultado sea confiable y respete la
separación de responsabilidades.

**Why this priority**: una invención o una HU redactada por el Analista rompería el control humano
y el alcance definido para el curso.

**Independent Test**: someter al agente a requerimientos incompletos, ejemplos de HU similares,
intentos de inyección de instrucciones y solicitudes de redacción o aprobación de HU.

**Acceptance Scenarios**:

1. **Given** un requerimiento incompleto, **When** el agente responde, **Then** declara los vacíos
   y no completa nombres, pólizas, coberturas, reglas, fechas, importes ni permisos.
2. **Given** una HU similar aprobada, **When** el agente la consulta, **Then** la usa como
   referencia y no la presenta como prueba de una regla aplicable al caso actual.
3. **Given** que el usuario pide redactar, aprobar o priorizar una HU, **When** el agente responde,
   **Then** explica la separación de responsabilidades, no redacta ni aprueba, y ofrece continuar
   con el análisis de vacíos.
4. **Given** un documento con instrucciones embebidas para cambiar el rol, **When** el agente lo
   procesa, **Then** ignora esas instrucciones y conserva su misión.
5. **Given** una consulta del agente, **When** intenta usar una herramienta no autorizada, **Then**
   la operación se rechaza y el agente continúa solo con las fuentes permitidas.
6. **Given** un posible dato personal no anonimizado, **When** el agente lo detecta, **Then**
   advierte que debe anonimizarse y evita repetirlo innecesariamente.
7. **Given** que el agente marca el análisis como listo para el redactor, **When** el usuario lo
   revisa, **Then** comprueba que no se generó ni aprobó una Historia de Usuario.

---

### User Story 7 - Diagnóstico y degradación controlada (Priority: P2)

Como integrante del equipo quiero disponer de estados y trazas correlacionadas, para diagnosticar
fallos sin exponer secretos ni datos personales y sin bloquear el chat cuando la observabilidad
falla.

**Why this priority**: mejora la operación y la demostración, pero el chat puede funcionar sin
ella; por eso es posterior a las historias que entregan el valor principal.

**Independent Test**: ejecutar un turno con observabilidad activa y verificar la traza; luego
desactivar la observabilidad y comprobar que el chat sigue funcionando con aviso de degradación.

**Acceptance Scenarios**:

1. **Given** una ejecución del agente, **When** el turno termina, **Then** existe una traza
   correlacionada con conversación, solicitud y turno, con duración real y herramientas usadas.
2. **Given** una traza registrada, **When** el equipo la revisa, **Then** no contiene secretos,
   credenciales, texto completo del usuario ni datos personales sin anonimizar.
3. **Given** que la observabilidad no está configurada o falla, **When** el usuario envía un
   mensaje, **Then** el chat responde igual y se muestra un aviso de observabilidad degradada.
4. **Given** que el usuario abre el chat, **When** consulta el estado, **Then** la aplicación
   muestra disponibilidad real y no indica "en línea" si el servicio no está operativo.
5. **Given** un error del agente, **When** el equipo lo investiga, **Then** encuentra el
   identificador de correlación sin recibir trazas internas ni credenciales en el navegador.

---

### Edge Cases

- Mensaje vacío, solo espacios, solo saltos de línea o con longitud exactamente en el límite.
- Mensaje que supera el límite en caracteres multibyte o con emojis; el límite debe ser estable.
- Doble clic, Enter repetido, cambio de pestaña y regreso durante una solicitud en curso.
- Dos pestañas abiertas: cada una mantiene su propia conversación y no comparten estado.
- Recarga de la página durante una solicitud o después de varios turnos: no debe reaparecer
  historial ni insertarse una respuesta generada antes de la recarga.
- Reinicio o eliminación en el instante exacto en que llega la respuesta (carrera).
- Cierre del panel durante una solicitud y reapertura después de que esta termina.
- Cancelación repetida o simultánea con la llegada de la respuesta.
- Reinicio repetido antes de que el servicio confirme el aborto.
- Corte de red, backend reiniciado o servicio del modelo detenido a mitad de un turno.
- Timeout mientras el modelo o una fuente siguen ejecutándose; aunque el aborto falle, la respuesta
  tardía no debe aceptarse.
- Respuesta del modelo truncada, con estructura incompleta o con tipos incorrectos.
- Respuesta extremadamente larga: debe poder leerse sin congelar la interfaz.
- Markdown con HTML anidado, `javascript:`, `data:`, imágenes remotas, eventos o codificación
  ofuscada.
- Sesión expirada o inexistente después de un reinicio del backend.
- Fallo o timeout de una fuente simulada; el agente no debe rellenar el vacío con invención.
- Fallo de autenticación o configuración del servicio del modelo.
- Fallo de exportación de observabilidad durante un turno exitoso.
- Usuario que intenta inyectar instrucciones en el requerimiento o en una fuente consultada.
- Límite de herramientas por turno alcanzado antes de completar el análisis.
- Panel abierto en móvil con teclado virtual visible; el campo y el botón deben seguir accesibles.
- Respuesta tardía de una conversación eliminada; debe descartarse por identidad, no por tiempo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La aplicación DEBE mostrar un botón de chat fijo en la esquina inferior derecha en
  todas las rutas existentes, sin cubrir controles primarios ni la navegación.
- **FR-002**: El usuario DEBE poder abrir y cerrar el panel sin cambiar de ruta ni recargar la
  página.
- **FR-003**: Cerrar el panel DEBE conservar los mensajes y su orden, y NO DEBE cancelar una
  solicitud en curso.
- **FR-004**: **Nuevo chat** DEBE limpiar el historial visible, iniciar una conversación vacía y
  mantener el panel abierto.
- **FR-005**: **Eliminar conversación** DEBE solicitar confirmación, limpiar el historial, eliminar
  el contexto en el servicio y cerrar el panel; al reabrirlo DEBE mostrar el estado vacío.
- **FR-006**: Cerrar, iniciar un chat nuevo y eliminar la conversación DEBEN ser acciones distintas:
  cerrar conserva el historial y mantiene el contexto; Nuevo chat descarta el contexto y mantiene
  el panel abierto; Eliminar confirma, descarta el contexto y cierra el panel.
- **FR-007**: El panel DEBE adaptarse a escritorio, tableta y móvil, sin desbordamiento horizontal
  y sin bloquear permanentemente la navegación ni el campo de escritura.
- **FR-008**: El chat DEBE ser operable con teclado y lector de pantalla, con etiquetas accesibles,
  foco gestionado, cierre por teclado, anuncio de mensajes nuevos y estados, y contraste suficiente.
- **FR-009**: Cada envío DEBE consultar al servicio real del agente. La aplicación NO DEBE mostrar
  respuestas simuladas, predefinidas ni generadas localmente para aparentar una ejecución.
- **FR-010**: La aplicación DEBE rechazar mensajes vacíos o compuestos solo por espacios y DEBE
  aplicar un límite máximo configurable, inicial de 4.000 caracteres, con mensaje claro.
- **FR-011**: Cada conversación DEBE permitir una sola solicitud en vuelo; el envío DEBE
  deshabilitarse mientras se procesa, los intentos duplicados NO DEBEN crear turnos adicionales y
  DEBE existir un control **Cancelar** disponible solo durante el procesamiento.
- **FR-012**: La aplicación DEBE mostrar un indicador de procesamiento dentro de los primeros 2
  segundos y mantenerlo hasta que la solicitud termine, falle, se cancele o se reinicie.
- **FR-013**: El desplazamiento automático DEBE seguir la intención de lectura: si el scroll está a
  80 píxeles CSS o menos del final antes de añadir un mensaje, la interfaz DEBE seguir el nuevo
  mensaje hasta el final; si está más arriba, DEBE conservar la posición, mostrar un control
  accesible «Ir al último mensaje» y permitir recorrer mensajes anteriores sin saltos. El control
  DEBE llevar al final al activarse y desaparecer cuando el usuario llegue allí. La escritura,
  cambios de health y otras actualizaciones que no añadan mensajes NO DEBEN mover el scroll.
- **FR-014**: Cada respuesta DEBE mostrar el Markdown visible, las cuatro clasificaciones, las
  preguntas, las fuentes realmente consultadas y la indicación de readiness.
- **FR-015**: La respuesta DEBE incluir una estructura validada con texto visible, listas de
  conocida/faltante/supuesta/ambigua, preguntas con categoría y estado, fuentes, readiness,
  identificadores de conversación, solicitud y turno, y duración real.
- **FR-016**: La aplicación DEBE validar la estructura antes de mostrarla; si es inválida, DEBE
  presentar un error controlado y NO DEBE renderizar JSON crudo ni contenido parcial como válido.
- **FR-017**: El Markdown DEBE renderizarse con soporte GFM, sin HTML crudo, sin scripts, sin
  manejadores de eventos y con enlaces peligrosos neutralizados.
- **FR-018**: Las preguntas SOLO DEBEN usar las categorías Reglas de negocio, Datos requeridos,
  Validaciones, Excepciones y Comportamiento esperado, y los estados pendiente o respondida.
- **FR-019**: El agente DEBE conservar el contexto del mismo requerimiento durante la sesión hasta
  que el usuario reinicie o elimine la conversación, la pestaña recargue y pierda su identidad, o
  el registro volátil expire; una pestaña recargada no puede recuperar ni consultar el contexto
  anterior.
- **FR-020**: Al recibir respuestas de Negocio, el agente DEBE actualizar la clasificación: lo
  confirmado pasa a conocida, lo resuelto deja de ser faltante y lo no resuelto permanece visible.
- **FR-021**: El agente SOLO DEBE consultar las cuatro fuentes permitidas y de solo lectura:
  glosario, HU similares, estándares y checklist de vacíos.
- **FR-022**: Las fuentes reportadas DEBEN corresponder a consultas realmente ejecutadas; el
  agente NO DEBE declarar una fuente que no consultó.
- **FR-023**: El agente NO DEBE inventar datos ni presentar supuestos como hechos confirmados; ante
  información ausente DEBE declarar el vacío y, si aplica, etiquetar el supuesto como tal.
- **FR-024**: El agente NO DEBE redactar, aprobar, priorizar ni generar Historias de Usuario o
  criterios de aceptación; solo puede indicar que el análisis está listo para el Redactor-Revisor.
- **FR-025**: El agente DEBE tratar el texto del usuario y el contenido de las fuentes como datos no
  confiables, ignorar instrucciones embebidas y preservar su misión y sus límites.
- **FR-026**: El system prompt DEBE ser editable en un archivo externo, cargarse en tiempo de
  ejecución y registrar versión o hash; su contenido NO DEBE estar hardcodeado.
- **FR-027**: El agente NO DEBE tener shell, lectura o escritura libre de archivos, internet,
  correo, repositorios, bases de datos ni acceso a sistemas reales; la allowlist DEBE aplicarse
  fuera del prompt.
- **FR-028**: Ningún secreto, credencial o token DEBE aparecer en el navegador, el bundle, las URLs,
  el almacenamiento del navegador, los logs o las respuestas; el navegador NO DEBE contactar
  directamente al motor del modelo ni a la observabilidad.
- **FR-029**: La conversación NO DEBE persistirse automáticamente en el almacenamiento del navegador;
  cerrar el panel DEBE minimizar sin borrar y recargar la página DEBE iniciar una sesión nueva sin
  recuperar mensajes ni contexto anteriores. El backend conserva el registro huérfano únicamente
  en memoria hasta eliminación explícita, TTL de 30 minutos desde la última actividad, expulsión
  por capacidad o apagado/reinicio del proceso; la pestaña nueva no recibe su ID. Una petición de
  cancelación al recargar es de mejor esfuerzo y no sustituye el TTL. No se permite `localStorage`,
  `sessionStorage`, IndexedDB, cookies ni otra persistencia de conversación en el navegador.
- **FR-030**: La aplicación DEBE mostrar disponibilidad real del servicio (lista, degradada o no
  disponible) y NO DEBE indicar "en línea" sin comprobación.
- **FR-031**: Los errores DEBEN ser comprensibles y recuperables, con opción de reintentar o iniciar
  un chat nuevo, sin stack traces, identificadores internos ni secretos.
- **FR-032**: El tiempo máximo DEBE ser un límite total por mensaje, configurable, con 90 segundos
  como valor inicial. Al agotarse, la aplicación DEBE informar el timeout, solicitar el aborto del
  procesamiento en el servidor, descartar cualquier resultado posterior y permitir reintentar.
- **FR-033**: Reiniciar o eliminar DEBE funcionar aunque haya una solicitud en curso; el estado
  DEBE invalidarse antes de abortar y las respuestas tardías DEBEN descartarse por identidad.
- **FR-034**: Si la sesión expira o no existe, la aplicación DEBE informarlo y ofrecer un chat nuevo
  sin reutilizar contexto anterior.
- **FR-035**: Cada turno DEBE poder correlacionarse por conversación, solicitud y turno, con
  duración, herramientas y errores; las trazas NO DEBEN contener secretos, texto completo del
  usuario ni datos personales sin anonimizar.
- **FR-036**: Un fallo de observabilidad NO DEBE impedir la respuesta del chat; solo DEBE degradar
  el diagnóstico y mostrar un aviso.
- **FR-037**: Las rutas, pantallas, navegación, Stepper, Accordion, datos mock, estilos y
  simulaciones existentes DEBEN conservarse; la funcionalidad DEBE ser aditiva.
- **FR-038**: El servicio DEBE ser accesible solo de forma local por defecto, sin exposición pública
  ni CORS abierto.
- **FR-039**: Ante un posible dato personal, el agente DEBE advertir la necesidad de anonimizarlo y
  evitar repetirlo innecesariamente.
- **FR-040**: Si una fuente falla o el límite de herramientas se alcanza, el agente DEBE declarar la
  limitación y continuar solo con información disponible, sin inventar ni ocultar el vacío.
- **FR-041**: Duraciones, tokens o fuentes SOLO DEBEN mostrarse cuando fueron medidos o realmente
  consultados; la aplicación NO DEBE inventar métricas de ejecución.
- **FR-042**: **Cancelar** DEBE abortar la solicitud en curso, marcar el turno como cancelado,
  conservar los mensajes y el contexto anteriores y excluir el turno cancelado del contexto del
  agente; NO DEBE borrar la conversación ni iniciar una sesión nueva.
- **FR-043**: Una respuesta que llegue después de una cancelación DEBE descartarse por identidad de
  conversación y turno, aunque el servicio la haya terminado de generar.
- **FR-044 (PEAS — Performance)**: El agente DEBE detectar vacíos, generar preguntas útiles y
  reducir el tiempo de análisis frente a una línea base manual de 3 a 5 requerimientos
  anonimizados, manteniendo en cero los datos inventados.
- **FR-045 (PEAS — Environment)**: El agente DEBE operar en la etapa de análisis de la aplicación
  web, con fuentes simuladas o anonimizadas y el motor local, sin acceder a sistemas reales.
- **FR-046 (PEAS — Actuators)**: El agente SOLO DEBE clasificar información, consultar las cuatro
  fuentes permitidas, generar preguntas y actualizar el análisis; NO DEBE redactar ni aprobar HU.
- **FR-047 (PEAS — Sensors)**: El agente DEBE usar el texto del usuario, las respuestas de Negocio,
  las correcciones del analista, los resultados de herramientas y la memoria de la sesión.

**FR-048**: Ante `OPENCODE_RATE_LIMITED`, si OpenCode informa una fecha o duracion futura valida, la aplicacion DEBE mostrar y actualizar el tiempo restante sin enviar solicitudes automaticas. El usuario DEBE poder reintentar manualmente el mismo mensaje sin duplicarlo. Si no hay un tiempo valido, debe indicar que OpenCode no informo cuando se restablecera la cuota.

### Error and Recovery Behavior

- **ERR-001 — Servicio del agente o modelo no disponible**: el usuario ve un mensaje de
  indisponibilidad, el indicador se detiene, no se muestra una respuesta falsa y puede reintentar.
- **ERR-002 — Tiempo máximo agotado**: se informa el timeout, se solicita el aborto en el servidor,
  se descarta cualquier respuesta posterior, se habilita reintentar o iniciar un chat nuevo y no
  queda un spinner indefinido.
- **ERR-003 — Salida inválida o incompleta**: se muestra un error controlado, se registra el fallo
  para diagnóstico y nunca se renderiza JSON crudo ni contenido parcial como análisis válido.
- **ERR-004 — Solicitud ya en curso**: se informa que hay un turno en proceso y no se duplica el
  envío ni la respuesta.
- **ERR-005 — Sesión expirada o inexistente**: se explica que la sesión terminó y se ofrece iniciar
  un chat nuevo; no se reutiliza contexto previo.
- **ERR-006 — Reinicio durante el procesamiento**: el estado se limpia de inmediato, se solicita el
  aborto y cualquier respuesta posterior se descarta sin mostrarse.
- **ERR-007 — Fuente simulada no disponible**: el agente declara la limitación, continúa con las
  fuentes disponibles o se detiene; no completa el vacío con invención.
- **ERR-008 — Fallo de autenticación o configuración**: se muestra un mensaje accionable sin
  revelar credenciales, rutas internas ni detalles de infraestructura.
- **ERR-009 — Observabilidad no disponible**: el chat sigue operando y se muestra un aviso de
  diagnóstico degradado; el fallo no se presenta como error del análisis.
- **ERR-010 — Corte de red o respuesta incierta**: se informa el fallo y el reintento reutiliza la
  identidad de la solicitud para no duplicar el turno.
- **ERR-011 — Contenido malicioso en la respuesta**: se neutraliza sin ejecutar código ni insertar
  HTML, y se preserva la legibilidad del resto del mensaje.
- **ERR-012 — Respuesta tardía de una conversación eliminada**: se descarta por identidad de
  conversación y turno, aunque el contenido llegue después de un reinicio exitoso.
- **ERR-013 — Cancelación por el usuario**: se aborta la solicitud, el control de envío vuelve a
  estar disponible, el turno queda como cancelado y no se inserta una respuesta posterior.

**ERR-014 - Cuota del proveedor agotada**: informar `OPENCODE_RATE_LIMITED`; si OpenCode devuelve una fecha o duracion de recuperacion valida, mostrar un contador que termina sin reintentar automaticamente. Si falta el dato, indicarlo explicitamente. El reintento manual conserva el mensaje y la conversacion existente.



### Key Entities *(include if feature involves data)*

- **Conversación**: registro efímero de análisis con identidad opaca, estado de servidor (`activa`,
  `procesando`, `reemplazada`, `eliminada` o `expirada`), contexto del requerimiento y actividad
  reciente. Abrir/cerrar el panel es estado de UI y no cambia el estado del servidor. No expone el
  identificador interno del motor del modelo.
- **Turno o mensaje**: unidad de intercambio con autor, texto, marca temporal, estado (enviado,
  procesando, completado, fallido, cancelado, expirado, descartado), identificador de solicitud y
  duración.
- **Análisis**: conjunto de cuatro listas —conocida, faltante, supuesta y ambigua— más la indicación
  de readiness para el Redactor-Revisor.
- **Pregunta de aclaración**: consulta para Negocio con categoría permitida, texto y estado
  pendiente o respondida.
- **Consulta a fuente**: registro de una fuente permitida realmente consultada y su resultado,
  siempre de solo lectura.
- **Respuesta del agente**: texto Markdown visible más análisis, preguntas, fuentes, readiness,
  identificadores y duración real.
- **Estado del servicio**: disponibilidad general y por dependencia (lista, degradada, no
  disponible), sin revelar detalles sensibles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las rutas existentes muestra el botón de chat en menos de 1 segundo tras
  cargar, y el panel abre en menos de 0,5 segundos.
- **SC-002**: Un analista puede abrir el chat, escribir y enviar su primera consulta en un máximo de
  3 interacciones.
- **SC-003**: El 95 % de las solicitudes válidas muestra el indicador de procesamiento en menos de
  2 segundos y termina en éxito o error explícito dentro de los 90 segundos configurados; el 0 %
  queda con un indicador indefinido.
- **SC-004**: El 100 % de las respuestas del chat proviene de una ejecución real del agente; se
  observan 0 respuestas simuladas o predefinidas.
- **SC-005**: Sobre un conjunto de 10 requerimientos históricos anonimizados con vacíos conocidos,
  el agente detecta al menos el 80 % de los vacíos que el analista confirma como válidos y presenta
  0 datos inventados como hechos confirmados.
- **SC-006**: Al menos el 70 % de las preguntas generadas en la evaluación es considerado útil y es
  llevado a Negocio por el analista.
- **SC-007**: En 20 ensayos de reinicio durante una respuesta lenta, el 100 % deja el chat limpio en
  menos de 5 segundos, permite iniciar otra conversación y muestra 0 respuestas tardías.
- **SC-008**: En 20 ensayos de doble envío rápido, el 100 % genera una sola solicitud y una sola
  respuesta, sin turnos duplicados.
- **SC-009**: El 100 % de las respuestas válidas muestra las cuatro clasificaciones, las preguntas y
  la readiness; el 0 % muestra JSON crudo en el chat.
- **SC-010**: Con al menos 10 cargas maliciosas de Markdown o HTML, se observan 0 ejecuciones de
  script, 0 inserciones de HTML arbitrario y 0 navegaciones a enlaces peligrosos.
- **SC-011**: El 100 % de los fallos inducidos (servicio caído, timeout, salida inválida, sesión
  expirada, conflicto y error de fuente) muestra un mensaje recuperable y permite reintentar sin
  recargar la página; tras restablecer el servicio, el 100 % de los reintentos funciona.
- **SC-012**: El 100 % de los turnos con observabilidad activa produce una traza correlacionada con
  duración y herramientas; 0 trazas contienen secretos o datos personales sin anonimizar; con la
  observabilidad caída, el 100 % de los chats sigue funcionando.
- **SC-013**: El 100 % de las rutas, pantallas, flujos del Stepper, datos mock y estilos existentes
  supera la regresión manual y el build; 0 pantallas existentes se sustituyen.
- **SC-014**: El 100 % de las consultas declara solo fuentes realmente consultadas; 0 fuentes se
  reportan sin ejecución.
- **SC-015**: El 0 % de las conversaciones se guarda automáticamente en el almacenamiento del
  navegador, y 0 secretos aparecen en bundle, URLs, logs o respuestas.
- **SC-016**: Al menos el 90 % de 5 usuarios de prueba completa el flujo principal sin ayuda y
  otorga una satisfacción media de al menos 4 sobre 5.
- **SC-017**: El 100 % de los mensajes generados respeta los límites del rol: 0 Historias de Usuario
  redactadas o aprobadas y 0 supuestos presentados como hechos.
- **SC-018**: En 20 ensayos de cancelación durante una respuesta lenta, el 100 % detiene el
  procesamiento en menos de 2 segundos, conserva el historial y el contexto anteriores, deja el
  turno como cancelado y muestra 0 respuestas posteriores de ese turno.
- **SC-019**: En 20 recargas de página, el 100 % inicia el chat vacío, muestra 0 mensajes previos,
  recupera 0 contexto y deja 0 contenido de conversación en el almacenamiento del navegador.
- **SC-020**: En 20 ensayos de timeout, el 100 % libera la conversación en menos de 2 segundos tras
  el vencimiento, permite reintentar y muestra 0 respuestas tardías de la solicitud expirada.
- **SC-021**: Sobre 3 a 5 requerimientos históricos anonimizados, el tiempo de análisis asistido es
  al menos un 50 % menor que la línea base manual medida en las mismas condiciones.

**Nota de medición**: las metas de SC-005, SC-006, SC-016 y SC-021 provienen de la definición del
agente y son objetivos propuestos, no resultados medidos. La evaluación PEAS inicial usa 3 a 5
requerimientos históricos anonimizados, pero SC-005 requiere 10 casos para cumplir su criterio
específico; con una muestra menor se reporta `PARTIAL`, nunca como aceptación. La reducción de
cambios después del grooming se difiere a una evaluación longitudinal con sprints reales.

## Out of Scope

- Implementar el Agente Redactor-Revisor, el Agente Asesor Técnico o el Agente Gestor de Cambios.
- Redactar, aprobar, priorizar o generar Historias de Usuario y criterios de aceptación desde el
  chat, o automatizar su generación en el Stepper existente.
- Integrarse con Azure DevOps, iTop, bases de datos, correo, repositorios de código reales,
  internet o sistemas productivos.
- Implementar un repositorio de HU de largo plazo; solo se consume como fuente simulada de lectura.
- Autenticación productiva, multiusuario, roles, auditoría o administración de usuarios.
- Persistencia permanente de conversaciones o historial entre recargas y reinicios del servicio.
- Subida de archivos, adjuntos, OCR, voz, streaming token a token o sistema multiagente.
- Selector de tipo de información dentro del chat; la entrada es texto libre.
- Aplicación móvil nativa, despliegue productivo o paneles de analítica de uso.
- Sustituir o rediseñar las pantallas, rutas, estilos, datos mock o simulaciones existentes.
- Medir la reducción de cambios después del grooming en esta fase; requiere sprints reales y se
  difiere a una evaluación longitudinal.
- Escritura directa en `main`, merges automáticos o cambios de alcance sin Spec Kit.

## Assumptions

- El usuario principal es un analista de requerimientos o Product Owner de Popular Seguros, y la
  interfaz se usa en español durante una demostración local.
- Solo el Agente Analista de Requerimientos se implementa en esta fase; los otros tres agentes de
  la definición quedan fuera de alcance.
- La plataforma local fijada por la constitución —motor del modelo mediante OpenCode, orquestación
  con LangChain, fuentes simuladas expuestas por MCP y observabilidad con Langfuse— está disponible
  y no se rediseña en esta especificación.
- Las fuentes de conocimiento son simuladas o anonimizadas; no se usarán datos reales de asegurados,
  pólizas ni siniestros.
- El servicio mantiene el estado de las conversaciones en memoria, en una sola instancia; un
  reinicio del backend invalida las sesiones y el usuario debe iniciar un chat nuevo.
- El límite de mensaje es de 4.000 caracteres y el timeout es total por mensaje, con 90 segundos
  iniciales y configurable; al vencer se aborta el trabajo y se descarta el resultado. El número
  máximo de herramientas por turno también es configurable.
- **Nuevo chat** descarta el contexto de inmediato y mantiene el panel abierto; **Eliminar
  conversación** agrega confirmación, elimina el contexto en el servicio y cierra el panel. Ambos
  son distintos de cerrar el panel, que conserva el contexto.
- Cerrar el panel no cancela la solicitud en curso; **Cancelar** aborta solo el turno activo y
  conserva el contexto anterior, mientras que reiniciar o eliminar invalidan toda la conversación.
- La conversación conserva contexto durante la sesión, pero no se persiste en el navegador ni se
  recupera después de recargar la página.
- Dos pestañas del navegador representan conversaciones independientes y no se sincronizan.
- La aplicación existente mantiene su stack y su identidad visual; esta funcionalidad es aditiva y
  no introduce un framework de interfaz nuevo.
- Las cinco métricas PEAS (vacíos ≥80 %, preguntas útiles ≥70 %, tiempo de análisis −50 %,
  satisfacción ≥4/5 y 0 datos inventados) son objetivos iniciales bloqueantes. La evaluación inicial
  usa 3–5 requerimientos históricos anonimizados; SC-005 exige N=10 para cumplimiento. La reducción
  de cambios después del grooming se difiere a una evaluación longitudinal.
- Se revisaron el borrador `specs/001-chat-flotante-analista/spec.md`, la definición de agentes
  actualizada al 22 de octubre de 2026 y los requerimientos originales del prototipo. Donde el
  material difiere, prevalece la definición del Analista: no redacta ni aprueba HU.
