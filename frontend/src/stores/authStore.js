import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      isLoggedIn: false,
      setUser: (user) => set({ user, isLoggedIn: !!user }),
      logout: () => {
        localStorage.removeItem('auth_access_token');
        localStorage.removeItem('auth_refresh_token');
        set({ user: null, isLoggedIn: false });
      },
    }),
    { name: 'auth-store', partialize: (state) => ({ user: state.user, isLoggedIn: state.isLoggedIn }) },
  ),
);
