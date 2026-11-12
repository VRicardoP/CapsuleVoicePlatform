import type { User, ApiResponse } from '../../types';
import { SECURITY_CONFIG } from './config';

// UUID generator compatible with non-secure contexts (HTTP)
export function generateRequestId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    try {
      return crypto.randomUUID();
    } catch {
      // Fall through to fallback
    }
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// ============================================================================
// RATE LIMITING
// ============================================================================

class RateLimiter {
  private requests: number[] = [];
  private maxRequests: number;
  private windowMs: number;

  constructor(maxRequests: number, windowMs: number = 60000) {
    this.maxRequests = maxRequests;
    this.windowMs = windowMs;
  }

  async checkLimit(): Promise<boolean> {
    const now = Date.now();
    this.requests = this.requests.filter(time => now - time < this.windowMs);
    if (this.requests.length >= this.maxRequests) {
      return false;
    }
    this.requests.push(now);
    return true;
  }

  getRemainingRequests(): number {
    const now = Date.now();
    this.requests = this.requests.filter(time => now - time < this.windowMs);
    return Math.max(0, this.maxRequests - this.requests.length);
  }
}

export const rateLimiter = new RateLimiter(SECURITY_CONFIG.MAX_REQUESTS_PER_MINUTE);

// ============================================================================
// UTILITIES
// ============================================================================

export async function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export function sanitizeInput(input: string): string {
  return input.replace(/[<>]/g, '').trim();
}

export function validateEmail(email: string): boolean {
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return emailRegex.test(email);
}

export function isValidUser(data: any): data is User {
  return (
    typeof data === 'object' &&
    typeof data.id === 'string' &&
    typeof data.name === 'string' &&
    typeof data.email === 'string' &&
    typeof data.company === 'string' &&
    typeof data.role === 'string'
  );
}

// ============================================================================
// SESSION EXPIRATION HANDLER
// ============================================================================

let onSessionExpired: (() => void) | null = null;

export function setSessionExpiredHandler(handler: (() => void) | null) {
  onSessionExpired = handler;
}

export function notifySessionExpired() {
  if (onSessionExpired) {
    onSessionExpired();
  }
}

// ============================================================================
// CSRF (double-submit token)
// ============================================================================

// Names mirror the backend's ``CSRF_COOKIE_NAME`` / ``CSRF_HEADER_NAME``.
const CSRF_HEADER = 'X-CSRF-Token';

/** Read the CSRF token cookie set by the backend on login. */
export function readCsrfToken(): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/(?:^|;\s*)capsulecorp_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/** Inject X-CSRF-Token header for mutator requests. No-op for GET/HEAD. */
export function withCsrfHeader(method: string | undefined, headers: HeadersInit): HeadersInit {
  const m = (method || 'GET').toUpperCase();
  if (m === 'GET' || m === 'HEAD' || m === 'OPTIONS') return headers;
  const token = readCsrfToken();
  if (!token) return headers;
  return { ...(headers as Record<string, string>), [CSRF_HEADER]: token };
}

// ============================================================================
// TOKEN REFRESH (DEPRECATED — BFF auto-refreshes server-side)
// ============================================================================

/** Returns 204 from the refresh shim. Kept as a no-op to preserve the
 *  retry-on-401 contract of older module clients. New code should not
 *  call this — a 401 means the session is genuinely expired and we
 *  should surface it via setSessionExpiredHandler. */
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

export async function refreshAccessToken(): Promise<boolean> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }
  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const response = await fetch(
        `${SECURITY_CONFIG.BASE_URL}${SECURITY_CONFIG.ENDPOINTS.REFRESH_TOKEN}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({}),
        },
      );
      // 204 (BFF healthy) and 200 (legacy still alive) both count as success.
      return response.ok || response.status === 204;
    } catch {
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

// ============================================================================
// SECURE HTTP CLIENT
// ============================================================================

export async function secureHttpClient<T>(
  endpoint: string,
  options: RequestInit = {},
  isRetry: boolean = false
): Promise<ApiResponse<T>> {
  if (!(await rateLimiter.checkLimit())) {
    return {
      success: false,
      data: null as any,
      error: 'Demasiadas solicitudes. Por favor, espere un momento.',
    };
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), SECURITY_CONFIG.REQUEST_TIMEOUT);

    const baseHeaders: HeadersInit = {
      'Content-Type': 'application/json',
      'X-Client-Version': '3.0.0',
      'X-Request-ID': generateRequestId(),
      ...(options.headers as Record<string, string>),
    };
    const headers = withCsrfHeader(options.method, baseHeaders);

    const response = await fetch(`${SECURITY_CONFIG.BASE_URL}${endpoint}`, {
      ...options,
      headers,
      credentials: 'include',
      signal: controller.signal,
      mode: 'cors',
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status === 401) {
        const isAuthEndpoint = endpoint.startsWith('/auth/');
        if (!isRetry && !isAuthEndpoint) {
          const refreshed = await refreshAccessToken();
          if (refreshed) {
            return secureHttpClient<T>(endpoint, options, true);
          }
        }
        notifySessionExpired();
        throw new Error('Sesión expirada. Por favor, inicie sesión nuevamente.');
      }
      if (response.status === 403) {
        throw new Error('No tiene permisos para acceder a este recurso.');
      }
      if (response.status === 429) {
        throw new Error('Demasiadas solicitudes. Por favor, intente más tarde.');
      }
      if (response.status >= 500) {
        throw new Error('Error del servidor. Por favor, intente más tarde.');
      }
      throw new Error(`Error HTTP ${response.status}`);
    }

    const data = await response.json();
    if (!data || typeof data !== 'object') {
      throw new Error('Respuesta inválida del servidor');
    }

    return { success: true, data: data as T };
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        return {
          success: false,
          data: null as any,
          error: 'La solicitud tardó demasiado tiempo. Por favor, intente nuevamente.',
        };
      }
      return { success: false, data: null as any, error: error.message };
    }
    return { success: false, data: null as any, error: 'Error desconocido' };
  }
}

// ============================================================================
// SECURE BLOB FETCH (for PDF/file downloads)
// ============================================================================

export async function secureBlobFetch(
  endpoint: string,
  options: { accept?: string; timeoutMultiplier?: number } = {}
): Promise<ApiResponse<Blob>> {
  if (!(await rateLimiter.checkLimit())) {
    return {
      success: false,
      data: null as unknown as Blob,
      error: 'Demasiadas solicitudes. Por favor, espere un momento.',
    };
  }

  try {
    const controller = new AbortController();
    const timeout = SECURITY_CONFIG.REQUEST_TIMEOUT * (options.timeoutMultiplier || 1);
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const response = await fetch(`${SECURITY_CONFIG.BASE_URL}${endpoint}`, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': options.accept || 'application/octet-stream',
        'X-Client-Version': '3.0.0',
        'X-Request-ID': generateRequestId(),
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status === 401) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          return secureBlobFetch(endpoint, options);
        }
        notifySessionExpired();
        throw new Error('Sesión expirada. Por favor, inicie sesión nuevamente.');
      }
      throw new Error(`Error HTTP ${response.status}`);
    }

    const blob = await response.blob();
    return { success: true, data: blob };
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        return {
          success: false,
          data: null as unknown as Blob,
          error: 'La solicitud tardó demasiado tiempo. Por favor, intente nuevamente.',
        };
      }
      return { success: false, data: null as unknown as Blob, error: error.message };
    }
    return { success: false, data: null as unknown as Blob, error: 'Error desconocido' };
  }
}
