import { useMemo } from 'react';
import { useAuthorization } from '../context/AuthorizationContext';
import {
  canAccessPII,
  maskEmail,
  maskName,
  maskPhone,
} from '../utils/pii';

/**
 * Hook ergonomic façade over `utils/pii.ts`.
 *
 * Reads the role from `useAuthorization()` and returns:
 * - `canAccessPII`: boolean (true if the user can see PII unmasked)
 * - `maskName(name)` / `maskPhone(phone)` / `maskEmail(email)`:
 *   either the original value (PII allowed) or an anonymized version.
 *
 * Replaces the legacy `useRBAC` hook for PII concerns. Other concerns of
 * the old hook (consent management, audit logs, WhatsApp roles) should
 * use `useAuthorization().hasPermission(...)` directly.
 */
export const usePiiAccess = () => {
  const { role } = useAuthorization();

  return useMemo(() => {
    const allowed = canAccessPII(role);
    return {
      canAccessPII: allowed,
      maskName: (name: string) => maskName(name, allowed),
      maskPhone: (phone: string) => maskPhone(phone, allowed),
      maskEmail: (email: string) => maskEmail(email, allowed),
    };
  }, [role]);
};
