import type { User, ApiResponse } from '../../types';
import { SECURITY_CONFIG } from './config';
import { secureHttpClient } from './httpClient';

export const userApi = {
  getCurrentUser: async (): Promise<ApiResponse<User>> => {
    return secureHttpClient(SECURITY_CONFIG.ENDPOINTS.USER_ME, {
      method: 'GET',
    });
  },

  updateCurrentUser: async (data: {
    full_name?: string;
    preferences?: { visibleModules: string[]; theme: string };
  }): Promise<ApiResponse<User>> => {
    return secureHttpClient(SECURITY_CONFIG.ENDPOINTS.USER_ME, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  saveUserPreferences: async (
    _userId: string,
    preferences: { visibleModules: string[] }
  ): Promise<ApiResponse<void>> => {
    if (SECURITY_CONFIG.USE_MOCK_DATA) {
      return { success: true, data: undefined };
    }

    return secureHttpClient<void>(SECURITY_CONFIG.ENDPOINTS.USER_PREFERENCES, {
      method: 'PUT',
      body: JSON.stringify({
        preferences: {
          visibleModules: preferences.visibleModules,
          theme: 'dark',
        },
      }),
    });
  },

  getSessions: async (): Promise<ApiResponse<Array<{
    id: string;
    device: string;
    ip_address: string;
    created_at: string;
    is_current: boolean;
  }>>> => {
    return secureHttpClient(SECURITY_CONFIG.ENDPOINTS.SESSIONS, {
      method: 'GET',
    });
  },

  terminateSession: async (sessionId: string): Promise<ApiResponse<void>> => {
    return secureHttpClient(`${SECURITY_CONFIG.ENDPOINTS.SESSIONS}/${sessionId}`, {
      method: 'DELETE',
    });
  },
};
