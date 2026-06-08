import api from './client';

export const login = (username, password) => {
  const form = new URLSearchParams();
  form.append('username', username);
  form.append('password', password);
  return api.post('/auth/login', form);
};

export const refresh = (refreshToken) =>
  api.post('/auth/refresh', { refresh_token: refreshToken });

export const logout = () => api.post('/auth/logout');
export const me = () => api.get('/auth/me');
