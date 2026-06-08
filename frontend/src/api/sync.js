import api from './client';

export const testSyncConnection = (params) =>
  api.post('/sync/test-connection', params);

export const runSync = (params) =>
  api.post('/sync/run', params);

export const listSyncTasks = (params) =>
  api.get('/sync/tasks', { params });

export const getSyncTask = (taskId) =>
  api.get(`/sync/tasks/${taskId}`);

export const getSyncTaskLogs = (taskId, params) =>
  api.get(`/sync/tasks/${taskId}/logs`, { params });

export const cancelSyncTask = (taskId) =>
  api.post(`/sync/tasks/${taskId}/cancel`);

export const listSourceTables = (params) =>
  api.get('/sync/tables', { params });

export const getTableInfo = (params) =>
  api.get('/sync/table-info', { params });
