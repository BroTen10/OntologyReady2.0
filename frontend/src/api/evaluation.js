import api from './client';

export function listEvaluationDatasets(params) {
  return api.get('/rag-evaluation/datasets', { params }).then(r => r.data);
}

export function createEvaluationDataset(data) {
  return api.post('/rag-evaluation/datasets', data).then(r => r.data);
}

export function getEvaluationDataset(id) {
  return api.get(`/rag-evaluation/datasets/${id}`).then(r => r.data);
}

export function deleteEvaluationDataset(id) {
  return api.delete(`/rag-evaluation/datasets/${id}`).then(r => r.data);
}

export function addQuestion(datasetId, data) {
  return api.post(`/rag-evaluation/datasets/${datasetId}/questions`, data).then(r => r.data);
}

export function addQuestionsBulk(datasetId, questions) {
  return api.post(`/rag-evaluation/datasets/${datasetId}/questions/bulk`, questions).then(r => r.data);
}

export function uploadQuestionsFile(datasetId, file) {
  const form = new FormData();
  form.append('file', file);
  return api.post(`/rag-evaluation/datasets/${datasetId}/questions/upload`, form).then(r => r.data);
}

export function deleteQuestion(id) {
  return api.delete(`/rag-evaluation/questions/${id}`).then(r => r.data);
}

export function listRuns(params) {
  return api.get('/rag-evaluation/runs', { params }).then(r => r.data);
}

export function createRun(data) {
  return api.post('/rag-evaluation/runs', data).then(r => r.data);
}

export function getRun(id) {
  return api.get(`/rag-evaluation/runs/${id}`).then(r => r.data);
}

export function deleteRun(id) {
  return api.delete(`/rag-evaluation/runs/${id}`).then(r => r.data);
}

export function getRunResults(id) {
  return api.get(`/rag-evaluation/runs/${id}/results`).then(r => r.data);
}

export function compareRuns(data) {
  return api.post('/rag-evaluation/runs/compare', data).then(r => r.data);
}
