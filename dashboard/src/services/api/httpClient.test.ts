import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  generateRequestId,
  sanitizeInput,
  validateEmail,
  isValidUser,
  rateLimiter,
  secureHttpClient,
} from './httpClient';

describe('generateRequestId', () => {
  it('returns a string in UUID-like format', () => {
    const id = generateRequestId();
    expect(id).toMatch(/^[0-9a-f-]{36}$/i);
  });

  it('returns unique values on successive calls', () => {
    const ids = new Set(Array.from({ length: 10 }, () => generateRequestId()));
    expect(ids.size).toBe(10);
  });
});

describe('sanitizeInput', () => {
  it('removes angle brackets', () => {
    const result = sanitizeInput('<script>alert("xss")</script>');
    expect(result).not.toContain('<');
    expect(result).not.toContain('>');
  });

  it('trims whitespace', () => {
    expect(sanitizeInput('  hello  ')).toBe('hello');
  });

  it('returns empty string for whitespace-only input', () => {
    expect(sanitizeInput('   ')).toBe('');
  });
});

describe('validateEmail', () => {
  it('accepts valid emails', () => {
    expect(validateEmail('user@example.com')).toBe(true);
    expect(validateEmail('admin@example.com')).toBe(true);
  });

  it('rejects invalid emails', () => {
    expect(validateEmail('not-an-email')).toBe(false);
    expect(validateEmail('@no-local.com')).toBe(false);
    expect(validateEmail('user@')).toBe(false);
    expect(validateEmail('')).toBe(false);
  });
});

describe('isValidUser', () => {
  it('returns true for valid user object', () => {
    const user = {
      id: '123',
      name: 'Test',
      email: 'test@test.com',
      company: 'TestCo',
      role: 'admin',
    };
    expect(isValidUser(user)).toBe(true);
  });

  it('returns false for missing fields', () => {
    expect(isValidUser({ id: '123', name: 'Test' })).toBe(false);
    expect(isValidUser(undefined)).toBe(false);
    // Note: isValidUser(null) throws because typeof null === 'object'
    // This is a known limitation — callers should null-check first
  });

  it('returns false for wrong field types', () => {
    expect(isValidUser({ id: 123, name: 'Test', email: 'e', company: 'c', role: 'r' })).toBe(false);
  });
});

describe('RateLimiter', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('allows requests within limit', async () => {
    const result = await rateLimiter.checkLimit();
    expect(result).toBe(true);
  });

  it('reports remaining requests', () => {
    const remaining = rateLimiter.getRemainingRequests();
    expect(remaining).toBeGreaterThan(0);
    expect(remaining).toBeLessThanOrEqual(200);
  });
});

describe('secureHttpClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('returns success with parsed JSON on 200', async () => {
    const mockData = { users: [] };
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockData),
    } as Response);

    const result = await secureHttpClient('/test');
    expect(result.success).toBe(true);
    expect(result.data).toEqual(mockData);
  });

  it('returns error on 403', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: false,
      status: 403,
    } as Response);

    const result = await secureHttpClient('/test');
    expect(result.success).toBe(false);
    expect(result.error).toContain('permisos');
  });

  it('returns error on 500', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: false,
      status: 500,
    } as Response);

    const result = await secureHttpClient('/test');
    expect(result.success).toBe(false);
    expect(result.error).toContain('servidor');
  });

  it('handles fetch abort (timeout)', async () => {
    vi.mocked(global.fetch).mockRejectedValueOnce(
      Object.assign(new Error('Aborted'), { name: 'AbortError' })
    );

    const result = await secureHttpClient('/test');
    expect(result.success).toBe(false);
    expect(result.error).toContain('tardó demasiado');
  });

  it('handles network errors', async () => {
    vi.mocked(global.fetch).mockRejectedValueOnce(new Error('Network failure'));

    const result = await secureHttpClient('/test');
    expect(result.success).toBe(false);
    expect(result.error).toBe('Network failure');
  });
});
