import api from './client';

export const testConnection = (datasetId, params) =>
  api.post(`/datasets/${datasetId}/ontology/modeling/test-connection`, params);

export const analyzeSchema = (datasetId, params) =>
  api.post(`/datasets/${datasetId}/ontology/modeling/analyze-schema`, params);

export const compileOntology = (datasetId, analysisResult) =>
  api.post(`/datasets/${datasetId}/ontology/modeling/compile`, { analysis_result: analysisResult });

export const registerOntology = (datasetId, compiledOntology) =>
  api.post(`/datasets/${datasetId}/ontology/modeling/register`, { compiled_ontology: compiledOntology });

export const quickModel = (datasetId, params) =>
  api.post(`/datasets/${datasetId}/ontology/modeling/quick-model`, params);

export const detectChanges = (datasetId, params) =>
  api.post(`/datasets/${datasetId}/ontology/modeling/detect-changes`, params);
