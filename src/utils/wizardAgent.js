// Funciones puras que conectan el wizard "Nueva Historia" con el Agente Analista.
// Traducen lo que escribe la persona a mensajes del agente y lo que responde el agente
// a los datos que muestran los pasos 2 y 3.

export const MAX_AGENT_MESSAGE_CODEPOINTS = 4000;

const SOURCE_LABELS = Object.freeze({
  consultar_glosario: 'Glosario',
  buscar_hu_similares: 'HU similares (ejemplo)',
  consultar_estandares: 'Estándares y skills',
  aplicar_checklist_vacios: 'Checklist de vacíos',
});

export function codepointLength(value) {
  return Array.from(String(value ?? '')).length;
}

function clean(value) {
  return String(value ?? '').trim();
}

export function requirementSignature({ name, infoType, description }) {
  return JSON.stringify([clean(name), clean(infoType), clean(description)]);
}

export function buildRequirementMessage({ name, infoType, description, system, codigoHu, requestType }, { isUpdate = false } = {}) {
  const header = isUpdate
    ? 'REQUERIMIENTO ACTUALIZADO (reemplaza al envío anterior; conserva las respuestas de Negocio que sigan siendo válidas)'
    : 'REQUERIMIENTO NUEVO';
  return [
    header,
    `Nombre: ${clean(name)}`,
    `Tipo de información: ${clean(infoType)}`,
    ...(clean(requestType) ? [`Tipo de solicitud: ${clean(requestType)}`] : []),
    ...(clean(system) ? [`Sistema: ${clean(system)}`] : []),
    ...(clean(codigoHu) ? [`Código de HU: ${clean(codigoHu)}`] : []),
    'Descripción:',
    clean(description),
  ].join('\n');
}

export function questionsToSend(questions, sentAnswers) {
  return questions.filter((question) => {
    const answer = clean(question.answer);
    return answer.length > 0 && sentAnswers[question.id] !== answer;
  });
}

export function buildAnswersMessage(questions, sentAnswers) {
  const pending = questionsToSend(questions, sentAnswers);
  if (pending.length === 0) return '';
  const lines = ['RESPUESTAS DE NEGOCIO a las preguntas anteriores. Actualiza el análisis y las preguntas pendientes.'];
  pending.forEach((question, index) => {
    lines.push('', `${index + 1}. [${question.category}] ${question.question}`, `Respuesta: ${clean(question.answer)}`);
  });
  return lines.join('\n');
}

export function mapAnalysis(analisis) {
  return {
    knownData: [...(analisis?.conocida ?? [])],
    missingData: [...(analisis?.faltante ?? [])],
    assumptions: [...(analisis?.supuesta ?? [])],
    ambiguities: [...(analisis?.ambigua ?? [])],
  };
}

const normalizarTexto = (value) => clean(value).toLowerCase().replace(/\s+/g, ' ');

// Combina las preguntas que devuelve el agente con las respuestas que la persona ya escribió.
// - La respuesta se conserva por id y, si el agente cambió el id o reformuló poco, por texto igual.
// - "Respondida" significa que hay una respuesta escrita: si el agente la da por resuelta pero no hay
//   texto, queda pendiente para que el campo y el conteo coincidan.
// - Si una pregunta con respuesta ya no aparece (el agente reorganizó las preguntas), se conserva con
//   su respuesta para no perder lo que la persona escribió.
export function mergeQuestions(previous, incoming) {
  const porId = new Map(previous.map((question) => [question.id, question]));
  const porTexto = new Map(previous.map((question) => [normalizarTexto(question.question), question]));
  const usadas = new Set();
  const combinadas = incoming.map((question) => {
    const anterior = porId.get(question.question_id) ?? porTexto.get(normalizarTexto(question.pregunta));
    if (anterior) usadas.add(anterior.id);
    const answer = anterior?.answer ?? '';
    return {
      id: question.question_id,
      category: question.categoria,
      question: question.pregunta,
      answer,
      status: clean(answer).length > 0 ? 'respondida' : 'pendiente',
    };
  });
  const conservadas = previous
    .filter((question) => !usadas.has(question.id) && clean(question.answer).length > 0)
    .map((question) => ({ ...question, status: 'respondida' }));
  return [...combinadas, ...conservadas];
}

export function latestAssistantResponse(messages) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const item = messages[index];
    if (item.role === 'assistant' && item.response) return item.response;
  }
  return null;
}

export function latestFailedMessage(messages) {
  const last = messages[messages.length - 1];
  return last && last.role === 'user' && last.status === 'failed' ? last : null;
}

export function describeSources(sources = []) {
  return sources.map((source) => ({
    key: source.nombre,
    label: SOURCE_LABELS[source.nombre] ?? source.nombre,
    count: source.resultados,
  }));
}
