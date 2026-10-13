import { SECURITY_CONFIG } from './config';
import { rateLimiter } from './httpClient';
import { authApi } from './authApi';
import { callsApi } from './callsApi';
import { dashboardApi } from './dashboardApi';
import { gdprApi } from './gdprApi';
import { userApi } from './userApi';
import { contactApi } from './contactApi';

export const apiService = {
  ...authApi,
  ...callsApi,
  ...dashboardApi,
  ...gdprApi,
  ...userApi,
  ...contactApi,
};

export const isUsingMockData = (): boolean => SECURITY_CONFIG.USE_MOCK_DATA;
export const getRemainingRequests = (): number => rateLimiter.getRemainingRequests();
