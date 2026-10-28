const API_BASE = '/api/analista';

export class AnalystApiError extends Error {
  constructor(status, payload = {}) {
    const detail = payload?.error ?? {};
    super(typeof detail.message === 'string' ? detail.message : 'No fue posible completar la solicitud.');
    this.name = 'AnalystApiError';
    this.status = status;
    this.code = typeof detail.code === 'string' ? detail.code : 'NETWORK_ERROR';
    this.retryable = Boolean(detail.retryable);
    this.requestId = typeof detail.request_id === 'string' ? detail.request_id : undefined;
    this.retryAt = typeof detail.retry_at === 'string' ? detail.retry_at : undefined;
  }
}

async function request(path, { method = 'GET', body, signal, keepalive = false } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body === undefined ? { Accept: 'application/json' } : {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'omit',
      cache: 'no-store',
      keepalive,
      signal,
    });
  } catch (cause) {
    const error = new AnalystApiError(0);
    error.cause = cause;
    error.code = 'NETWORK_ERROR';
    error.retryable = true;
    throw error;
  }

  if (response.status === 204) return null;

  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  if (!response.ok) throw new AnalystApiError(response.status, payload);
  return payload;
}

export const analystApi = Object.freeze({
  getHealth: ({ signal } = {}) => request('/health', { signal }),
  createConversation: ({ signal } = {}) => request('/conversaciones', { method: 'POST', signal }),
  sendMessage: (conversationId, payload, { signal } = {}) => request(
    `/conversaciones/${encodeURIComponent(conversationId)}/mensajes`,
    { method: 'POST', body: payload, signal },
  ),
  cancelTurn: (conversationId, requestId, { keepalive = false } = {}) => request(
    `/conversaciones/${encodeURIComponent(conversationId)}/cancelar`,
    { method: 'POST', body: { request_id: requestId }, keepalive },
  ),
  resetConversation: (conversationId) => request(
    `/conversaciones/${encodeURIComponent(conversationId)}/reiniciar`,
    { method: 'POST' },
  ),
  deleteConversation: (conversationId) => request(
    `/conversaciones/${encodeURIComponent(conversationId)}`,
    { method: 'DELETE' },
  ),
});
