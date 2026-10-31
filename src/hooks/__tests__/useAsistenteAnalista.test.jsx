import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { analystApi } from '../../services/analystApi.js';
import { useAsistenteAnalista } from '../useAsistenteAnalista.js';

vi.mock('../../services/analystApi.js', () => ({
  analystApi: {
    getHealth: vi.fn(),
    createConversation: vi.fn(),
    sendMessage: vi.fn(),
    cancelTurn: vi.fn(),
    resetConversation: vi.fn(),
    deleteConversation: vi.fn(),
  },
}));

describe('useAsistenteAnalista turn timeout', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    analystApi.getHealth.mockResolvedValue({ status: 'ready', timeout_seconds: 1 });
    analystApi.createConversation.mockResolvedValue({
      conversation_id: '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f',
    });
    analystApi.cancelTurn.mockResolvedValue({ canceled: true });
  });

  afterEach(() => vi.useRealTimers());

  it('cancels the server turn and records a retryable failed message when the 90-second deadline elapses', async () => {
    let requestSignal;
    analystApi.sendMessage.mockImplementation((_conversationId, _payload, { signal }) => {
      requestSignal = signal;
      return new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
      });
    });

    const { result } = renderHook(() => useAsistenteAnalista());
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    let sendPromise;
    act(() => {
      sendPromise = result.current.sendMessage('Check the timeout behavior');
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(analystApi.sendMessage).toHaveBeenCalledOnce();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(requestSignal.aborted).toBe(true);
    expect(analystApi.cancelTurn).toHaveBeenCalledWith(
      '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f',
      expect.any(String),
      { keepalive: true },
    );
    expect(result.current.isProcessing).toBe(false);
    expect(result.current.draft).toBe('');
    expect(result.current.generationStatus).toBe('timeout');
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0]).toMatchObject({ status: 'failed', errorCode: 'TURN_TIMEOUT' });
    expect(result.current.error).toMatch(/tardó demasiado/i);
    await act(async () => { await sendPromise; });
  });

  it('abre otra conversación y reintenta una vez cuando el servidor olvidó la anterior', async () => {
    analystApi.createConversation
      .mockResolvedValueOnce({ conversation_id: 'viejo' })
      .mockResolvedValueOnce({ conversation_id: 'nuevo' });
    analystApi.sendMessage
      .mockRejectedValueOnce(Object.assign(new Error('no existe'), { code: 'CONVERSATION_NOT_FOUND' }))
      .mockRejectedValueOnce(Object.assign(new Error('fin'), { code: 'TURN_CANCELLED' }));

    const { result } = renderHook(() => useAsistenteAnalista());
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    await act(async () => { await result.current.sendMessage('Hola'); });

    expect(analystApi.createConversation).toHaveBeenCalledTimes(2);
    expect(analystApi.sendMessage).toHaveBeenNthCalledWith(2, 'nuevo', expect.any(Object), expect.any(Object));
  });

  it('invalidates a pending request and sends a keepalive cancellation on pagehide', async () => {
    let requestSignal;
    analystApi.sendMessage.mockImplementation((_conversationId, _payload, { signal }) => {
      requestSignal = signal;
      return new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
      });
    });
    const { result } = renderHook(() => useAsistenteAnalista());
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    let sendPromise;
    act(() => {
      sendPromise = result.current.sendMessage('Leave this page');
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    await act(async () => {
      window.dispatchEvent(new Event('pagehide'));
      await Promise.resolve();
    });

    expect(requestSignal.aborted).toBe(true);
    expect(analystApi.cancelTurn).toHaveBeenCalledWith(
      '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f',
      expect.any(String),
      { keepalive: true },
    );
    await act(async () => { await sendPromise; });
  });
});
