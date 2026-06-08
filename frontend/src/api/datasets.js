import api from './client';

export function listDatasets(params = {}) {
  return api.get('/datasets', { params }).then(r => r.data);
}

export function createDataset(data) {
  return api.post('/datasets', data).then(r => r.data);
}

export function getDataset(id) {
  return api.get(`/datasets/${id}`).then(r => r.data);
}

export function updateDataset(id, data) {
  return api.put(`/datasets/${id}`, data).then(r => r.data);
}

export function deleteDataset(id) {
  return api.delete(`/datasets/${id}`).then(r => r.data);
}
