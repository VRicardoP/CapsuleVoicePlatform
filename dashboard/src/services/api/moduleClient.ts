/**
 * Shared HTTP client factory for feature modules.
 *
 * Each module (whatsapp, outbound, newsletter) used to have an identical
 * copy of request/voidRequest/jsonPost/jsonPatch/qs helpers. This factory
 * eliminates that duplication — call `createModuleClient(base)` once per
 * module and re-export the returned helpers.
 *
 * BFF (Phase 1) changes:
 * - Adds `X-CSRF-Token` header for mutator methods (double-submit cookie).
 * - When a 401 retry fails (or refresh shim returns non-OK), notifies the
 *   global session-expired handler so the app can route to the login
 *   screen instead of leaving the UI in a broken state. Fixes the bug
 *   where module-level requests would silently throw on session expiry.
 */
import { refreshAccessToken, withCsrfHeader, notifySessionExpired } from './httpClient';
import { SECURITY_CONFIG } from './config';

/** Resolve module base URL using VITE_API_URL when available. */
function resolveBase(path: string): string {
  const apiUrl = SECURITY_CONFIG.BASE_URL; // reads VITE_API_URL || '/api/v1'
  // path is like '/api/v1/newsletter' — strip the '/api/v1' prefix if apiUrl already contains it
  if (apiUrl !== '/api/v1' && path.startsWith('/api/v1')) {
    return `${apiUrl}${path.slice('/api/v1'.length)}`;
  }
  return path;
}

export interface ModuleClient {
  /** JSON-returning request with automatic 401 retry. */
  request: <T>(url: string, options?: RequestInit, isRetry?: boolean) => Promise<T>;
  /** Non-JSON request (e.g. DELETE) with automatic 401 retry. */
  voidRequest: (url: string, options?: RequestInit, isRetry?: boolean) => Promise<Response>;
  /** Build RequestInit for a JSON POST. */
  jsonPost: (data: unknown) => RequestInit;
  /** Build RequestInit for a JSON PATCH. */
  jsonPatch: (data: unknown) => RequestInit;
  /** Build a query-string from a params object, filtering nullish/empty values. */
  qs: (params: Record<string, string | number | boolean | undefined | null>) => string;
  /** The base URL prefix (e.g. "/api/v1/whatsapp"). */
  BASE: string;
}

export function createModuleClient(base: string): ModuleClient {
  /** Apply CSRF header for mutator methods. */
  function withHeaders(options?: RequestInit): RequestInit {
    if (!options) return { credentials: 'include' };
    return {
      ...options,
      credentials: 'include',
      headers: withCsrfHeader(options.method, options.headers ?? {}),
    };
  }

  /** Re-auth-required is a separate signal (session is OK, but the user
   *  must re-prove credentials). We rethrow with a typed marker so the
   *  caller can show the password modal instead of going to login. */
  function isReauthRequired(response: Response): boolean {
    return (
      response.status === 401 &&
      (response.headers.get('x-reauth-code') === 'REAUTH_REQUIRED' ||
        response.headers.get('www-authenticate')?.includes('re-auth-required') === true)
    );
  }

  async function request<T>(url: string, options?: RequestInit, isRetry = false): Promise<T> {
    const response = await fetch(url, withHeaders(options));
    if (!response.ok) {
      if (response.status === 401) {
        if (isReauthRequired(response)) {
          const err = new Error('Re-authentication required');
          (err as any).code = 'REAUTH_REQUIRED';
          throw err;
        }
        if (!isRetry) {
          const refreshed = await refreshAccessToken();
          if (refreshed) return request<T>(url, options, true);
        }
        notifySessionExpired();
        throw new Error('Sesión expirada. Inicie sesión nuevamente.');
      }
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'Request failed');
    }
    return response.json();
  }

  async function voidRequest(url: string, options?: RequestInit, isRetry = false): Promise<Response> {
    const response = await fetch(url, withHeaders(options));
    if (!response.ok) {
      if (response.status === 401) {
        if (isReauthRequired(response)) {
          const err = new Error('Re-authentication required');
          (err as any).code = 'REAUTH_REQUIRED';
          throw err;
        }
        if (!isRetry) {
          const refreshed = await refreshAccessToken();
          if (refreshed) return voidRequest(url, options, true);
        }
        notifySessionExpired();
        throw new Error('Sesión expirada. Inicie sesión nuevamente.');
      }
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'Request failed');
    }
    return response;
  }

  function jsonPost(data: unknown): RequestInit {
    return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) };
  }

  function jsonPatch(data: unknown): RequestInit {
    return { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) };
  }

  function qs(params: Record<string, string | number | boolean | undefined | null>): string {
    const sp = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v != null && v !== '') sp.set(k, String(v));
    }
    const s = sp.toString();
    return s ? `?${s}` : '';
  }

  return { request, voidRequest, jsonPost, jsonPatch, qs, BASE: resolveBase(base) };
}
