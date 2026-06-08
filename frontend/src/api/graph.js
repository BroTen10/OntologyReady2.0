import api from './client';

export const getGraphStats = (datasetId) =>
  api.get(`/datasets/${datasetId}/ontology/graph/stats`);

export const getNeighbors = (datasetId, objectType, objectId, depth = 1) =>
  api.get(`/datasets/${datasetId}/ontology/graph/neighbors/${objectType}/${objectId}`, { params: { depth } });

export const findPath = (datasetId, sourceId, targetId, maxDepth = 5) =>
  api.post(`/datasets/${datasetId}/ontology/graph/path`, { source_id: sourceId, target_id: targetId, max_depth: maxDepth });

export const traverse = (datasetId, startNode, direction = 'both', maxDepth = 3, edgeTypes, nodeTypes) =>
  api.post(`/datasets/${datasetId}/ontology/graph/traverse`, {
    start_node: startNode, direction, max_depth: maxDepth,
    edge_types: edgeTypes || null, node_types: nodeTypes || null,
  });
