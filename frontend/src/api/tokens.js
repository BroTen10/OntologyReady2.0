import api from './client';

export const listApiKeys = () => api.get('/api-keys');
export const createApiKey = (data) => api.post('/api-keys', data);
export const revokeApiKey = (id) => api.delete(`/api-keys/${id}`);

export const listPersonalTokens = () => api.get('/personal-tokens');
export const createPersonalToken = (data) => api.post('/personal-tokens', data);
export const revokePersonalToken = (id) => api.delete(`/personal-tokens/${id}`);

export const listAllApiKeys = (page, pageSize) =>
  api.get('/admin/api-keys', { params: { page, page_size: pageSize } });
export const revokeApiKeyAdmin = (id) => api.delete(`/admin/api-keys/${id}`);

export const listAllTokens = (page, pageSize) =>
  api.get('/admin/tokens', { params: { page, page_size: pageSize } });
export const revokeTokenAdmin = (id) => api.delete(`/admin/tokens/${id}`);
export const revokeUserTokensAdmin = (userId) => api.post(`/admin/tokens/revoke-by-user/${userId}`);
