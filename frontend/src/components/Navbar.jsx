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
      background: 'rgba(24,24,37,0.92)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--bg-surface0)',
      display: 'flex', alignItems: 'center',
    }}>
      <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
        {/* Logo */}
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', textDecoration: 'none' }}>
          <span style={{ fontSize: '1.4rem' }}>🐍</span>
          <span style={{
            fontWeight: 800, fontSize: '1.15rem',
            background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
          }}>PyChallenge</span>
        </Link>

        {/* Center / Nav Links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <Link
            to="/"
            style={{
              padding: '0.4rem 0.85rem', borderRadius: 'var(--radius-sm)',
              fontSize: '0.9rem', fontWeight: 500, textDecoration: 'none',
              color: isActive('/') ? 'var(--accent)' : 'var(--text-sub)',
              background: isActive('/') ? 'rgba(137,180,250,0.1)' : 'transparent',
              transition: 'all 0.2s',
            }}
          >
            Bosh sahifa
          </Link>

          {/* If guest, show in-page anchors */}
          {!user ? (
            <>
              <a
                href="/#challenges"
                style={{
                  padding: '0.4rem 0.85rem', borderRadius: 'var(--radius-sm)',
                  fontSize: '0.9rem', fontWeight: 500, textDecoration: 'none',
                  color: 'var(--text-sub)', transition: 'all 0.2s',
                }}
              >
                Challengelar
              </a>
              <a
                href="/#how-it-works"
                style={{
                  padding: '0.4rem 0.85rem', borderRadius: 'var(--radius-sm)',
                  fontSize: '0.9rem', fontWeight: 500, textDecoration: 'none',
                  color: 'var(--text-sub)', transition: 'all 0.2s',
                }}
              >
                Qoidalar
              </a>
              <a
                href="/#demo"
                style={{
                  padding: '0.4rem 0.85rem', borderRadius: 'var(--radius-sm)',
                  fontSize: '0.9rem', fontWeight: 600, textDecoration: 'none',
                  color: 'var(--accent)', background: 'rgba(137,180,250,0.08)',
                  border: '1px solid rgba(137,180,250,0.2)', transition: 'all 0.2s',
                }}
              >
                ⚡ Sinab ko'rish
              </a>
            </>
          ) : (
            <Link
              to="/dashboard"
              style={{
                padding: '0.4rem 0.85rem', borderRadius: 'var(--radius-sm)',
                fontSize: '0.9rem', fontWeight: 500, textDecoration: 'none',
                color: isActive('/dashboard') ? 'var(--accent)' : 'var(--text-sub)',
                background: isActive('/dashboard') ? 'rgba(137,180,250,0.1)' : 'transparent',
                transition: 'all 0.2s',
              }}
            >
              Challengelarim
            </Link>
          )}

          {isAdmin && isAdmin() && (
            <Link
              to="/admin"
              style={{
                padding: '0.4rem 0.85rem', borderRadius: 'var(--radius-sm)',
                fontSize: '0.9rem', fontWeight: 500, textDecoration: 'none',
                color: location.pathname.startsWith('/admin') ? 'var(--accent-2)' : 'var(--text-sub)',
                background: location.pathname.startsWith('/admin') ? 'rgba(203,166,247,0.1)' : 'transparent',
                transition: 'all 0.2s',
              }}
            >
              👑 Admin
            </Link>
          )}
        </div>

        {/* Right action buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {!user ? (
            <>
              <Link
                to="/login"
                className="btn btn-ghost"
                style={{
                  padding: '0.4rem 0.9rem', fontSize: '0.85rem',
                  color: 'var(--text-main)', border: '1px solid var(--bg-surface1)'
                }}
              >
                Kirish
              </Link>
              <Link
                to="/register"
                className="btn btn-primary"
                style={{ padding: '0.4rem 1.1rem', fontSize: '0.85rem' }}
              >
                Ro'yxatdan o'tish
              </Link>
            </>
          ) : (
            <>
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
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
