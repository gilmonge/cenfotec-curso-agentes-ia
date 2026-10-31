import React from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { PanelAsistenteComponent } from '../PanelAsistenteComponent';
import { QUOTA_RECOVERY_UNKNOWN } from '../../../utils/quotaRecovery.js';

function renderQuotaFailure(retryAt, onRetry = vi.fn()) {
  render(<PanelAsistenteComponent
    open
    messages={[{
      id: 'user-message-1',
      role: 'user',
      text: 'Consulta que debe conservarse',
      status: 'failed',
      errorCode: 'OPENCODE_RATE_LIMITED',
      retryAt,
    }]}
    onRetry={onRetry}
    health={{ status: 'ready', checks: { opencode: { status: 'ok' } } }}
    backendConnection="connected"
  />);
  return onRetry;
}

describe('quota recovery notice lifecycle', () => {
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('shows only the explicit fallback when OpenCode provides no valid recovery time', () => {
    renderQuotaFailure(undefined);
    expect(screen.getByText(QUOTA_RECOVERY_UNKNOWN)).toBeInTheDocument();
    expect(screen.queryByText(/dentro de/)).not.toBeInTheDocument();
  });

  it('updates the countdown each second and clears its timer at zero without automatic retry', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-10-27T12:00:00.000Z'));
    const retryAt = new Date(Date.now() + 60_000).toISOString();
    const onRetry = renderQuotaFailure(retryAt);

    expect(screen.getByText(/dentro de 1 minuto/)).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(1000));
    expect(screen.getByText(/dentro de 59 segundos/)).toBeInTheDocument();
    expect(onRetry).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(1);

    act(() => vi.advanceTimersByTime(59_000));
    expect(screen.getByText(/El tiempo de recuperación informado por OpenCode ya se cumpl/)).toBeInTheDocument();
    expect(onRetry).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar este mensaje' }));
    expect(onRetry).toHaveBeenCalledOnce();
    expect(onRetry).toHaveBeenCalledWith('user-message-1');
  });

  it('clears an active interval when the message component unmounts', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-10-27T12:00:00.000Z'));
    const retryAt = new Date(Date.now() + 60_000).toISOString();
    const view = render(<PanelAsistenteComponent
      open
      messages={[{
        id: 'user-message-1',
        role: 'user',
        text: 'Consulta',
        status: 'failed',
        errorCode: 'OPENCODE_RATE_LIMITED',
        retryAt,
      }]}
      health={{ status: 'ready', checks: { opencode: { status: 'ok' } } }}
      backendConnection="connected"
    />);

    expect(vi.getTimerCount()).toBe(1);
    view.unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
