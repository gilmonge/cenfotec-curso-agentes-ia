import { avisarSesionVencida, encabezadoSesion } from '../utils/sesion.js';
const API_BASE = '/api/workflows';

const STATUS_MESSAGES = Object.freeze({
  400: 'La respuesta no coincide con la intervención humana pendiente. Revise los datos y vuelva a intentarlo.',
  404: 'No se encontró el flujo. Puede que se haya descartado; revise la lista de HU en proceso o inicie uno nuevo.',
  409: 'El flujo está ocupado o ya no espera esta decisión. Actualice su estado antes de volver a enviar.',
  422: 'La respuesta no cumple el contrato del flujo. Revise los campos e inténtelo de nuevo.',
  503: 'Un servicio necesario no está disponible. El flujo no avanzó; puede reintentar cuando el servicio vuelva.',
  500: 'Ocurrió un error inesperado. El avance anterior quedó guardado: consulte el estado del flujo.',
  504: 'El flujo tardó demasiado y su resultado está incompleto. Consulte su estado antes de repetir la decisión.',
});

export class WorkflowApiError extends Error {
  constructor(status, payload = {}, { path = '', method = 'GET' } = {}) {
    const detail = payload?.error ?? {};
    const safeMessage = status === 404 && method === 'POST' && path === ''
      ? 'El endpoint de workflows no está disponible en este backend. Puede continuar con el flujo manual.'
      : STATUS_MESSAGES[status];
    super(safeMessage ?? (typeof detail.message === 'string'
      ? detail.message
      : 'No fue posible completar la solicitud del flujo.'));
    this.name = 'WorkflowApiError';
    this.status = status;
    this.code = typeof detail.code === 'string' ? detail.code : 'NETWORK_ERROR';
    this.retryable = Boolean(detail.retryable);
    this.requestId = typeof detail.request_id === 'string' ? detail.request_id : undefined;
  }
}

async function request(path, { method = 'GET', body, signal } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body === undefined ? { Accept: 'application/json', ...encabezadoSesion() } : {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...encabezadoSesion(),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin',
      cache: 'no-store',
      signal,
    });
  } catch (cause) {
    if (cause?.name === 'AbortError') throw cause;
    const error = new WorkflowApiError(0);
    error.cause = cause;
    error.code = 'NETWORK_ERROR';
    error.retryable = true;
    throw error;
  }

  let payload;
  try {
    payload = response.status === 204 ? null : await response.json();
  } catch {
    payload = {};
  }
  avisarSesionVencida(response.status);
  if (!response.ok) throw new WorkflowApiError(response.status, payload, { path, method });
  return payload;
}

export const startWorkflow = (body, { signal } = {}) => request('', { method: 'POST', body, signal });
export const getWorkflow = (workflowId, { signal } = {}) => request(`/${encodeURIComponent(workflowId)}`, { signal });
export const resumeWorkflow = (workflowId, body, { signal } = {}) => request(
  `/${encodeURIComponent(workflowId)}/resume`, { method: 'POST', body, signal },
);

export const listWorkflows = ({ signal } = {}) => request('', { signal });
export const deleteWorkflow = (workflowId, { signal } = {}) => request(
  `/${encodeURIComponent(workflowId)}`, { method: 'DELETE', signal },
);
export const saveWorkflowDraft = (workflowId, respuestas, { signal } = {}) => request(
  `/${encodeURIComponent(workflowId)}/borrador`, { method: 'PUT', body: { respuestas }, signal },
);
export const retryWorkflow = (workflowId, { signal } = {}) => request(
  `/${encodeURIComponent(workflowId)}/reintentar`, { method: 'POST', signal },
);

export const workflowApi = Object.freeze({
  startWorkflow, getWorkflow, resumeWorkflow, listWorkflows, deleteWorkflow, saveWorkflowDraft, retryWorkflow,
});
