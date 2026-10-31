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
      'Entre a "Nueva Historia" en el menú superior.',
      'Complete el requerimiento: título, tipo de información, sistema, área solicitante y descripción.',
      'Pulse el análisis para que el Agente Analista revise el requerimiento.',
      'Responda las preguntas que genere el agente, con la información que le dé Negocio.',
      'Revise el borrador (Como / Quiero / Para) y los criterios de aceptación.',
      'Guarde la historia. Quedará en la lista de Historias de Usuario.',
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
    id: 'datos',
    pregunta: '¿Puedo usar datos reales del negocio?',
    texto:
      'No. Las fuentes del agente son simuladas o anonimizadas. Anonimice cualquier dato personal antes de escribirlo.',
  },
  {
    id: 'guardado',
    pregunta: '¿Dónde se guardan las historias?',
    texto:
      'En la base de datos del sistema, por lo que las ve todo el equipo desde cualquier navegador. El navegador solo guarda una copia temporal para mostrarlas más rápido.',
  },
];

// Preguntas que se ofrecen como botones al abrir el chat.
export const SUGERENCIA_INICIAL = ['crear', 'codigo', 'criterios', 'reanalisis'];

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
