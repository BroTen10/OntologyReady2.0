import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export default function ProtectedRoute({ children }) {
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn);
  const hasToken = !!localStorage.getItem('auth_access_token');
  if (!isLoggedIn && !hasToken) return <Navigate to="/login" replace />;
  return children;
}
