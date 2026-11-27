import { request } from './analystApi.js';

// Pendientes de la persona: lo que espera su decisión y los avisos sobre sus historias.
export const pendientesApi = Object.freeze({
  listar: ({ signal } = {}) => request('/pendientes', { signal }),
  marcarLeido: (avisoId) => request(`/pendientes/avisos/${encodeURIComponent(avisoId)}/leido`, { method: 'POST' }),
});
