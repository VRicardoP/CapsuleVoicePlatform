import { describe, it, expect } from 'vitest';
import { SECURITY_CONFIG } from './config';

describe('SECURITY_CONFIG', () => {
  it('has required endpoint definitions', () => {
    expect(SECURITY_CONFIG.ENDPOINTS.LOGIN).toBe('/auth/login');
    expect(SECURITY_CONFIG.ENDPOINTS.LOGOUT).toBe('/auth/logout');
    expect(SECURITY_CONFIG.ENDPOINTS.REFRESH_TOKEN).toBe('/auth/refresh');
    expect(SECURITY_CONFIG.ENDPOINTS.DASHBOARD).toBe('/dashboard');
    expect(SECURITY_CONFIG.ENDPOINTS.CALLS).toBe('/calls');
  });

  it('has reasonable defaults', () => {
    expect(SECURITY_CONFIG.MAX_REQUESTS_PER_MINUTE).toBeGreaterThan(0);
    expect(SECURITY_CONFIG.REQUEST_TIMEOUT).toBeGreaterThanOrEqual(5000);
  });

  it('BASE_URL contains /api/v1', () => {
    expect(typeof SECURITY_CONFIG.BASE_URL).toBe('string');
    expect(SECURITY_CONFIG.BASE_URL).toContain('/api/v1');
  });
});
