import api from './client';

// Workspaces
export const listWorkspaces = () => api.get('/graphrag/workspaces').then(r => r.data);
export const createWorkspace = (data) => api.post('/graphrag/workspaces', data).then(r => r.data);
export const getWorkspace = (id) => api.get(`/graphrag/workspaces/${id}`).then(r => r.data);
export const updateWorkspace = (id, data) => api.put(`/graphrag/workspaces/${id}`, data).then(r => r.data);
export const deleteWorkspace = (id) => api.delete(`/graphrag/workspaces/${id}`).then(r => r.data);
export const setDefaultWorkspace = (id) => api.post(`/graphrag/workspaces/${id}/default`).then(r => r.data);
export const getDefaultWorkspace = () => api.get('/graphrag/workspaces/default').then(r => r.data);

// Documents
export const listDocuments = (wsId) => api.get(`/graphrag/workspaces/${wsId}/documents`).then(r => r.data);
export const deleteDocument = (docId) => api.delete(`/graphrag/documents/${docId}`).then(r => r.data);
export const uploadAndProcess = (wsId, file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post(`/graphrag/workspaces/${wsId}/upload-and-process`, fd).then(r => r.data);
};

// Graph
export const getGraph = (wsId) => api.get(`/graphrag/workspaces/${wsId}/graph`).then(r => r.data);
export const getGraphStats = (wsId) => api.get(`/graphrag/workspaces/${wsId}/graph/stats`).then(r => r.data);
export const getNeighbors = (wsId, entityId, depth = 1) => api.get(`/graphrag/workspaces/${wsId}/graph/neighbors/${entityId}?depth=${depth}`).then(r => r.data);
export const searchEntities = (wsId, query = '', entityType) => api.get(`/graphrag/workspaces/${wsId}/entities`, { params: { query, entity_type: entityType || undefined } }).then(r => r.data);

// Communities
export const getCommunities = (wsId) => api.get(`/graphrag/workspaces/${wsId}/communities`).then(r => r.data);

// Chat
export const chat = (data) => api.post('/graphrag/chat', data).then(r => r.data);
export const chatStream = (data) => api.post('/graphrag/chat/stream', data, { responseType: 'stream' });

// Model Configs
export const listModelConfigs = (wsId, modelType) => api.get('/graphrag/model-configs', { params: { workspace_id: wsId, model_type: modelType || undefined } }).then(r => r.data);
export const createModelConfig = (data) => api.post('/graphrag/model-configs', data).then(r => r.data);
export const getModelConfig = (id) => api.get(`/graphrag/model-configs/${id}`).then(r => r.data);
export const updateModelConfig = (id, data) => api.put(`/graphrag/model-configs/${id}`, data).then(r => r.data);
export const deleteModelConfig = (id) => api.delete(`/graphrag/model-configs/${id}`).then(r => r.data);
