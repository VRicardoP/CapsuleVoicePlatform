/**
 * PII access + masking utilities.
 *
 * Replaces the legacy `useRBAC.ts` hook (which was tied to the obsolete role
 * names `admin` / `viewer` / `auditor`). Now driven by the role string from
 * the new permission system (`superadmin`, `client_admin`, `user`).
 *
 * Pure functions only — UI integration lives in `hooks/usePiiAccess.ts`.
 */

const PII_ELIGIBLE_ROLES = new Set([
  // New permission system
  'superadmin',
  'client_admin',
  'user',
  // Legacy roles kept for back-compat with any cached sessions
  'admin',
]);

/** Returns true if the given role is allowed to see PII unmasked. */
export function canAccessPII(role: string | null | undefined): boolean {
  if (!role) return false;
  return PII_ELIGIBLE_ROLES.has(role);
}

/**
 * Anonymize a person's name. Each space-separated part is reduced to its
 * initial followed by ``***``. If ``unmask`` is true, returns the name
 * unchanged.
 */
export function maskName(name: string, unmask: boolean): string {
  if (unmask || !name) return name;
  return name
    .split(' ')
    .map((part) => (part.length > 0 ? `${part.charAt(0)}***` : ''))
    .join(' ');
}

/**
 * Anonymize a phone number, leaving only the last 3 digits visible.
 * Non-digit characters in the prefix become ``*``.
 */
export function maskPhone(phone: string, unmask: boolean): string {
  if (unmask || !phone) return phone;
  if (phone.length <= 3) return phone;
  return phone.slice(0, -3).replace(/\d/g, '*') + phone.slice(-3);
}

/** Anonymize an email: keep first and last char of the local part. */
export function maskEmail(email: string, unmask: boolean): string {
  if (unmask || !email) return email;
  const [local, domain] = email.split('@');
  if (!local || !domain) return email;
  if (local.length <= 2) return `${local.charAt(0)}***@${domain}`;
  const masked = `${local.charAt(0)}***${local.charAt(local.length - 1)}`;
  return `${masked}@${domain}`;
}
