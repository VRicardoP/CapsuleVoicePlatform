import { createModuleClient } from '../../../../services/api/moduleClient';

const client = createModuleClient('/api/v1/whatsapp');

export const WA_BASE = client.BASE;
export const { request, voidRequest, jsonPost, jsonPatch, qs } = client;
