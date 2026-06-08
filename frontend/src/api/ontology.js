import api from './client';

export function listObjectTypes(datasetId, params) {
  return api.get(`/datasets/${datasetId}/ontology/object-types`, { params }).then(r => r.data);
}

export function createObjectType(datasetId, data) {
  return api.post(`/datasets/${datasetId}/ontology/object-types`, data).then(r => r.data);
}

export function batchCreateObjectTypes(datasetId, types) {
  return api.post(`/datasets/${datasetId}/ontology/object-types/batch`, types).then(r => r.data);
}

export function getObjectType(datasetId, typeName) {
  return api.get(`/datasets/${datasetId}/ontology/object-types/${typeName}`).then(r => r.data);
}

export function updateObjectType(datasetId, typeName, data) {
  return api.put(`/datasets/${datasetId}/ontology/object-types/${typeName}`, data).then(r => r.data);
}

export function deleteObjectType(datasetId, typeName) {
  return api.delete(`/datasets/${datasetId}/ontology/object-types/${typeName}`).then(r => r.data);
}

export function listLinkTypes(datasetId, params) {
  return api.get(`/datasets/${datasetId}/ontology/link-types`, { params }).then(r => r.data);
}

export function createLinkType(datasetId, data) {
  return api.post(`/datasets/${datasetId}/ontology/link-types`, data).then(r => r.data);
}

export function batchCreateLinkTypes(datasetId, types) {
  return api.post(`/datasets/${datasetId}/ontology/link-types/batch`, types).then(r => r.data);
}

export function getLinkType(datasetId, linkName) {
  return api.get(`/datasets/${datasetId}/ontology/link-types/${linkName}`).then(r => r.data);
}

export function updateLinkType(datasetId, linkName, data) {
  return api.put(`/datasets/${datasetId}/ontology/link-types/${linkName}`, data).then(r => r.data);
}

export function deleteLinkType(datasetId, linkName) {
  return api.delete(`/datasets/${datasetId}/ontology/link-types/${linkName}`).then(r => r.data);
}

export function listActionTypes(datasetId, params) {
  return api.get(`/datasets/${datasetId}/ontology/action-types`, { params }).then(r => r.data);
}

export function createActionType(datasetId, data) {
  return api.post(`/datasets/${datasetId}/ontology/action-types`, data).then(r => r.data);
}

export function batchCreateActionTypes(datasetId, types) {
  return api.post(`/datasets/${datasetId}/ontology/action-types/batch`, types).then(r => r.data);
}

export function getActionType(datasetId, actionName) {
  return api.get(`/datasets/${datasetId}/ontology/action-types/${actionName}`).then(r => r.data);
}

export function updateActionType(datasetId, actionName, data) {
  return api.put(`/datasets/${datasetId}/ontology/action-types/${actionName}`, data).then(r => r.data);
}

export function deleteActionType(datasetId, actionName) {
  return api.delete(`/datasets/${datasetId}/ontology/action-types/${actionName}`).then(r => r.data);
}

export function listDataSources(datasetId) {
  return api.get(`/datasets/${datasetId}/ontology/data-sources`).then(r => r.data);
}
