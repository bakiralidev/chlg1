import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function Navbar() {
  const { user, logout, isAdmin } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      height: '64px',
      background: 'rgba(24,24,37,0.9)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--bg-surface0)',
      display: 'flex', alignItems: 'center',
    }}>
      <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
        {/* Logo */}
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', textDecoration: 'none' }}>
          <span style={{ fontSize: '1.4rem' }}>🐍</span>
          <span style={{
            fontWeight: 800, fontSize: '1.1rem',
            background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
          }}>PyChallenge</span>
        </Link>

        {/* Nav links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Link
            to="/"
            style={{
              padding: '0.4rem 0.9rem', borderRadius: 'var(--radius-sm)',
              fontSize: '0.9rem', fontWeight: 500, textDecoration: 'none',
              color: isActive('/') ? 'var(--accent)' : 'var(--text-sub)',
              background: isActive('/') ? 'rgba(137,180,250,0.1)' : 'transparent',
            }}
          >
            Bosh sahifa
          </Link>

          {isAdmin && isAdmin() && (
            <Link
              to="/admin"
              style={{
                padding: '0.4rem 0.9rem', borderRadius: 'var(--radius-sm)',
                fontSize: '0.9rem', fontWeight: 500, textDecoration: 'none',
                color: location.pathname.startsWith('/admin') ? 'var(--accent-2)' : 'var(--text-sub)',
                background: location.pathname.startsWith('/admin') ? 'rgba(203,166,247,0.1)' : 'transparent',
              }}
            >
              👑 Admin
            </Link>
          )}

          {/* User info & logout */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginLeft: '0.5rem' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.4rem 0.75rem',
              background: 'var(--bg-surface0)',
              borderRadius: 'var(--radius-sm)',
            }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {user?.username || user?.email}
              </span>
              {user?.total_score > 0 && (
                <span className="badge badge-blue">{user.total_score} ball</span>
              )}
            </div>
            <button
              id="navbar-logout"
              onClick={handleLogout}
              className="btn btn-ghost"
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}
            >
              Chiqish
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
