import api from './client';

// Knowledge Bases
export function listKnowledgeBases() {
  return api.get('/rag/knowledge-bases').then(r => r.data);
}

export function createKnowledgeBase(name, description = '') {
  return api.post('/rag/knowledge-bases', { name, description }).then(r => r.data);
}

export function getKnowledgeBase(kbId) {
  return api.get(`/rag/knowledge-bases/${kbId}`).then(r => r.data);
}

export function deleteKnowledgeBase(kbId) {
  return api.delete(`/rag/knowledge-bases/${kbId}`).then(r => r.data);
}

export function getKBStats(kbId) {
  return api.get(`/rag/knowledge-bases/${kbId}/stats`).then(r => r.data);
}

// Documents
export function listDocuments(kbId) {
  return api.get(`/rag/knowledge-bases/${kbId}/documents`).then(r => r.data);
}

export function uploadDocument(kbId, file) {
  const form = new FormData();
  form.append('file', file);
  return api.post(`/rag/knowledge-bases/${kbId}/documents`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
}

export function deleteDocument(docId) {
  return api.delete(`/rag/documents/${docId}`).then(r => r.data);
}

export function listChunks(docId, kbId) {
  return api.get(`/rag/documents/${docId}/chunks`, { params: { kb_id: kbId } }).then(r => r.data);
}

// Search
export function search(kbId, query, topK = 10) {
  return api.post('/rag/search', { kb_id: kbId, query, top_k: topK }).then(r => r.data);
}

// Chat
export function ragChat(kbId, question, history = []) {
  return api.post('/rag/chat', { kb_id: kbId, question, history }).then(r => r.data);
}

export function ragChatStream(kbId, question, history = []) {
  return api.post('/rag/chat/stream', { kb_id: kbId, question, history }, {
    responseType: 'stream',
  });
}

// Conversations
export function listConversations() {
  return api.get('/rag/conversations').then(r => r.data);
}

export function createConversation(kbId, title = '', modelParams = {}, systemPrompt = '') {
  return api.post('/rag/conversations', {
    kb_id: kbId, title, model_params: modelParams, system_prompt: systemPrompt,
  }).then(r => r.data);
}

export function getConversation(convId) {
  return api.get(`/rag/conversations/${convId}`).then(r => r.data);
}

export function deleteConversation(convId) {
  return api.delete(`/rag/conversations/${convId}`).then(r => r.data);
}
