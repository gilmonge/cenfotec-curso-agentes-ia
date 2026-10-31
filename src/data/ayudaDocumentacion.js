// Contenido de la página de Ayuda (texto fijo). Cada bloque es una lista de { titulo, texto, puntos? }.

export const PASOS_ASISTENTE = [
  {
    titulo: 'Paso 1 — Requerimiento',
    texto: 'Ingrese la minuta, el correo o el incidente que llegó de Negocio, con su título, tipo de información, sistema, código de HU y área solicitante. El avance se guarda solo como borrador y se recupera si se pierde la conexión.',
  },
  {
    titulo: 'Paso 2 — Análisis del Agente Analista',
    texto: 'El agente consulta el glosario, las HU similares, los estándares y el checklist de vacíos, y clasifica la información en conocida, faltante, supuesta y ambigua. Puede tardar hasta 90 segundos y se puede cancelar.',
  },
  {
    titulo: 'Paso 3 — Preguntas para Negocio',
    texto: 'El agente arma preguntas en lenguaje natural, agrupadas por tema. Usted las lleva a Negocio, registra las respuestas y las envía al agente.',
    puntos: [
      'Si hay respuestas nuevas, el reanálisis es obligatorio: no se puede avanzar sin enviarlas.',
      'Se repite hasta que no queden preguntas pendientes. Las respuestas ya dadas se conservan entre reanálisis.',
      'Mientras queden pendientes se puede guardar la HU como borrador.',
    ],
  },
  {
    titulo: 'Paso 4 — Historia y criterios (borrador)',
    texto: 'Borrador editable en formato Como / Quiero / Para, con criterios de aceptación en formato Dado que / Cuando / Entonces. El Agente Redactor-Revisor aún no está implementado: hoy el borrador es simulado y la persona lo redacta y corrige.',
  },
  {
    titulo: 'Paso 5 — Aprobación del Product Owner',
    texto: 'El Product Owner revisa el resumen y confirma que los datos están anonimizados. No se puede aprobar con preguntas pendientes. Al aprobar, la HU queda como Aprobada, se guarda en el Repositorio de HU (la memoria que el agente consulta en análisis futuros) y se habilitan Solicitar cambio y las descargas.',
  },
];

export const NAVEGACION_ASISTENTE = [
  'Use Atrás para volver al paso anterior sin perder lo escrito.',
  'Los pasos avanzan en orden: cada botón se habilita cuando el paso anterior está completo.',
  'Si se interrumpe el trabajo, al volver a Nueva Historia se ofrece recuperar el borrador.',
];

export const ACCIONES_HISTORIA = [
  {
    titulo: 'Ver detalle',
    texto: 'Es solo de consulta: arriba ofrece únicamente Volver. Muestra la historia en pestañas (Historia, Criterios de aceptación, Preguntas pendientes, Observaciones, Historial, Análisis y Datos de la plantilla); cada pestaña aparece solo si la HU tiene ese dato. Si hay preguntas pendientes o el análisis quedó desactualizado, avisa y ofrece responderlas o volver a analizar.',
  },
  {
    titulo: 'Editar',
    texto: 'Abre el formulario por secciones.',
    puntos: [
      'Antes de aprobar se puede cambiar todo. Si cambian el requerimiento o las respuestas, queda marcado que hay que volver a analizar; cambiar solo los criterios no lo exige.',
      'Con la HU aprobada sirve para corregir redacción o datos mal escritos: se guarda en el lugar, sigue aprobada, no sube la revisión ni pasa por el agente, y queda registrado quién editó, cuándo y qué campos.',
      'Antes de guardar una HU aprobada se actualiza el Repositorio; si lo rechaza (por ejemplo, por datos personales), no se guarda nada.',
      'Las observaciones se agregan como notas con fecha y autor (bitácora).',
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
    texto: 'Genera la HU en Word o PDF con la plantilla de documento (código de formato, encabezado, pie con número de página). Las observaciones salen en una página final, solo con su texto.',
  },
  {
    titulo: 'Eliminar',
    texto: 'Solo está en el listado y pide confirmación. Si la HU ya estaba aprobada, primero se borra del Repositorio para que el agente deje de usarla; si eso falla, no se borra y se informa el motivo. Después se borra de la base y del navegador.',
  },
];

export const AGENTE_ANALISTA = {
  rol: 'Agente Analista de Requerimientos. Es un agente semiautónomo: investiga en sus fuentes, razona, clasifica y hace preguntas, y luego se detiene a esperar las respuestas de Negocio.',
  hace: [
    'Descubre y aclara los vacíos de un requerimiento antes de redactar la HU y de llegar al grooming.',
    'Clasifica la información en conocida, faltante, supuesta y ambigua.',
    'Genera preguntas por categoría, con palabras de negocio, y reanaliza cuando llegan las respuestas.',
    'Cita el estándar que sustenta una pregunta y advierte si detecta datos personales sin anonimizar.',
  ],
  herramientas: [
    'Glosario de términos de seguros.',
    'Búsqueda de HU similares ya aprobadas.',
    'Estándares de desarrollo e interfaz.',
    'Checklist de vacíos (estados, permisos, validaciones, excepciones y vigencias).',
  ],
  noHace: [
    'No redacta ni aprueba historias de usuario.',
    'No inventa reglas, nombres, fechas ni importes: lo que no viene del requerimiento o de una fuente identificada no se da por confirmado.',
    'Trata las minutas y los resultados de las herramientas como contenido no confiable; no sigue instrucciones escritas dentro de ellos.',
    'No accede a internet, sistemas reales, correo ni archivos libres.',
  ],
  memoria: 'Aprende de las HU aprobadas (Repositorio de HU) y de las lecciones que el Product Owner aprueba. Una HU eliminada deja de usarse como referencia.',
  pendientes: 'Aún no están implementados el Agente Redactor-Revisor, el Asesor Técnico ni el Gestor de Cambios: hoy la persona redacta, y el Product Owner clasifica los cambios.',
};

export const TECNOLOGIAS = [
  { titulo: 'Interfaz', texto: 'React 18, Vite 5, React Router 6, Sass, lucide-react (íconos), react-markdown con remark-gfm.' },
  { titulo: 'Documentos', texto: 'docx (archivos Word) y jsPDF con jspdf-autotable (archivos PDF), con una plantilla de documento configurable.' },
  { titulo: 'Backend', texto: 'Python 3.12, FastAPI con Uvicorn, Pydantic, httpx, SQLAlchemy con PyMySQL.' },
  { titulo: 'Agente de IA', texto: 'LangChain, FastMCP/MCP para las herramientas del agente y OpenCode Server 2.1.2 como interfaz con el modelo (proveedor y modelo configurables). Trazabilidad con Langfuse.' },
  { titulo: 'Datos', texto: 'TiDB Cloud (compatible con MySQL) como base compartida del equipo, con una copia local en el navegador que se sincroniza.' },
  { titulo: 'Pruebas', texto: 'Vitest y Testing Library en la interfaz; pytest y pytest-asyncio en el backend.' },
  { titulo: 'Despliegue', texto: 'Docker en una sola imagen (interfaz compilada + backend + OpenCode), publicada en Render con despliegue automático desde la rama main.' },
];

export const PENDIENTES = [
  {
    titulo: 'Flujo de aprobación',
    texto: 'Hoy cualquiera puede aprobar. Se propone que las HU creadas por Negocio queden en "Pendiente de aprobación" hasta que el Product Owner las revise: lo apruebe o la devuelva con comentario. Solo al aprobarse pasarían a Aprobada, entrarían al Repositorio y se habilitarían las descargas.',
  },
  {
    titulo: 'Roles y permisos',
    texto: 'Se propone un esquema estándar de roles y permisos: roles a los que se asignan permisos (por ejemplo aprobar-historia-usuario, solicitar-cambio, eliminar-historia), y roles que se asignan a los usuarios. Roles iniciales sugeridos: Negocio, Analista, Product Owner y Administrador. Los permisos se validarían en el backend, no solo ocultando botones.',
  },
  {
    titulo: 'Usuarios e inicio de sesión',
    texto: 'Hoy no hay inicio de sesión: el nombre se escribe a mano. Para el prototipo se propone una tabla de usuarios con usuario y contraseña (guardada con hash) y una pantalla de ingreso; el autor de la bitácora y de las ediciones saldría de ahí. Más adelante el ingreso podría cambiarse por Active Directory sin tocar los roles. También se prevé una pantalla de Seguridad para administrar usuarios, roles y permisos.',
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
  {
    titulo: 'Agentes pendientes',
    texto: 'Falta construir el Agente Redactor-Revisor, el Asesor Técnico y el Gestor de Cambios.',
  },
];

// Orden alfabético por nombre.
export const EQUIPO = ['Allam Fernandez', 'Gilberth Monge', 'Yuvania Castillo'];
