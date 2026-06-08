import api from './client';

export function listUsers(params) {
  return api.get('/users', { params }).then(r => r.data);
}

export function getUser(id) {
  return api.get(`/users/${id}`).then(r => r.data);
}

export function createUser(data) {
  return api.post('/users', data).then(r => r.data);
}

export function updateUser(id, data) {
  return api.put(`/users/${id}`, data).then(r => r.data);
}

export function deleteUser(id) {
  return api.delete(`/users/${id}`).then(r => r.data);
}

export function listRoles() {
  return api.get('/roles').then(r => r.data);
}

export function createRole(data) {
  return api.post('/roles', data).then(r => r.data);
}

export function updateRole(name, data) {
  return api.put(`/roles/${name}`, data).then(r => r.data);
}

export function deleteRole(name) {
  return api.delete(`/roles/${name}`).then(r => r.data);
}

export function listGroups() {
  return api.get('/groups').then(r => r.data);
}

export function createGroup(data) {
  return api.post('/groups', data).then(r => r.data);
}

export function updateGroup(name, data) {
  return api.put(`/groups/${name}`, data).then(r => r.data);
}

export function deleteGroup(name) {
  return api.delete(`/groups/${name}`).then(r => r.data);
}
