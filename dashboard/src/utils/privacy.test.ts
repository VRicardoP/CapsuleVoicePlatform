import { describe, it, expect } from 'vitest';
import {
  detectPII,
  anonymizeName,
  anonymizePhone,
  anonymizeEmail,
  redactPII,
  isConsentValid,
  getConsentDaysRemaining,
  hasRequiredRole,
  isValidEmail,
  isValidSpanishPhone,
  generateDisplayHash,
  sanitizeInput,
  PII_CATEGORY,
} from './privacy';

describe('detectPII', () => {
  it('detects email addresses', () => {
    const result = detectPII('Contact me at user@example.com');
    expect(result).toContain(PII_CATEGORY.EMAIL);
  });

  it('detects Spanish phone numbers', () => {
    const result = detectPII('Llama al 612345678');
    expect(result).toContain(PII_CATEGORY.PHONE);
  });

  it('detects Spanish DNI', () => {
    const result = detectPII('DNI: 12345678A');
    expect(result).toContain(PII_CATEGORY.ID_NUMBER);
  });

  it('returns empty for clean text', () => {
    expect(detectPII('Hello world')).toEqual([]);
  });
});

describe('anonymizeName', () => {
  it('partially anonymizes by default', () => {
    const result = anonymizeName('Juan Garcia');
    expect(result).toMatch(/^J\*+ G\*+$/);
  });

  it('fully anonymizes in full mode', () => {
    expect(anonymizeName('Juan Garcia', 'full')).toBe('*** DATOS PROTEGIDOS ***');
  });
});

describe('anonymizePhone', () => {
  it('masks all but last 3 digits', () => {
    const result = anonymizePhone('612345678');
    expect(result).toMatch(/\*+678$/);
  });

  it('handles short numbers', () => {
    expect(anonymizePhone('12')).toBe('**');
  });
});

describe('anonymizeEmail', () => {
  it('masks local part keeping first and last char', () => {
    const result = anonymizeEmail('usuario@example.com');
    expect(result).toMatch(/^u\*+o@example\.com$/);
  });

  it('handles missing domain', () => {
    expect(anonymizeEmail('nodomain')).toBe('***@***');
  });
});

describe('redactPII', () => {
  it('redacts emails in text', () => {
    const result = redactPII('Send to user@test.com please');
    expect(result).toContain('[EMAIL REDACTADO]');
    expect(result).not.toContain('user@test.com');
  });

  it('redacts phone numbers', () => {
    const result = redactPII('Llama al 612345678');
    expect(result).toContain('[TELÉFONO REDACTADO]');
  });

  it('redacts DNI', () => {
    const result = redactPII('Su DNI es 12345678A');
    expect(result).toContain('[DNI/NIE REDACTADO]');
    expect(result).not.toContain('12345678A');
  });
});

describe('isConsentValid', () => {
  it('returns false for null consent', () => {
    expect(isConsentValid(null)).toBe(false);
    expect(isConsentValid(undefined)).toBe(false);
  });

  it('returns true for active consent', () => {
    expect(isConsentValid({
      given: true,
      revokedAt: null,
      expiresAt: null,
    } as Parameters<typeof isConsentValid>[0])).toBe(true);
  });

  it('returns false for revoked consent', () => {
    expect(isConsentValid({
      given: true,
      revokedAt: '2024-01-01',
    } as Parameters<typeof isConsentValid>[0])).toBe(false);
  });

  it('returns false for expired consent', () => {
    expect(isConsentValid({
      given: true,
      revokedAt: null,
      expiresAt: '2020-01-01T00:00:00Z',
    } as Parameters<typeof isConsentValid>[0])).toBe(false);
  });
});

describe('getConsentDaysRemaining', () => {
  it('returns null for consent without expiry', () => {
    expect(getConsentDaysRemaining({
      given: true,
      expiresAt: null,
    } as Parameters<typeof getConsentDaysRemaining>[0])).toBeNull();
  });

  it('returns 0 for expired consent', () => {
    expect(getConsentDaysRemaining({
      given: true,
      revokedAt: null,
      expiresAt: '2020-01-01T00:00:00Z',
    } as Parameters<typeof getConsentDaysRemaining>[0])).toBe(0);
  });
});

describe('hasRequiredRole', () => {
  it('admin has access to everything', () => {
    expect(hasRequiredRole('admin', 'viewer')).toBe(true);
    expect(hasRequiredRole('admin', 'user')).toBe(true);
    expect(hasRequiredRole('admin', 'admin')).toBe(true);
  });

  it('viewer cannot access admin features', () => {
    expect(hasRequiredRole('viewer', 'admin')).toBe(false);
  });

  it('user has access to viewer features', () => {
    expect(hasRequiredRole('user', 'viewer')).toBe(true);
  });
});

describe('isValidEmail', () => {
  it('validates correct emails', () => {
    expect(isValidEmail('test@example.com')).toBe(true);
  });

  it('rejects invalid emails', () => {
    expect(isValidEmail('not-email')).toBe(false);
    expect(isValidEmail('')).toBe(false);
  });
});

describe('isValidSpanishPhone', () => {
  it('accepts valid Spanish mobile', () => {
    expect(isValidSpanishPhone('612345678')).toBe(true);
    expect(isValidSpanishPhone('+34612345678')).toBe(true);
  });

  it('rejects non-Spanish numbers', () => {
    expect(isValidSpanishPhone('123456789')).toBe(false);
  });
});

describe('generateDisplayHash', () => {
  it('returns 8-char uppercase hex string', () => {
    const hash = generateDisplayHash('test-input');
    expect(hash).toMatch(/^[0-9A-F]{8}$/);
  });

  it('is deterministic', () => {
    expect(generateDisplayHash('same')).toBe(generateDisplayHash('same'));
  });

  it('returns different hashes for different inputs', () => {
    expect(generateDisplayHash('abc')).not.toBe(generateDisplayHash('def'));
  });
});

describe('sanitizeInput', () => {
  it('escapes HTML entities', () => {
    const result = sanitizeInput('<script>alert("xss")</script>');
    expect(result).not.toContain('<');
    expect(result).not.toContain('>');
    expect(result).toContain('&lt;');
    expect(result).toContain('&gt;');
  });

  it('escapes quotes', () => {
    const result = sanitizeInput('"hello"');
    expect(result).toContain('&quot;');
  });
});
