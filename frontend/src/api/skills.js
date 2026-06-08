import api from './client';

// ── CRUD ──────────────────────────────────────────────────

export function listSkills(params = {}) {
  return api.get('/skills', { params }).then(r => r.data);
}

export function getSkill(skillId) {
  return api.get(`/skills/${skillId}`).then(r => r.data);
}

export function createSkill(data) {
  return api.post('/skills', data).then(r => r.data);
}

export function updateSkill(skillId, data) {
  return api.put(`/skills/${skillId}`, data).then(r => r.data);
}

export function deleteSkill(skillId) {
  return api.delete(`/skills/${skillId}`).then(r => r.data);
}

// ── Actions ───────────────────────────────────────────────

export function enableSkill(skillId) {
  return api.post(`/skills/${skillId}/enable`).then(r => r.data);
}

export function disableSkill(skillId) {
  return api.post(`/skills/${skillId}/disable`).then(r => r.data);
}

export function cloneSkill(skillId, newName) {
  return api.post(`/skills/${skillId}/clone`, null, { params: { new_name: newName } }).then(r => r.data);
}

// ── Presets ───────────────────────────────────────────────

export function listPresets() {
  return api.get('/skills/presets/index').then(r => r.data);
}

export function getPreset(name) {
  return api.get(`/skills/presets/${name}`).then(r => r.data);
}

export function importPresets(presets) {
  return api.post('/skills/presets/import', { presets }).then(r => r.data);
}

// ── Upload / Download ─────────────────────────────────────

export function downloadSkill(skillId) {
  return api.get(`/skills/${skillId}/download`).then(r => r.data);
}

export function uploadSkillPack(pack) {
  return api.post('/skills/upload', pack).then(r => r.data);
}

// ── Generate from Action ──────────────────────────────────

export function generateFromAction(datasetId, data) {
  return api.post('/skills/generate-from-action', data, { params: { dataset_id: datasetId } }).then(r => r.data);
}

// ── Categories ────────────────────────────────────────────

export function listCategories() {
  return api.get('/skills/categories/list').then(r => r.data);
}
