import api from './client';

export function getSystemConfig() {
  return api.get('/admin/system-config').then(r => r.data);
}

export function updateSystemConfig(key, data) {
  return api.put(`/admin/system-config/${key}`, data).then(r => r.data);
}

export function deleteSystemConfig(key) {
  return api.delete(`/admin/system-config/${key}`).then(r => r.data);
}

export function getHealth() {
  return api.get('/health').then(r => r.data);
}
