import type { User, ApiResponse } from '../../types';
import { SECURITY_CONFIG } from './config';
import { secureHttpClient, delay, sanitizeInput, validateEmail, isValidUser } from './httpClient';

export const authApi = {
  login: async (email: string, password: string): Promise<ApiResponse<User>> => {
    if (!validateEmail(email)) {
      return { success: false, data: null as any, error: 'Email inválido' };
    }

    if (password.length < 8) {
      return { success: false, data: null as any, error: 'Contraseña debe tener al menos 8 caracteres' };
    }

    const sanitizedEmail = sanitizeInput(email);

    if (SECURITY_CONFIG.USE_MOCK_DATA) {
      await delay(800);
      const mockUser: User = {
        id: '550e8400-e29b-41d4-a716-446655440000',
        name: 'Demo User',
        email: sanitizedEmail,
        company: 'Demo Company',
        role: 'user',
        preferences: {
          visibleModules: ['metrics-overview', 'weekly-evolution'],
          theme: 'dark',
        },
      };
      return { success: true, data: mockUser };
    }

    const response = await secureHttpClient<{ user: User; expiresIn: number }>(
      SECURITY_CONFIG.ENDPOINTS.LOGIN,
      {
        method: 'POST',
        body: JSON.stringify({ email: sanitizedEmail, password }),
      }
    );

    if (response.success) {
      if (!isValidUser(response.data.user)) {
        return { success: false, data: null as any, error: 'Respuesta inválida del servidor' };
      }
      return { success: true, data: response.data.user };
    }

    return { success: false, data: null as any, error: response.error || 'Login failed' };
  },

  logout: async (): Promise<ApiResponse<void>> => {
    if (SECURITY_CONFIG.USE_MOCK_DATA) {
      return { success: true, data: undefined };
    }

    return secureHttpClient<void>(SECURITY_CONFIG.ENDPOINTS.LOGOUT, {
      method: 'POST',
      body: JSON.stringify({ invalidate_all: false }),
    });
  },
};
