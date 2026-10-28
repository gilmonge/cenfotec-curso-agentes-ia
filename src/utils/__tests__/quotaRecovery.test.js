import { describe, expect, it } from 'vitest';
import {
  QUOTA_RECOVERY_ELAPSED,
  QUOTA_RECOVERY_UNKNOWN,
  formatQuotaDuration,
  quotaRecoveryMessage,
  quotaRemainingSeconds,
} from '../quotaRecovery.js';

describe('quota recovery formatting', () => {
  it.each([
    [1, '1 segundo'],
    [59, '59 segundos'],
    [60, '1 minuto'],
    [90, '2 minutos'],
    [3600, '1 hora'],
    [3661, '1 hora y 2 minutos'],
    [7199, '2 horas'],
  ])('formats %i remaining seconds as %s', (seconds, expected) => {
    expect(formatQuotaDuration(seconds)).toBe(expected);
  });

  it('converts a future recovery instant to a ceil-rounded second count', () => {
    const now = Date.UTC(2026, 9, 27, 12, 0);
    expect(quotaRemainingSeconds(new Date(now + 1999).toISOString(), now)).toBe(2);
    expect(quotaRemainingSeconds(new Date(now + 60_000).toISOString(), now)).toBe(60);
    expect(quotaRemainingSeconds(new Date(now + 3_600_000).toISOString(), now)).toBe(3600);
  });

  it.each([undefined, null, 'not-a-date', '123'])('does not invent a countdown for %s', (retryAt) => {
    expect(quotaRecoveryMessage(retryAt, Date.UTC(2026, 9, 27, 12, 0))).toBe(QUOTA_RECOVERY_UNKNOWN);
  });

  it('reports when a previously informed instant has elapsed', () => {
    const now = Date.UTC(2026, 9, 27, 12, 0);
    expect(quotaRecoveryMessage(new Date(now).toISOString(), now)).toBe(QUOTA_RECOVERY_ELAPSED);
    expect(quotaRecoveryMessage(new Date(now - 1).toISOString(), now)).toBe(QUOTA_RECOVERY_ELAPSED);
  });
});
