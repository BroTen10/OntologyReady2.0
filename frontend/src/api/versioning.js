import api from './client';

// Staging
export function listStagedChanges(datasetId) {
  return api.get(`/datasets/${datasetId}/staging`).then(r => r.data);
}

export function stageChange(datasetId, data) {
  return api.post(`/datasets/${datasetId}/staging`, data).then(r => r.data);
}

export function getStagedChange(datasetId, changeId) {
  return api.get(`/datasets/${datasetId}/staging/${changeId}`).then(r => r.data);
}

export function discardStagedChange(datasetId, changeId) {
  return api.delete(`/datasets/${datasetId}/staging/${changeId}`).then(r => r.data);
}

export function undoStagedChanges(datasetId, changeIds) {
  return api.post(`/datasets/${datasetId}/staging/undo`, { change_ids: changeIds || null }).then(r => r.data);
}

export function commitStaging(datasetId, message, commitChanges) {
  return api.post(`/datasets/${datasetId}/staging/commit`, {
    message,
    commit_changes: commitChanges || null,
  }).then(r => r.data);
}

// Versions
export function listVersions(datasetId, page = 1, pageSize = 20) {
  return api.get(`/datasets/${datasetId}/versions`, { params: { page, page_size: pageSize } }).then(r => r.data);
}

export function getVersion(datasetId, versionId) {
  return api.get(`/datasets/${datasetId}/versions/${versionId}`).then(r => r.data);
}

export function updateVersionNotes(datasetId, versionId, notes) {
  return api.put(`/datasets/${datasetId}/versions/${versionId}/notes`, { notes }).then(r => r.data);
}

export function diffVersions(datasetId, versionA, versionB) {
  return api.get(`/datasets/${datasetId}/versions/diff`, { params: { a: versionA, b: versionB } }).then(r => r.data);
}

export function rollbackVersion(datasetId, versionId) {
  return api.post(`/datasets/${datasetId}/versions/${versionId}/rollback`).then(r => r.data);
}
