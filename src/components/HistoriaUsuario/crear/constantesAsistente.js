// Constantes del asistente para crear una historia: pasos, opciones y textos fijos.

export const ROTULO_ESTADO_WORKFLOW = {
  failed: 'detenido por un error',
  running: 'en ejecución',
  completed: 'finalizado',
  cancelled: 'cancelado',
};

export const PASO = Object.freeze({ REQUERIMIENTO: 1, ANALISIS: 2, PREGUNTAS: 3, HISTORIA: 4, APROBACION: 5 });

export const pasoDelFlujo = (snapshot) => {
  const kind = snapshot?.interrupt?.kind;
  if (kind === 'business_answers') return PASO.PREGUNTAS;
  if (snapshot?.results?.story) return PASO.HISTORIA;
  return snapshot?.results?.analyst ? PASO.PREGUNTAS : null;
};

export const CAMPO_FORMULARIO = ['requirementName', 'infoType', 'requestType', 'system', 'codigoHu', 'requester', 'description'];

export const INFO_TYPE_OPTIONS = [
  { value: 'Minuta', label: 'Minuta de reunión' },
  { value: 'Correo', label: 'Correo' },
  { value: 'Incidente', label: 'Incidente' },
  { value: 'Solicitud de cambio', label: 'Solicitud de cambio (nueva HU)' },
  { value: 'Descripción libre', label: 'Descripción libre' },
  { value: 'Notas de conversación', label: 'Notas de conversación' },
  { value: 'Otro', label: 'Otro formato' }
];
