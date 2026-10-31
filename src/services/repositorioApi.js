import { request } from './analystApi.js';
import { criterioCompleto, limpiarCriterios, resumenCriterio } from '../utils/criterios.js';

// Repositorio de HU: memoria de largo plazo del Agente Analista (base de datos MySQL/TiDB en el backend).
export const repositorioApi = Object.freeze({
  saveStory: (payload, { signal } = {}) => request('/repositorio/historias', { method: 'POST', body: payload, signal }),
  deleteStory: (id, { signal } = {}) => request(`/repositorio/historias/${encodeURIComponent(id)}`, { method: 'DELETE', signal }),
  listStories: ({ signal } = {}) => request('/repositorio/historias', { signal }),
  registerChange: (payload, { signal } = {}) => request('/repositorio/cambios', { method: 'POST', body: payload, signal }),
  listChanges: (huId, { signal } = {}) => request(`/repositorio/cambios?hu_id=${encodeURIComponent(huId)}`, { signal }),
  listLessons: (estado, { signal } = {}) => request(
    `/repositorio/lecciones${estado ? `?estado=${encodeURIComponent(estado)}` : ''}`,
    { signal },
  ),
  decideLesson: (lessonId, decision, { signal } = {}) => request(
    `/repositorio/lecciones/${encodeURIComponent(lessonId)}/decision`,
    { method: 'POST', body: { decision }, signal },
  ),
});

// Historias de trabajo del equipo: se guardan en la base de datos y se comparten entre dispositivos.
export const historiasApi = Object.freeze({
  list: ({ signal } = {}) => request('/historias', { signal }),
  save: (story, { signal } = {}) => request(`/historias/${encodeURIComponent(story.id)}`, { method: 'PUT', body: story, signal }),
  remove: (id, { signal } = {}) => request(`/historias/${encodeURIComponent(id)}`, { method: 'DELETE', signal }),
});

// El backend envía mensajes concretos (por ejemplo, datos personales detectados): se muestran tal cual.
export function repositorioErrorMessage(error) {
  if (error?.code === 'NETWORK_ERROR') return 'No hay conexión con el backend local. Inicie el servicio e inténtelo de nuevo.';
  if (error?.code === 'REPOSITORY_NOT_FOUND') return 'La HU no está en el Repositorio de HU.';
  if (error?.name === 'AnalystApiError' && error.message) return error.message;
  return 'No fue posible completar la operación en el Repositorio de HU.';
}

export function buildRepositoryPayload({ id, code, title, infoType, description, userStory, acceptanceCriteria, questions }) {
  return {
    id,
    codigo: String(code ?? '').trim(),
    titulo: title.trim(),
    tipo_informacion: infoType,
    requerimiento: description.trim(),
    historia: {
      asA: userStory.asA.trim(),
      iWant: userStory.iWant.trim(),
      soThat: userStory.soThat.trim(),
    },
    criterios: limpiarCriterios(acceptanceCriteria)
      .filter(criterioCompleto)
      .map((criterion) => ({ text: resumenCriterio(criterion), given: criterion.given, when: criterion.when, then: criterion.then })),
    aclaraciones: questions
      .filter((question) => String(question.answer ?? '').trim())
      .slice(0, 10)
      .map((question) => ({ pregunta: question.question, respuesta: question.answer.trim() })),
    confirmo_anonimizada: true,
  };
}
