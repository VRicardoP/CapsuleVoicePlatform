import type { ApiResponse } from '../../types';
import { SECURITY_CONFIG } from './config';
import { secureHttpClient, delay } from './httpClient';

export const contactApi = {
  sendContactEmail: async (data: {
    subject: string;
    message: string;
  }): Promise<ApiResponse<{ success: boolean; message: string }>> => {
    if (SECURITY_CONFIG.USE_MOCK_DATA) {
      await delay(500);
      return {
        success: true,
        data: {
          success: true,
          message: 'Tu mensaje ha sido enviado correctamente. Nos pondremos en contacto contigo pronto.',
        },
      };
    }

    return secureHttpClient(SECURITY_CONFIG.ENDPOINTS.CONTACT_SEND, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};
