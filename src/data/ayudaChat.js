// Preguntas frecuentes del chat de ayuda. Texto fijo: no usa ningún modelo ni consume cuota.
// Cada respuesta es una lista de párrafos; "pasos" se muestra como lista numerada.
export const BIENVENIDA_AYUDA =
  'Hola, soy el asistente de ayuda. Elija una pregunta y le explico cómo usar el sistema.';

export const PREGUNTAS_AYUDA = [
  {
    id: 'crear',
    pregunta: '¿Cómo creo una historia?',
    texto: 'Para crear una historia de usuario:',
    pasos: [
      'Entre a "Nueva historia" en el menú superior.',
      'Complete el requerimiento: título, tipo de información, sistema, área solicitante y descripción.',
      'Pulse «Analizar Requerimiento» para que el Agente Analista lo revise.',
      'Lleve a Negocio, en una sola ronda, las preguntas del Analista y las decisiones del Asesor Técnico, y registre las respuestas.',
      'Revise la historia (Como / Quiero / Para) y los criterios que redactó el Redactor-Revisor.',
      'El Product Owner la aprueba y queda en el Repositorio de HU.',
    ],
  },
  {
    id: 'codigo',
    pregunta: '¿Qué es el código de la HU?',
    texto:
      'Es el identificador que ve el equipo, con el formato PREFIJO-CODIGO-001 (por ejemplo HU-CODIGO-001). El consecutivo se propone solo al crear la historia. Internamente cada historia también tiene un identificador técnico (GUID) que no se muestra y que no es el código.',
  },
  {
    id: 'analisis',
    pregunta: '¿Qué hace el análisis del requerimiento?',
    texto:
      'El Agente Analista revisa el requerimiento y clasifica la información en conocida, faltante, supuesta y ambigua. Con lo faltante arma preguntas por categoría para llevar a Negocio. Si cambia el título, el tipo de información o la descripción del requerimiento, la historia queda marcada para volver a analizarse.',
  },
  {
    id: 'criterios',
    pregunta: '¿Cómo edito los criterios de aceptación?',
    texto: 'Cada criterio tiene tres partes. Para editarlos:',
    pasos: [
      'Abra la historia y pulse "Editar" (o use el paso de criterios al crearla).',
      'Complete "Dado que", "Cuando" y "Entonces" en cada criterio.',
      'Use "Agregar criterio" para sumar otro o "Quitar" para eliminarlo.',
      'Debe quedar al menos un criterio completo.',
    ],
  },
  {
    id: 'reanalisis',
    pregunta: '¿Cuándo debo volver a analizar?',
    texto:
      'Cuando cambia el requerimiento (título, tipo de información o descripción) el sistema avisa que el análisis quedó desactualizado. Cambiar solo los criterios no obliga a analizar de nuevo: la historia se marca como "Criterios modificados" para que se revise.',
  },
  {
    id: 'editar',
    pregunta: '¿Cómo modifico una historia ya creada?',
    texto:
      'Abra la historia desde la lista y pulse "Editar". La pantalla muestra secciones colapsables; abra la que necesite, haga el cambio y guarde.',
  },
  {
    id: 'aprobar',
    pregunta: '¿Qué pasa cuando el Product Owner aprueba?',
    texto:
      'La historia aprobada se guarda, anonimizada, en el Repositorio de HU. Es la memoria que el agente consulta en análisis futuros para encontrar historias similares.',
  },
  {
    id: 'cambios',
    pregunta: '¿Qué hago si llega un cambio a una HU aprobada?',
    texto:
      'Para corregir redacción o datos mal escritos use Editar: se guarda en el lugar y queda registrado quién y cuándo. Si Negocio pide algo distinto, use Solicitar cambio (ícono de acciones del listado, en historias aprobadas): se vuelve a analizar y, si faltó una pregunta, se propone una lección aprendida (LEC-001, LEC-002…) para análisis futuros.',
  },
  {
    id: 'retomar',
    pregunta: '¿Puedo dejar una historia a medias y seguir otro día?',
    texto:
      'Sí. Cada vez que el flujo espera una respuesta, el avance se guarda. Vaya a Historias de Usuario: arriba, en «En proceso», pulse Retomar y se abre en el paso donde quedó. En las preguntas puede usar «Guardar sin enviar» para dejar respuestas a medias.',
  },
  {
    id: 'impacto',
    pregunta: '¿Qué es el impacto en otros módulos?',
    texto:
      'El Asesor Técnico revisa el código del sistema justo después del primer análisis del Analista y explica, sin detalle técnico, qué otras funciones afecta el cambio (por ejemplo, una carga masiva o un reporte). Se muestra en el paso 3, junto con las decisiones que Negocio debe tomar, en la misma ronda que las preguntas del Analista. La historia se redacta después, ya con esos impactos como criterios.',
  },
  {
    id: 'datos',
    pregunta: '¿Puedo usar datos reales del negocio?',
    texto:
      'No. Las fuentes de los agentes y el código que revisa el Asesor Técnico son de ejemplo o anonimizados. Anonimice cualquier dato personal antes de escribirlo.',
  },
  {
    id: 'guardado',
    pregunta: '¿Dónde se guardan las historias?',
    texto:
      'En la base de datos del sistema, por lo que las ve todo el equipo desde cualquier navegador. El navegador solo guarda una copia temporal para mostrarlas más rápido.',
  },
  {
    id: 'arquitectura',
    pregunta: '¿Cómo está construido el sistema?',
    texto:
      'Por capas (interfaz, API, orquestación, agentes, herramientas y datos) y con registros: cada agente es una carpeta con su definición, y las pantallas salen de un registro único. Así, agregar un agente o una pantalla se hace en un solo lugar. El detalle está en Ayuda → Arquitectura.',
  },
  {
    id: 'pendientes',
    pregunta: '¿Dónde veo lo que tengo por aprobar?',
    texto:
      'En Pendientes, en el menú: el número indica cuántas cosas esperan su decisión o tiene avisos sin leer. El Product Owner ve las historias por aprobar; quien creó una historia ve si fue aprobada, devuelta con su motivo o rechazada.',
  },
  {
    id: 'mantenimiento',
    pregunta: '¿Cómo doy permisos a una persona?',
    texto:
      'En Mantenimiento (solo para administradores). En Usuarios se busca a la persona y se le marcan sus roles; en Roles se elige un rol y se marcan sus acciones, por ejemplo Aprobar historia. El cambio aplica de inmediato. Solo quien tenga la acción de aprobar ve la opción Aprobar en el paso 5.',
  },
];

// Preguntas que se ofrecen como botones al abrir el chat.
export const SUGERENCIA_INICIAL = ['crear', 'retomar', 'impacto', 'codigo'];

export const TEXTO_SIN_COINCIDENCIA =
  'No tengo una respuesta fija para eso. Este asistente solo responde las preguntas de la lista; elija una de ellas.';

const normalizar = (valor) =>
  String(valor || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

// Búsqueda simple por palabras para el cuadro de texto: no interpreta preguntas abiertas.
export const buscarPregunta = (consulta) => {
  const palabras = normalizar(consulta)
    .split(/[^a-z0-9]+/)
    .filter((palabra) => palabra.length > 3);
  if (!palabras.length) return null;
  let mejor = null;
  let puntaje = 0;
  PREGUNTAS_AYUDA.forEach((item) => {
    const enPregunta = normalizar(item.pregunta);
    const enRespuesta = normalizar(`${item.texto} ${(item.pasos || []).join(' ')}`);
    // La coincidencia con la pregunta pesa más que la coincidencia con el texto de la respuesta.
    const total = palabras.reduce(
      (suma, palabra) => suma + (enPregunta.includes(palabra) ? 3 : 0) + (enRespuesta.includes(palabra) ? 1 : 0),
      0,
    );
    if (total > puntaje) {
      puntaje = total;
      mejor = item;
    }
  });
  return mejor;
};
