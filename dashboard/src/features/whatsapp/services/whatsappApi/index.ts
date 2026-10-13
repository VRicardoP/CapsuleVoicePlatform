import { conversationApi } from './conversations';
import { contactApi } from './contacts';
import { templateApi } from './templates';
import { campaignApi } from './campaigns';
import { commerceApi } from './commerce';
import { automationApi } from './automation';
import { adminApi } from './admin';

export const whatsappApi = {
  ...conversationApi,
  ...contactApi,
  ...templateApi,
  ...campaignApi,
  ...commerceApi,
  ...automationApi,
  ...adminApi,
};
