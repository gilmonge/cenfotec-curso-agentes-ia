import { describe, expect, it } from 'vitest';
import { analystErrorMessage } from '../utils/analystErrors';
import { AnalystApiError } from '../services/analystApi.js';

describe('analystErrorMessage', () => {
  it('explains an OpenCode quota response without suggesting a provider fallback', () => {
    expect(analystErrorMessage({ code: 'OPENCODE_RATE_LIMITED' })).toMatch(/Cuota agotada/);
  });

  it('explains when the configured model is not available', () => {
    expect(analystErrorMessage({ code: 'MODEL_UNAVAILABLE' })).toMatch(/OPENCODE_MODEL_ID/);
  });

  it('explains authentication errors without exposing upstream details', () => {
    expect(analystErrorMessage({ code: 'OPENCODE_AUTH_FAILED' })).toMatch(/autenticaci/);
  });

  it('keeps the safe timeout message for HTTP 504', () => {
    expect(analystErrorMessage({ code: 'TURN_TIMEOUT' })).toMatch(/tardó demasiado/);
  });
});

describe('AnalystApiError', () => {
  it('maps the normalized retry_at field without exposing other upstream details', () => {
    const error = new AnalystApiError(503, { error: {
      code: 'OPENCODE_RATE_LIMITED',
      message: 'OpenCode agotó la cuota disponible del proveedor.',
      retryable: true,
      retry_at: '2026-10-27T12:08:00Z',
    } });

    expect(error.retryAt).toBe('2026-10-27T12:08:00Z');
    expect(error.code).toBe('OPENCODE_RATE_LIMITED');
    expect(error.status).toBe(503);
  });
});
