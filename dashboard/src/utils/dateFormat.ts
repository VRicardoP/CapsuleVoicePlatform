/**
 * Centralized date/time formatting for SferaAI.
 *
 * Conventions:
 * - Dates: dd/mm/yyyy (es-ES)
 * - Times: 24h format (HH:mm)
 * - All formatting uses Europe/Madrid timezone awareness
 */

const LOCALE = 'es-ES';

/** Format a date as dd/mm/yyyy */
export function formatDate(input: string | Date | null | undefined): string {
  if (!input) return '-';
  const d = typeof input === 'string' ? new Date(input) : input;
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleDateString(LOCALE, { day: '2-digit', month: '2-digit', year: 'numeric' });
}

/** Format a date as "23 mar 2026" (short month) */
export function formatDateShort(input: string | Date | null | undefined): string {
  if (!input) return '-';
  const d = typeof input === 'string' ? new Date(input) : input;
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleDateString(LOCALE, { day: '2-digit', month: 'short', year: 'numeric' });
}

/** Format time as HH:mm (24h) */
export function formatTime(input: string | Date | null | undefined): string {
  if (!input) return '-';
  const d = typeof input === 'string' ? new Date(input) : input;
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleTimeString(LOCALE, { hour: '2-digit', minute: '2-digit', hour12: false });
}

/** Format as "dd/mm/yyyy HH:mm" */
export function formatDateTime(input: string | Date | null | undefined): string {
  if (!input) return '-';
  const d = typeof input === 'string' ? new Date(input) : input;
  if (isNaN(d.getTime())) return '-';
  return `${formatDate(d)} ${formatTime(d)}`;
}

/** Format as "dd/mm" (for tables, lists) */
export function formatDateCompact(input: string | Date | null | undefined): string {
  if (!input) return '-';
  const d = typeof input === 'string' ? new Date(input) : input;
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleDateString(LOCALE, { day: '2-digit', month: '2-digit' });
}
