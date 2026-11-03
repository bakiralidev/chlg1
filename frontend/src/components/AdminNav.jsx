import { Link, useLocation } from 'react-router-dom';

export default function AdminNav() {
  const location = useLocation();

  const tabs = [
    { path: '/admin', label: '🏆 Challengelar', exact: true },
    { path: '/admin/participants', label: '👥 Ishtirokchilar' },
    { path: '/admin/submissions', label: '📝 Yechimlar va Baholash' },
    { path: '/admin/scores', label: '🤖 AI Baholash' },
  ];

  const isTabActive = (tab) => {
    if (tab.exact) return location.pathname === tab.path;
    return location.pathname.startsWith(tab.path);
  };

  return (
    <div style={{
      display: 'flex',
      gap: '0.5rem',
      padding: '0.4rem',
      background: 'var(--bg-surface0)',
      borderRadius: 'var(--radius)',
      marginBottom: '2rem',
      border: '1px solid var(--border-color)',
      overflowX: 'auto',
    }}>
      {tabs.map((tab) => {
        const active = isTabActive(tab);
        return (
          <Link
            key={tab.path}
            to={tab.path}
            style={{
              padding: '0.6rem 1.25rem',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.9rem',
              fontWeight: 600,
              textDecoration: 'none',
              transition: 'all 0.2s ease',
              whiteSpace: 'nowrap',
              color: active ? '#fff' : 'var(--text-muted)',
              background: active
                ? 'linear-gradient(135deg, var(--accent), var(--accent-2))'
                : 'transparent',
              boxShadow: active ? '0 4px 12px rgba(137, 180, 250, 0.25)' : 'none',
            }}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}

