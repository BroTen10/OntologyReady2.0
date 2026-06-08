import api from './client';

// ── ACR Config ───────────────────────────────────────────

export async function getACRConfig() {
  return api.get('/acr/config').then(r => r.data);
}

export async function updateACRConfig(data) {
  return api.put('/acr/config', data).then(r => r.data);
}

// ── Access Rules ─────────────────────────────────────────

export async function listRules(resourceType) {
  const params = resourceType ? { resource_type: resourceType } : {};
  return api.get('/acr/rules', { params }).then(r => r.data);
}

export async function getRule(ruleId) {
  return api.get(`/acr/rules/${ruleId}`).then(r => r.data);
}

export async function createRule(data) {
  return api.post('/acr/rules', data).then(r => r.data);
}

export async function updateRule(ruleId, data) {
  return api.put(`/acr/rules/${ruleId}`, data).then(r => r.data);
}

export async function deleteRule(ruleId) {
  return api.delete(`/acr/rules/${ruleId}`).then(r => r.data);
}

// ── Rule Groups ──────────────────────────────────────────

export async function listRuleGroups() {
  return api.get('/acr/rule-groups').then(r => r.data);
}

export async function getRuleGroup(groupId) {
  return api.get(`/acr/rule-groups/${groupId}`).then(r => r.data);
}

export async function createRuleGroup(data) {
  return api.post('/acr/rule-groups', data).then(r => r.data);
}

export async function updateRuleGroup(groupId, data) {
  return api.put(`/acr/rule-groups/${groupId}`, data).then(r => r.data);
}

export async function deleteRuleGroup(groupId) {
  return api.delete(`/acr/rule-groups/${groupId}`).then(r => r.data);
}

// ── Bindings ─────────────────────────────────────────────

export async function listBindings() {
  return api.get('/acr/bindings').then(r => r.data);
}

export async function createBinding(data) {
  return api.post('/acr/bindings', data).then(r => r.data);
}

export async function deleteBinding(bindingId) {
  return api.delete(`/acr/bindings/${bindingId}`).then(r => r.data);
}
