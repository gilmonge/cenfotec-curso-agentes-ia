// Contenido de la página de Ayuda (texto fijo). Cada bloque es una lista de { titulo, texto, puntos? }.

export const PASOS_ASISTENTE = [
  {
    titulo: 'Paso 1 — Requerimiento',
    texto: 'Ingrese la minuta, el correo o el incidente que llegó de Negocio, con su título, tipo de información, sistema, código de HU y área solicitante. Si todavía no lo va a analizar, use «Guardar y continuar después»: queda como borrador en la lista de historias.',
  },
  {
    titulo: 'Paso 2 — Análisis del Analista y del Asesor Técnico',
    texto: 'El Agente Analista decide qué consultar (glosario, HU similares, estándares y checklist de vacíos) y clasifica la información en conocida, faltante, supuesta y ambigua. Lo que solo se sabe revisando el sistema (por ejemplo, en qué otros lugares aparece un dato) no se le pregunta a Negocio: se lo pasa al Asesor Técnico, que revisa el código enseguida. Puede tardar unos minutos.',
  },
  {
    titulo: 'Paso 3 — Preguntas para Negocio',
    texto: 'El Analista y el Asesor Técnico trabajan en equipo y arman una sola ronda: arriba se muestra qué otras funciones afecta el cambio (por ejemplo, una carga masiva o un reporte), sin detalle técnico, y abajo un solo formulario con las preguntas del Analista y las decisiones del Asesor. Usted las lleva a Negocio, registra las respuestas y las envía.',
    puntos: [
      'Si quedan vacíos, el Analista hace otra ronda. Una pregunta ya respondida no se vuelve a hacer.',
      'Si un punto se parece a algo que Negocio ya respondió, no se repregunta: pasa como supuesto que el Product Owner valida al aprobar.',
      'Lo que el Asesor no pudo confirmar en el código no se le pregunta a Negocio: queda como pendiente técnico para Desarrollo.',
      'Puede guardar respuestas sin enviarlas (por ejemplo, si debe consultarlas) y terminarlas otro día.',
    ],
  },
  {
    titulo: 'Paso 4 — Historia y criterios (borrador)',
    texto: 'El Agente Redactor-Revisor escribe la historia en formato Como / Quiero / Para, con criterios Dado que / Cuando / Entonces que cubren también cada impacto en otros módulos y las decisiones tomadas, y la revisa hasta en dos rondas. El borrador se puede editar.',
  },
  {
    titulo: 'Paso 5 — Aprobación del Product Owner',
    texto: 'El Product Owner revisa la historia, el impacto en otros módulos, las decisiones tomadas y los supuestos a validar, y confirma que los datos están anonimizados. Puede aprobarla, devolverla a un agente con un motivo o rechazarla. Al aprobar, la HU se guarda en el Repositorio de HU y se recarga en el conocimiento que consultan los agentes.',
  },
];

export const NAVEGACION_ASISTENTE = [
  'El avance se guarda cada vez que el flujo espera una respuesta: puede salir y retomarlo otro día desde Historias de Usuario → En proceso, aunque el servicio se haya reiniciado.',
  'Si un paso falla (por ejemplo, un agente no responde), el avance anterior queda guardado y aparece «Reintentar el paso que falló».',
  'Use Atrás para volver a ver un paso anterior sin perder lo escrito.',
  'Mientras los agentes trabajan se muestra una pantalla de espera; puede tardar varios minutos.',
];

export const ACCIONES_HISTORIA = [
  {
    titulo: 'Retomar o descartar (HU en proceso)',
    texto: 'Las HU que todavía no terminan aparecen arriba del listado, en «En proceso», con lo que están esperando y quién las inició. Retomar abre el paso donde quedó, con lo que ya se respondió; Descartar borra el avance guardado.',
  },
  {
    titulo: 'Ver detalle',
    texto: 'Es solo de consulta: arriba ofrece únicamente Volver. Muestra la historia en pestañas (Historia, Criterios de aceptación, Preguntas pendientes, Observaciones, Historial, Análisis y Datos de la plantilla); cada pestaña aparece solo si la HU tiene ese dato. En Observaciones, las dependencias y los pendientes técnicos se pueden marcar como atendidos. Si hay preguntas pendientes o el análisis quedó desactualizado, avisa y ofrece responderlas o volver a analizar.',
  },
  {
    titulo: 'Editar',
    texto: 'Abre el formulario por secciones.',
    puntos: [
      'Antes de aprobar se puede cambiar todo. Si cambian el requerimiento o las respuestas, queda marcado que hay que volver a analizar; cambiar solo los criterios no lo exige.',
      'Con la HU aprobada sirve para corregir redacción o datos mal escritos: se guarda en el lugar, sigue aprobada, no sube la revisión ni pasa por el agente, y queda registrado quién editó, cuándo y qué campos.',
      'Antes de guardar una HU aprobada se actualiza el Repositorio; si lo rechaza (por ejemplo, por datos personales), no se guarda nada.',
      'Las observaciones son una bitácora: una entrada por idea, con fecha, tipo (decisión, dependencia, pendiente técnico, supuesto, devolución del PO o nota) y origen. No se editan ni se borran; para corregir se agrega una nota nueva.',
    ],
  },
  {
    titulo: 'Solicitar cambio (solo HU aprobada)',
    texto: 'Se usa cuando Negocio cambia el alcance. Siempre lleva a un nuevo análisis.',
    puntos: [
      'Se describe lo que pide Negocio. Si fue un vacío del análisis, se escribe la pregunta que debió hacerse y queda como lección propuesta para que el Product Owner la apruebe; si Negocio solo cambió de decisión, se marca la casilla y no hay lección.',
      'Al pulsar "Registrar y analizar cambio" se abre el asistente sobre la misma HU, con el mismo código y el cambio ya cargado.',
      'Al aprobar, sube a la siguiente revisión y la anterior queda en el Historial.',
    ],
  },
  {
    titulo: 'Descargar',
    texto: 'Genera la HU en Word o PDF con la plantilla de documento (código de formato, encabezado, pie con número de página). Las observaciones salen en una página final como tabla (Fecha, Tipo, Origen, Comentario, Estado).',
  },
  {
    titulo: 'Eliminar',
    texto: 'Solo está en el listado y pide confirmación. Si la HU ya estaba aprobada, primero se borra del Repositorio para que el agente deje de usarla; si eso falla, no se borra y se informa el motivo. Después se borra de la base y del navegador.',
  },
];

// Lo que comparten los cuatro agentes: las cuatro propiedades de un agente.
export const PROPIEDAD_AGENTE = [
  { titulo: 'Autonomía', texto: 'Cada agente decide qué consultar y con qué consulta. Primero arma un plan; el sistema lo valida y lo ejecuta.' },
  { titulo: 'Razonamiento', texto: 'Explica por qué consulta cada fuente y trabaja en ciclos de percibir, pensar y actuar. Su plan se puede ver en «Cómo trabajó el agente».' },
  { titulo: 'Herramientas (MCP)', texto: 'Cada agente tiene su propio servidor MCP con herramientas de solo lectura. Solo ve las herramientas de su rol; si pide otra, se descarta y queda registrado.' },
  { titulo: 'Memoria (RAG)', texto: 'Detrás de las herramientas está la base de conocimiento en Pinecone: glosario, estándares, checklist, HU aprobadas, lecciones aprendidas y el código del sistema.' },
];

export const AGENTES = [
  {
    nombre: 'Agente Analista',
    rol: 'Descubre y aclara los vacíos de un requerimiento antes de redactar la HU y de llegar al grooming. Se detiene a esperar las respuestas de Negocio.',
    hace: [
      'Clasifica la información en conocida, faltante, supuesta y ambigua.',
      'Genera preguntas por categoría, con palabras de negocio, y reanaliza cuando llegan las respuestas.',
      'Advierte si detecta datos personales sin anonimizar.',
    ],
    fuentes: 'Glosario de seguros, HU similares aprobadas, estándares de desarrollo y checklist de vacíos.',
  },
  {
    nombre: 'Asesor Técnico',
    rol: 'Trabaja en equipo con el Analista: encuentra todos los lugares del sistema que afecta un cambio, incluso los que el requerimiento no menciona, y suma sus decisiones a la ronda de preguntas para Negocio.',
    hace: [
      'Busca cada campo o regla en el código del sistema (y sus variantes, como el nombre de una columna en una carga) y abre los archivos donde aparece.',
      'Explica a Negocio, sin detalle técnico, qué otras funciones cambian y qué reglas debe decidir; lo que no pudo confirmar en el código queda como pendiente técnico.',
      'Guarda para Desarrollo la evidencia técnica (archivos y riesgos), que no se muestra en pantalla.',
    ],
    fuentes: 'Repositorio de código de solo lectura (de ejemplo: codigo-ejemplo-polizas), estándares y HU similares.',
  },
  {
    nombre: 'Redactor-Revisor',
    rol: 'Redacta la historia con lo que ya se aclaró y la revisa antes de que llegue al Product Owner.',
    hace: [
      'Escribe Como / Quiero / Para y criterios Dado que / Cuando / Entonces verificables.',
      'Cubre con criterios cada impacto en otros módulos y aplica las decisiones tomadas.',
      'Revisa su propio borrador hasta en dos rondas; nunca aprueba.',
    ],
    fuentes: 'Estándares de redacción, checklist de calidad y HU similares.',
  },
  {
    nombre: 'Gestor de Cambios',
    rol: 'Atiende las solicitudes de cambio sobre una HU ya aprobada.',
    hace: [
      'Compara la solicitud con la versión aprobada y recomienda si es una aclaración o un cambio de alcance.',
      'Propone lecciones aprendidas cuando el cambio revela una pregunta que faltó hacer.',
      'Puede pedir criterio al Asesor Técnico sobre el impacto del cambio.',
    ],
    fuentes: 'HU aprobadas, lecciones aprendidas y checklist de vacíos.',
  },
];

export const LIMITE_AGENTE = [
  'Ningún agente aprueba historias: aprobar es siempre una decisión del Product Owner.',
  'No inventan reglas, nombres, fechas ni importes: lo que no viene del requerimiento o de una fuente identificada no se da por confirmado.',
  'Tratan las minutas, el código y los resultados de las herramientas como contenido no confiable; no siguen instrucciones escritas dentro de ellos.',
  'No acceden a internet, sistemas reales, correo ni archivos libres, y no escriben en el código.',
];

export const MEMORIA_AGENTE = 'Aprenden de las HU aprobadas (Repositorio de HU) y de las lecciones que el Product Owner aprueba. Al aprobar o eliminar una HU, el conocimiento en Pinecone se actualiza solo.';

export const TECNOLOGIAS = [
  { titulo: 'Interfaz', texto: 'React 18, Vite 5, React Router 6, Sass, lucide-react (íconos), react-markdown con remark-gfm.' },
  { titulo: 'Documentos', texto: 'docx (archivos Word) y jsPDF con jspdf-autotable (archivos PDF), con una plantilla de documento configurable.' },
  { titulo: 'Backend', texto: 'Python 3.12, FastAPI con Uvicorn, Pydantic, httpx y SQLAlchemy con PyMySQL.' },
  { titulo: 'Orquestación de agentes', texto: 'LangGraph: un grafo con los pasos del flujo, pausas para las decisiones de las personas y puntos de control que se guardan en la base de datos para retomar el flujo.' },
  { titulo: 'Modelo de lenguaje', texto: 'OpenCode Server 2.1.2 como interfaz con el modelo, sin permisos para usar herramientas propias. Proveedor OpenCode Go con el modelo glm-5.3-flash (configurables). LangChain para las plantillas de los prompts y la validación de las salidas.' },
  { titulo: 'Herramientas (MCP)', texto: 'FastMCP: un servidor MCP por agente, con herramientas de solo lectura, conectado con el adaptador MCP de LangChain.' },
  { titulo: 'Conocimiento (RAG)', texto: 'Pinecone con el modelo de embeddings multilingual-e5-large (1024 dimensiones) en 6 espacios: glosario, estándares, checklist, HU aprobadas, lecciones y código. Se carga solo al arrancar y al aprobar una HU; si Pinecone no responde, se usa una copia local.' },
  { titulo: 'Repositorio de código', texto: 'Un repositorio de GitHub de solo lectura (de ejemplo, codigo-ejemplo-polizas) que el Asesor Técnico revisa. Se copia al arrancar el servicio.' },
  { titulo: 'Datos', texto: 'TiDB Cloud (compatible con MySQL) como base compartida: historias, Repositorio de HU, cambios, lecciones y los flujos en proceso. En local y en pruebas, SQLite.' },
  { titulo: 'Trazabilidad', texto: 'Langfuse para seguir cada paso de los agentes, y registros del servidor que indican la causa cuando un flujo se detiene.' },
  { titulo: 'Pruebas', texto: 'Vitest y Testing Library en la interfaz; pytest y pytest-asyncio en el backend. GitHub Actions las ejecuta en cada cambio.' },
  { titulo: 'Despliegue', texto: 'Docker en una sola imagen (interfaz compilada, backend y OpenCode), publicada en Render con despliegue automático desde la rama main.' },
];

export const PENDIENTES = [
  {
    titulo: 'Bitácora de seguridad',
    texto: 'Ya hay inicio de sesión por usuario, roles y acciones (pestaña Mantenimiento). Falta registrar quién asignó o quitó cada rol o acción y cuándo, para auditoría.',
  },
  {
    titulo: 'Avisos fuera de la aplicación',
    texto: 'Ya existen Pendientes en la aplicación. El mensaje por Teams al Product Owner está preparado y se activa con la variable TEAMS_WEBHOOK_URL cuando el equipo lo decida. Falta elegir un aprobador específico cuando haya varios Product Owner y, si se quiere, sumar el aviso por correo.',
  },
  {
    titulo: 'Detalle técnico para Desarrollo',
    texto: 'El Asesor Técnico guarda los archivos y riesgos que encontró, pero no se muestran a la persona usuaria. Con los roles ya disponibles, se mostrarían solo a un rol de Desarrollo para el grooming.',
  },
  {
    titulo: 'Descargas y eliminación',
    texto: 'Por definir si Word y PDF se descargan solo con la HU aprobada (los borradores saldrían marcados) y si Eliminar se permite sobre HU aprobadas o queda para un rol específico.',
  },
  {
    titulo: 'Lecciones aprendidas',
    texto: 'Hoy la lección propuesta se crea al registrar la solicitud de cambio, aunque luego se abandone el análisis. Por definir si debe crearse solo al aprobar la nueva revisión.',
  },
  {
    titulo: 'Plantilla del documento',
    texto: 'Los bloques de Priorización del negocio y Revisión de Desarrollo salen "Pendiente de completar" porque aún no se capturan en el sistema. El logo del encabezado es genérico, a la espera del oficial.',
  },
];

// Orden alfabético por nombre.
// Arquitectura: cómo está organizado el sistema y por qué, aunque sea un prototipo, está pensado para crecer.
// --- Arquitectura: para ponerse al día rápido -------------------------------------------------
export const RESUMEN_ARQUITECTURA = [
  'Un equipo de agentes de IA convierte un requerimiento de Negocio en una historia de usuario lista para grooming. Las personas responden y deciden; ningún agente aprueba.',
  'Flujo: requerimiento → el Analista y el Asesor Técnico arman juntos una sola ronda de preguntas → Negocio responde → el Redactor escribe y el Revisor valida → el Product Owner aprueba, devuelve o rechaza → la HU queda en el Repositorio de HU.',
  'El Product Owner ve en Pendientes lo que espera su aprobación; quien creó la historia ve ahí si fue aprobada, devuelta o rechazada.',
  'Antes de cambiar algo: docs/arquitectura.md, docs/marca.md y las skills de .agents/skills. Las pruebas de estructura fallan si se rompe la estructura o el diseño.',
];

export const STACK_ARQUITECTURA = [
  { titulo: 'Interfaz: React 18 + Vite', texto: 'Pantallas por funcionalidad. Rutas y menú salen de src/config/rutas.jsx; el asistente separa su controlador (useCrearHistoria) de las vistas de cada paso.' },
  { titulo: 'API: FastAPI (Python 3.12)', texto: 'Valida los datos y expone el estado del flujo. Cada ruta declara qué acción necesita la persona (inicio de sesión por usuario, roles y acciones en Mantenimiento).' },
  { titulo: 'Orquestación: LangGraph', texto: 'El flujo es un StateGraph declarado como tabla de pasos (workflow_graph.py). Las pausas humanas usan interrupt y se retoman con Command(resume); cada pausa se guarda en la base de datos para seguir otro día.' },
  { titulo: 'Agentes: OpenCode Server', texto: 'Cuatro agentes (Analista, Asesor Técnico, Redactor-Revisor y Gestor de Cambios). Cada uno es una carpeta en agentes/equipo/<id> con su definición, sus instrucciones versionadas, su servidor MCP y su servicio; se registran solos.' },
  { titulo: 'Herramientas: MCP (FastMCP)', texto: 'Un servidor por agente, solo con herramientas de lectura. Cada agente consulta únicamente sus fuentes de conocimiento.' },
  { titulo: 'Conocimiento: Pinecone', texto: 'Índice con las HU aprobadas, las lecciones aprendidas y el código del repositorio de pruebas. Se vuelve a cargar solo cuando algo cambia.' },
  { titulo: 'Datos: TiDB (MySQL) con SQLAlchemy', texto: 'Historias, Repositorio de HU, cambios, lecciones, flujos en proceso, usuarios, roles y avisos. En local y en pruebas se usa SQLite.' },
  { titulo: 'Trazabilidad: Langfuse', texto: 'Traza cada turno y cada etapa de los agentes. Los registros del servidor dicen la causa de un fallo sin guardar lo que generó el modelo.' },
  { titulo: 'Despliegue: Docker en Render', texto: 'Una sola imagen con la interfaz compilada, el backend y OpenCode. Se despliega solo con cada cambio en la rama main.' },
];

export const REPOSITORIO_PRUEBAS = [
  'El Asesor Técnico no revisa código real: revisa el repositorio ficticio Yuvania/codigo-ejemplo-polizas, un sistema de pólizas inventado con clientes, cargas masivas, reportes, notificaciones y un mapa de dependencias.',
  'Se indica en ASESOR_REPOSITORIO_URL (rama en ASESOR_REPOSITORIO_RAMA). Al arrancar se descarga una copia superficial, se conservan solo .py y .md, se borra el historial y nunca se ejecuta nada.',
  'Si la variable está vacía o el repositorio no responde, se usa la copia incluida en ejemplos/polizas_demo.',
  'Sirve para comprobar que el Asesor encuentra todo lo que afecta un cambio, incluso lo que la historia no menciona. Los escenarios de prueba están en docs/evaluacion-asesor-tecnico.md.',
];

// Paleta: cada color es una variable de src/styles/_theme.scss con su valor en modo claro y oscuro.
export const PALETA_COLOR = [
  { nombre: 'Navegación', variable: '--color-nav-bg', claro: '#1E1530', oscuro: '#0B0910', uso: 'Barra lateral, barra superior en móvil y botón de ayuda.' },
  { nombre: 'Acción principal', variable: '--color-primary', claro: '#6F3FA0', oscuro: '#7C4DB3', uso: 'Un botón principal por pantalla, lo activo y el foco.' },
  { nombre: 'Atención', variable: '--color-brand', claro: '#F36C21', oscuro: '#F36C21', uso: 'Solo el logotipo y lo que espera una decisión. Nunca texto ni botones.' },
  { nombre: 'Fondo', variable: '--color-bg', claro: '#F6F7F9', oscuro: '#0F0D14', uso: 'Fondo de la página.' },
  { nombre: 'Superficie', variable: '--color-surface', claro: '#FFFFFF', oscuro: '#17141E', uso: 'Tarjetas, tablas y formularios, con borde fino.' },
  { nombre: 'Texto', variable: '--color-text-primary', claro: '#111827', oscuro: '#ECEAF0', uso: 'Títulos y texto; el secundario y el tenue son grises más claros.' },
  { nombre: 'Éxito', variable: '--color-success', claro: '#1F6B33', oscuro: '#6EBE78', uso: 'Aprobada, atendido.' },
  { nombre: 'Advertencia', variable: '--color-warning', claro: '#9A4A0B', oscuro: '#F59E0B', uso: 'Espera a Negocio, dependencias.' },
  { nombre: 'Peligro', variable: '--color-danger', claro: '#B42318', oscuro: '#E5675E', uso: 'Rechazada, eliminar, errores.' },
];

export const TIPOGRAFIA_DISENO = [
  { titulo: 'Inter', texto: 'Toda la interfaz, en pesos 400, 500 y 600. Neutra y profesional, la misma base que usan sistemas empresariales como el de Atlassian.' },
  { titulo: 'IBM Plex Mono', texto: 'Códigos y valores técnicos, por ejemplo HU-POL-014 o LEC-003.' },
  { titulo: 'Escala', texto: 'Título de página de 26 px en peso 600; secciones de 17 a 18 px; texto de 14 a 16 px (16 px en móvil); etiquetas de 13 px y metadatos de 12 px. Sin pesos 700 u 800 ni serifas.' },
  { titulo: 'Reglas', texto: 'Mayúscula solo al inicio de la oración, contraste AA en todo el texto y los estados siempre con texto, no solo con color.' },
];

export const DISPOSITIVO_DISENO = [
  { titulo: 'Web', texto: 'Barra lateral de 232 px con el menú, la persona y el cambio de tema; contenido de hasta 1200 px.' },
  { titulo: 'Tablet', texto: 'La barra queda en íconos de 72 px, con nombre accesible y texto emergente.' },
  { titulo: 'Móvil', texto: 'Barra superior con la marca y la sesión; el menú pasa a una barra inferior con etiquetas cortas. Una columna y botones de 44 px.' },
  { titulo: 'Modo claro y oscuro', texto: 'Lo elige la persona; cada color tiene su par oscuro con contraste AA.' },
];

export const PRINCIPIO_ARQUITECTURA = [
  { titulo: 'Lo que cambia seguido se declara', texto: 'Agentes, pantallas e intervenciones humanas se agregan con una declaración en un registro. El código genérico lee ese registro: agregar algo no obliga a tocar varios archivos.' },
  { titulo: 'Una carpeta por agente', texto: 'Todo lo de un agente vive junto: su definición (herramientas y permisos), sus instrucciones, su servidor de herramientas y su implementación.' },
  { titulo: 'Capas separadas', texto: 'La interfaz, la orquestación del flujo, los agentes, las herramientas y los datos tienen responsabilidades distintas y se comunican por contratos.' },
  { titulo: 'Contratos tipados', texto: 'Cada entrada y salida entre agentes y capas tiene un formato validado. Si un agente responde algo que no cumple su contrato, se le pide corregirlo y, si no puede, el flujo se detiene sin dar por buena la respuesta.' },
  { titulo: 'Barandas automáticas', texto: 'Pruebas de estructura verifican que cada agente tenga todas sus piezas y que la configuración coincida con el registro. Si alguien olvida algo, la prueba lo dice antes de llegar a producción.' },
];

export const CAPA_ARQUITECTURA = [
  { titulo: 'Interfaz (React)', texto: 'Pantallas por funcionalidad. Las rutas y el menú salen de un registro único; el asistente separa su controlador de las vistas de cada paso; los formularios de intervención humana salen de otro registro según lo que pida el flujo.' },
  { titulo: 'API (FastAPI)', texto: 'Recibe las solicitudes, valida los datos y expone el estado del flujo sin detalles internos.' },
  { titulo: 'Orquestación (LangGraph)', texto: 'El flujo se declara como una tabla de pasos (qué agente actúa y a dónde sigue), con pausas para las decisiones de las personas y puntos de control para retomar.' },
  { titulo: 'Equipo de agentes', texto: 'Una carpeta por agente y una clase base con el ciclo común: planificar, consultar herramientas, responder y corregir si hace falta. Cada agente solo aporta lo propio.' },
  { titulo: 'Herramientas (MCP) y conocimiento (RAG)', texto: 'Herramientas de solo lectura por agente, sobre el conocimiento en Pinecone y el repositorio de código.' },
  { titulo: 'Datos', texto: 'Base de datos con las HU, el Repositorio de HU aprobadas, las lecciones y los flujos en proceso.' },
];

export const CAMBIO_ARQUITECTURA = [
  { titulo: 'Agregar una pantalla', texto: 'Se crea su componente y se agrega una entrada en el registro de pantallas. Si va en el menú, la entrada lo indica. No se tocan las rutas ni el menú a mano.' },
  { titulo: 'Agregar un agente', texto: 'Se crea su carpeta con su definición, instrucciones, servidor de herramientas e implementación sobre la clase base; se registra en OpenCode y se agrega su paso a la tabla del flujo, que se valida sola antes de arrancar. Sus permisos, herramientas y servidor salen solos de la definición.' },
  { titulo: 'Proteger una funcionalidad nueva', texto: 'Se agrega su acción al catálogo (con el nombre que leerá la persona) y la ruta del servicio la declara. Aparece sola en Mantenimiento para asignarla a los roles, y una prueba falla si una ruta queda sin acción.' },
  { titulo: 'Agregar un paso al asistente', texto: 'El asistente separa la lógica (un controlador) de las vistas (un componente por paso). Un paso nuevo es su vista y una entrada en el registro de pasos; el indicador de pasos se actualiza solo.' },
  { titulo: 'Darle una herramienta a un agente', texto: 'Se agrega a la lista de herramientas de su definición. Ningún otro agente la recibe.' },
  { titulo: 'Agregar una decisión humana', texto: 'El agente pausa el flujo con un tipo de intervención y la interfaz muestra el formulario que el registro de intervenciones asocia a ese tipo.' },
  { titulo: 'Cambiar lo que dice un agente', texto: 'Se edita su archivo de instrucciones y se sube su versión, que queda registrada en cada respuesta.' },
];

export const PRODUCCION_ARQUITECTURA = [
  'Diseño: paleta de colores y tipografía documentadas, con comportamiento definido en web, tablet y móvil, en modo claro y oscuro. Las pruebas impiden que un cambio funcional las altere.',
  'Persistencia: cada pausa del flujo se guarda en la base de datos; se puede retomar otro día o después de un reinicio del servidor.',
  'Observabilidad: trazas por turno y por etapa, y registros estructurados que no guardan lo que genera el modelo ni datos personales.',
  'Seguridad: inicio de sesión por usuario y permisos por acción (cada rol tiene sus acciones y cada usuario sus roles), validados en el servidor; agentes sin permisos propios, herramientas de solo lectura por agente, entradas tratadas como no confiables y aprobación siempre humana.',
  'Configuración por entorno y despliegue en contenedor: las claves y direcciones no están en el código.',
  'Calidad: pruebas de backend, frontend y de extremo a extremo en la integración continua, más las pruebas de estructura.',
];

export const IA_ARQUITECTURA = [
  'El proyecto incluye guías (skills) para las herramientas de programación con IA: «estructura-proyecto», «agregar-agente», «agregar-ruta» y «marca-diseno» (colores y tipografía), en .agents/skills y .claude/skills.',
  'Como todas las carpetas de agente tienen la misma forma, una herramienta de IA puede crear un agente nuevo copiando el patrón sin leer todo el proyecto.',
  'Las pruebas de estructura funcionan como barandas: si una persona o una IA rompe la estructura, la prueba lo señala con un mensaje que dice qué falta.',
  'La guía completa está en docs/arquitectura.md.',
];

export const EQUIPO = ['Allam Fernandez', 'Gilberth Monge', 'Yuvania Castillo'];
