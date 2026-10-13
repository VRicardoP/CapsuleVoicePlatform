/**
 * Utilidades de privacidad y protección de datos personales (PII)
 * Implementa cumplimiento RGPD/LOPDGDD
 */

import type { ConsentInfo, UserRole } from '../types';

/**
 * Categorías de datos PII según RGPD
 */
export const PII_CATEGORY = {
  NAME: 'name',
  EMAIL: 'email',
  PHONE: 'phone',
  ADDRESS: 'address',
  ID_NUMBER: 'id_number',
  FINANCIAL: 'financial',
  HEALTH: 'health',
  BIOMETRIC: 'biometric',
  LOCATION: 'location',
} as const;

type PiiCategoryValue = typeof PII_CATEGORY[keyof typeof PII_CATEGORY];

/**
 * Detecta si un texto contiene datos PII
 * @param text - Texto a analizar
 * @returns Array de categorías PII detectadas
 */
export const detectPII = (text: string): PiiCategoryValue[] => {
  const categories: PiiCategoryValue[] = [];

  // Detectar emails
  if (/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/.test(text)) {
    categories.push(PII_CATEGORY.EMAIL);
  }

  // Detectar teléfonos españoles
  if (/(\+34|0034)?[\s.-]?[6-9]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}/.test(text)) {
    categories.push(PII_CATEGORY.PHONE);
  }

  // Detectar DNI/NIE español
  if (/\b\d{8}[A-Z]\b|\b[XYZ]\d{7}[A-Z]\b/.test(text)) {
    categories.push(PII_CATEGORY.ID_NUMBER);
  }

  // Detectar direcciones (básico)
  if (/\b(calle|avenida|plaza|paseo|c\/)[\s\w\d,.-]+\d+/i.test(text)) {
    categories.push(PII_CATEGORY.ADDRESS);
  }

  return categories;
};

/**
 * Anonimiza un nombre completo
 * Art. 5.1.e RGPD - Minimización de datos
 *
 * @param name - Nombre a anonimizar
 * @param mode - Nivel de anonimización ('partial' | 'full')
 * @returns Nombre anonimizado
 */
export const anonymizeName = (name: string, mode: 'partial' | 'full' = 'partial'): string => {
  if (mode === 'full') {
    return '*** DATOS PROTEGIDOS ***';
  }

  // Anonimización parcial: Primera letra + asteriscos
  const parts = name.trim().split(/\s+/);
  return parts.map(part => {
    if (part.length <= 1) return part;
    return part.charAt(0) + '*'.repeat(Math.min(part.length - 1, 3));
  }).join(' ');
};

/**
 * Anonimiza un número de teléfono
 * Art. 32 RGPD - Seguridad del tratamiento
 *
 * @param phone - Teléfono a anonimizar
 * @param visibleDigits - Cantidad de dígitos visibles al final (por defecto 3)
 * @returns Teléfono anonimizado
 */
export const anonymizePhone = (phone: string, visibleDigits: number = 3): string => {
  const cleaned = phone.replace(/\s/g, '');
  if (cleaned.length <= visibleDigits) {
    return '*'.repeat(cleaned.length);
  }

  const visible = cleaned.slice(-visibleDigits);
  const masked = cleaned.slice(0, -visibleDigits).replace(/\d/g, '*');

  return masked + visible;
};

/**
 * Anonimiza un email
 * Art. 32 RGPD - Seguridad del tratamiento
 *
 * @param email - Email a anonimizar
 * @returns Email anonimizado
 */
export const anonymizeEmail = (email: string): string => {
  const [local, domain] = email.split('@');
  if (!domain) return '***@***';

  if (local.length <= 2) {
    return '*'.repeat(local.length) + '@' + domain;
  }

  const first = local.charAt(0);
  const last = local.charAt(local.length - 1);
  const masked = '*'.repeat(Math.min(local.length - 2, 5));

  return `${first}${masked}${last}@${domain}`;
};

/**
 * Redacta contenido PII de un texto
 * Reemplaza datos personales detectados con [REDACTED]
 *
 * @param text - Texto original
 * @returns Texto con PII redactado
 */
export const redactPII = (text: string): string => {
  let redacted = text;

  // Redactar emails
  redacted = redacted.replace(
    /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    '[EMAIL REDACTADO]'
  );

  // Redactar teléfonos
  redacted = redacted.replace(
    /(\+34|0034)?[\s.-]?[6-9]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}/g,
    '[TELÉFONO REDACTADO]'
  );

  // Redactar DNI/NIE
  redacted = redacted.replace(
    /\b\d{8}[A-Z]\b|\b[XYZ]\d{7}[A-Z]\b/g,
    '[DNI/NIE REDACTADO]'
  );

  return redacted;
};

/**
 * Valida si un consentimiento está activo
 * Art. 7 RGPD - Condiciones para el consentimiento
 *
 * @param consent - Información del consentimiento
 * @returns true si el consentimiento es válido y activo
 */
export const isConsentValid = (consent: ConsentInfo | null | undefined): boolean => {
  if (!consent) return false;

  // Debe haber sido otorgado
  if (!consent.given) return false;

  // No debe estar revocado
  if (consent.revokedAt) return false;

  // Verificar expiración
  if (consent.expiresAt) {
    const expiryDate = new Date(consent.expiresAt);
    const now = new Date();
    if (now > expiryDate) return false;
  }

  return true;
};

/**
 * Calcula el tiempo restante de un consentimiento
 *
 * @param consent - Información del consentimiento
 * @returns Días restantes, null si no expira o es inválido
 */
export const getConsentDaysRemaining = (consent: ConsentInfo): number | null => {
  if (!consent.expiresAt) return null;
  if (!isConsentValid(consent)) return 0;

  const expiry = new Date(consent.expiresAt);
  const now = new Date();
  const diffTime = expiry.getTime() - now.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  return Math.max(0, diffDays);
};

/**
 * Formatea una fecha de forma legible cumpliendo RGPD
 * @param dateString - Fecha en formato ISO
 * @returns Fecha formateada
 */
export const formatPrivacyDate = (dateString: string): string => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

/**
 * Genera un hash simple para identificadores anonimizados
 * NO es criptográficamente seguro - solo para display
 *
 * @param input - String a hashear
 * @returns Hash de 8 caracteres
 */
export const generateDisplayHash = (input: string): string => {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(16).padStart(8, '0').slice(0, 8).toUpperCase();
};

/**
 * Registra acceso a datos PII para auditoría
 * Art. 32.1.d RGPD - Proceso de verificación de eficacia
 *
 * @param userId - ID del usuario que accede
 * @param dataType - Tipo de dato accedido
 * @param recordId - ID del registro accedido
 */
/**
 * Valida permisos de rol para operaciones específicas
 * Art. 32.1.b RGPD - Control de acceso
 *
 * @param userRole - Rol del usuario
 * @param requiredRole - Rol requerido para la operación
 * @returns true si el usuario tiene permisos suficientes
 */
export const hasRequiredRole = (userRole: UserRole, requiredRole: UserRole): boolean => {
  // New permission system maps to the legacy levels as follows:
  //   superadmin / admin    → 4 (full)
  //   client_admin          → 4 (admin-tier in their tenant)
  //   user                  → 3
  //   viewer                → 2
  //   auditor               → 1
  // Unknown roles fall through to 0.
  const roleHierarchy: Partial<Record<UserRole, number>> = {
    superadmin: 4,
    admin: 4,
    client_admin: 4,
    user: 3,
    viewer: 2,
    auditor: 1,
  };

  return (roleHierarchy[userRole] ?? 0) >= (roleHierarchy[requiredRole] ?? 0);
};

/**
 * Sanitiza input del usuario para prevenir XSS
 * Art. 32.1.a RGPD - Pseudonimización y cifrado
 *
 * @param input - Input del usuario
 * @returns Input sanitizado
 */
export const sanitizeInput = (input: string): string => {
  return input
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
};

/**
 * Valida formato de email
 * @param email - Email a validar
 * @returns true si el formato es válido
 */
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$/;
  return emailRegex.test(email);
};

/**
 * Valida formato de teléfono español
 * @param phone - Teléfono a validar
 * @returns true si el formato es válido
 */
export const isValidSpanishPhone = (phone: string): boolean => {
  const phoneRegex = /^(\+34|0034)?[\s.-]?[6-9]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}$/;
  return phoneRegex.test(phone);
};
