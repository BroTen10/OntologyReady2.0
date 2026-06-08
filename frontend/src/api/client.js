import axios from 'axios';

const api = axios.create({ baseURL: '/api', timeout: 30000 });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshPromise = null;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem('auth_refresh_token');
      if (refreshToken && !original.url.includes('/auth/refresh')) {
        try {
          if (!refreshPromise) {
            refreshPromise = api.post('/auth/refresh', { refresh_token: refreshToken });
          }
          const { data: refreshData } = await refreshPromise;
          refreshPromise = null;
          if (refreshData.code === 0) {
            const { access_token, refresh_token } = refreshData.data;
            localStorage.setItem('auth_access_token', access_token);
            localStorage.setItem('auth_refresh_token', refresh_token);
            original.headers.Authorization = `Bearer ${access_token}`;
            return api(original);
          }
        } catch {
          refreshPromise = null;
        }
      }
      localStorage.removeItem('auth_access_token');
      localStorage.removeItem('auth_refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default api;
