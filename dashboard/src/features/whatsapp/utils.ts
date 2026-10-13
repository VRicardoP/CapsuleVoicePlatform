/** Format E.164 phone for display: Spanish numbers without prefix, international with +XX */
export function formatPhone(phone: string): string {
  const digits = phone.replace(/^\+/, '');
  // Spanish number: 34 + 9 digits
  if (digits.startsWith('34') && digits.length === 11) return digits.slice(2);
  // 9-digit Spanish number (stored with or without +)
  if (digits.length === 9 && /^[6-9]/.test(digits)) return digits;
  // International: show with +
  return `+${digits}`;
}
