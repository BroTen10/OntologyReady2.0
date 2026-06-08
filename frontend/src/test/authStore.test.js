import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '../stores/authStore';

describe('authStore', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({ user: null, isLoggedIn: false });
  });

  it('should have initial state with no user', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isLoggedIn).toBe(false);
  });

  it('should set user and isLoggedIn when setUser is called', () => {
    const user = { id: '1', username: 'admin', roles: ['admin'] };
    useAuthStore.getState().setUser(user);
    const state = useAuthStore.getState();
    expect(state.user).toEqual(user);
    expect(state.isLoggedIn).toBe(true);
  });

  it('should set isLoggedIn to false when setUser(null) is called', () => {
    useAuthStore.getState().setUser({ id: '1', username: 'test' });
    useAuthStore.getState().setUser(null);
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isLoggedIn).toBe(false);
  });

  it('should clear tokens and user on logout', () => {
    localStorage.setItem('auth_access_token', 'test-access');
    localStorage.setItem('auth_refresh_token', 'test-refresh');
    useAuthStore.getState().setUser({ id: '1', username: 'test' });
    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isLoggedIn).toBe(false);
    expect(localStorage.getItem('auth_access_token')).toBeNull();
    expect(localStorage.getItem('auth_refresh_token')).toBeNull();
  });
});
