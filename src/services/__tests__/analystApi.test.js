import { afterEach, describe, expect, it, vi } from 'vitest';
import { AnalystApiError, analystApi } from '../analystApi.js';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('analystApi', () => {
  it('requests health through the same-origin proxy without credentials or storage', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'degraded' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const before = Object.keys(localStorage);

    await expect(analystApi.getHealth()).resolves.toEqual({ status: 'degraded' });
    expect(fetchMock).toHaveBeenCalledWith('/api/analista/health', expect.objectContaining({
      credentials: 'omit',
      cache: 'no-store',
    }));
    expect(Object.keys(localStorage)).toEqual(before);
  });

  it('sends only request identity and message to the backend conversation route', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ estado: 'completado' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const payload = { request_id: '9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d', message: 'Consulta sintética' };

    await analystApi.sendMessage('3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f', payload);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/analista/conversaciones/3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f/mensajes',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(payload), credentials: 'omit' }),
    );
  });

  it('translates REST envelopes into a typed API error without exposing internals', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { code: 'TURN_IN_PROGRESS', message: 'Ya hay un turno en proceso.', retryable: false },
    }), { status: 409 })));

    await expect(analystApi.getHealth()).rejects.toMatchObject({
      name: 'AnalystApiError',
      status: 409,
      code: 'TURN_IN_PROGRESS',
      retryable: false,
    });
    expect(AnalystApiError).toBeDefined();
  });

  it('returns null for a successful 204 delete response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    await expect(analystApi.deleteConversation('conversation-id')).resolves.toBeNull();
  });

  it('marks pagehide cancellation requests as keepalive', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ canceled: true }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await analystApi.cancelTurn('conversation-id', 'request-id', { keepalive: true });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/analista/conversaciones/conversation-id/cancelar',
      expect.objectContaining({ keepalive: true, credentials: 'omit' }),
    );
  });
});
