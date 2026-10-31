const UUID4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const ANALYSIS_KEYS = ['conocida', 'faltante', 'supuesta', 'ambigua'];
const QUESTION_CATEGORIES = new Set([
  'Reglas de negocio', 'Datos requeridos', 'Validaciones', 'Excepciones', 'Comportamiento esperado',
]);
const QUESTION_STATES = new Set(['pendiente', 'respondida']);
const SOURCES = new Set([
  'consultar_glosario', 'buscar_hu_similares', 'consultar_estandares', 'aplicar_checklist_vacios',
]);

function hasExactKeys(value, expected) {
  return value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === expected.length
    && expected.every((key) => Object.hasOwn(value, key));
}

function textList(value, maximum, maxLength) {
  return Array.isArray(value) && value.length <= maximum
    && value.every((item) => typeof item === 'string' && item.trim().length > 0 && Array.from(item).length <= maxLength);
}

function validQuestion(question) {
  return hasExactKeys(question, ['question_id', 'categoria', 'pregunta', 'estado', 'created_turn_id', 'updated_turn_id'])
    && typeof question.question_id === 'string' && question.question_id.length > 0 && question.question_id.length <= 80
    && QUESTION_CATEGORIES.has(question.categoria)
    && typeof question.pregunta === 'string' && question.pregunta.trim().length > 0 && Array.from(question.pregunta).length <= 500
    && QUESTION_STATES.has(question.estado)
    && (question.created_turn_id === null || UUID4.test(question.created_turn_id))
    && (question.updated_turn_id === null || UUID4.test(question.updated_turn_id));
}

function validSource(source) {
  return hasExactKeys(source, ['nombre', 'resultados', 'duracion_ms'])
    && SOURCES.has(source.nombre)
    && Number.isInteger(source.resultados) && source.resultados >= 0
    && Number.isInteger(source.duracion_ms) && source.duracion_ms >= 0;
}

const RESPONSE_KEYS = [
  'conversation_id', 'request_id', 'turn_id', 'estado', 'respuesta_markdown', 'analisis',
  'preguntas', 'fuentes_consultadas', 'listo_para_redactor', 'limitaciones', 'duracion_ms', 'prompt_version',
];

export function isValidAnalystResponse(value) {
  // `beneficios` es opcional: lo propone el agente y la persona analista lo edita.
  const withBenefits = value && typeof value === 'object' && Object.hasOwn(value, 'beneficios');
  if (!hasExactKeys(value, withBenefits ? [...RESPONSE_KEYS, 'beneficios'] : RESPONSE_KEYS)) return false;
  if (withBenefits && !textList(value.beneficios, 5, 300)) return false;
  if (![value.conversation_id, value.request_id, value.turn_id].every((id) => typeof id === 'string' && UUID4.test(id))) return false;
  if (value.estado !== 'completado') return false;
  if (typeof value.respuesta_markdown !== 'string' || value.respuesta_markdown.trim().length < 1 || Array.from(value.respuesta_markdown).length > 50_000) return false;
  if (!hasExactKeys(value.analisis, ANALYSIS_KEYS) || !ANALYSIS_KEYS.every((key) => textList(value.analisis[key], 100, 1000))) return false;
  if (!Array.isArray(value.preguntas) || value.preguntas.length > 50 || !value.preguntas.every(validQuestion)) return false;
  if (!Array.isArray(value.fuentes_consultadas) || value.fuentes_consultadas.length > 4 || !value.fuentes_consultadas.every(validSource)) return false;
  if (typeof value.listo_para_redactor !== 'boolean') return false;
  const expectedReady = !value.analisis.faltante.length
    && !value.analisis.supuesta.length
    && !value.analisis.ambigua.length
    && !value.preguntas.some((question) => question.estado === 'pendiente');
  if (value.listo_para_redactor !== expectedReady) return false;
  if (!textList(value.limitaciones, 10, 300)) return false;
  if (!Number.isInteger(value.duracion_ms) || value.duracion_ms < 0) return false;
  return typeof value.prompt_version === 'string' && value.prompt_version.length > 0 && Array.from(value.prompt_version).length <= 40;
}

export function validateAnalystResponse(value) {
  if (isValidAnalystResponse(value)) return value;
  const error = new Error('El agente no devolvió una respuesta completa y válida.');
  error.code = 'AGENT_OUTPUT_INVALID';
  error.retryable = false;
  throw error;
}
