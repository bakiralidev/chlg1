import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import ConsentModal from './ConsentModal';

export default function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.must_change_password) {
    return <Navigate to="/set-password" replace />;
  }

  return (
    <>
      {user?.needs_consent ? <ConsentModal /> : null}
      <Outlet />
    </>
  );
}
