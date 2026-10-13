import { describe, it, expect, vi, beforeEach } from 'vitest';
import { authApi } from './authApi';

describe('authApi.login', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('rejects invalid email format', async () => {
    const result = await authApi.login('not-email', 'password123');
    expect(result.success).toBe(false);
    expect(result.error).toContain('Email');
  });

  it('rejects short password', async () => {
    const result = await authApi.login('user@example.com', 'short');
    expect(result.success).toBe(false);
    expect(result.error).toContain('8 caracteres');
  });

  it('calls API with sanitized email on valid input', async () => {
    const mockUser = {
      id: '550e8400-e29b-41d4-a716-446655440000',
      name: 'Test User',
      email: 'test@example.com',
      company: 'TestCo',
      role: 'admin',
    };

    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ user: mockUser, expiresIn: 1800 }),
    } as Response);

    const result = await authApi.login('test@example.com', 'password123');
    expect(result.success).toBe(true);
    expect(result.data).toEqual(mockUser);
  });

  it('rejects server response with invalid user shape', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ user: { id: 123 }, expiresIn: 1800 }),
    } as Response);

    const result = await authApi.login('test@example.com', 'password123');
    expect(result.success).toBe(false);
    expect(result.error).toContain('inválida');
  });
});

describe('authApi.logout', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('calls logout endpoint', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    } as Response);

    const result = await authApi.logout();
    expect(result.success).toBe(true);
  });
});
