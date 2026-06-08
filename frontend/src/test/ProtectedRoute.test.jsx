import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProtectedRoute from '../components/ProtectedRoute';
import { useAuthStore } from '../stores/authStore';

vi.mock('../stores/authStore', () => ({
  useAuthStore: vi.fn(),
}));

describe('ProtectedRoute', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('should render children when logged in', () => {
    useAuthStore.mockReturnValue(true); // isLoggedIn
    localStorage.setItem('auth_access_token', 'test-token');

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div data-testid="protected-content">Protected</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('should redirect to /login when not logged in and no token', () => {
    useAuthStore.mockReturnValue(false);
    localStorage.removeItem('auth_access_token');

    render(
      <MemoryRouter initialEntries={['/']}>
        <ProtectedRoute>
          <div data-testid="protected-content">Protected</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('should render children when has token even if isLoggedIn is false', () => {
    useAuthStore.mockReturnValue(false);
    localStorage.setItem('auth_access_token', 'test-token');

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div data-testid="protected-content">Protected</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });
});
