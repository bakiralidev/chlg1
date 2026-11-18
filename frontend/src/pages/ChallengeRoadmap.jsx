import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { toast } from 'react-hot-toast';
import Navbar from '../components/Navbar';

const STATUS_CONFIG = {
  today:       { bg: 'rgba(166,227,161,0.14)', border: 'var(--success)', label: 'Bugun (ochiq)', icon: '🟢', textColor: 'var(--success)' },
  completed:   { bg: 'rgba(137,180,250,0.14)', border: 'var(--accent)',  label: 'Topshirilgan',  icon: '✅', textColor: 'var(--accent)' },
  disqualified:{ bg: 'rgba(243,139,168,0.1)',  border: 'var(--danger)',  label: 'DQ',            icon: '🚫', textColor: 'var(--danger)' },
  expired:     { bg: 'rgba(108,112,134,0.1)',  border: 'var(--bg-surface1)', label: "O'tkazib yuborilgan (0 ball)", icon: '⛔', textColor: 'var(--text-dim)' },
  locked:      { bg: 'var(--bg-surface0)',     border: 'var(--bg-surface0)', label: 'Hali ochilmagan', icon: '🔒', textColor: 'var(--text-dim)' },
};

function getDayStatus(day) {
  if (day.is_disqualified) return 'disqualified';
  if (day.is_completed) return 'completed';
  if (day.is_today) return 'today';
  if (day.is_expired) return 'expired';
  if (day.is_locked) return 'locked';
  return 'locked';
}

export default function ChallengeRoadmap() {
  const { challengeId } = useParams();
  const navigate = useNavigate();
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getMyProgress(challengeId)
      .then(({ data }) => setProgress(data))
      .catch(() => toast.error("Ma'lumot yuklanmadi"))
      .finally(() => setLoading(false));
  }, [challengeId]);

  const handleDayClick = (day, status) => {
    if (status === 'expired') {
      toast.error('Bu kunning muddati tugagan');
      return;
    }
    if (status === 'locked') {
      toast.error(`Bu kun hali ochilmagan (${day.opens_on})`);
      return;
    }
    if (status === 'today' || status === 'completed') {
      const targetId = day.day_id || `${challengeId}_day${day.day_number}`;
      navigate(`/arena/${targetId}`);
    }
  };

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="loading-page">
          <div className="spinner" />
          <span>Yuklanmoqda...</span>
        </div>
      </>
    );
  }

  const days = progress?.days || [];
  const completed = days.filter((d) => d.is_completed).length;
  const total = days.length;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem' }}>
          <div className="fade-in" style={{ marginBottom: '2rem' }}>
            <h1 style={{ fontSize: '1.8rem', marginBottom: '0.5rem' }}>
              🗺️ {progress?.challenge_name}
            </h1>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
              {completed}/{total} kun topshirildi
            </p>
            <div className="progress-bar" style={{ maxWidth: '400px' }}>
              <div className="progress-fill" style={{ width: `${pct}%` }} />
            </div>

            <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              {progress?.my_total_score != null && (
                <span className="badge badge-blue" style={{ fontSize: '0.85rem' }}>
                  🏆 Umumiy ball: {progress.my_total_score}
                </span>
              )}
              {progress?.my_rank != null && (
                <span className="badge badge-purple" style={{ fontSize: '0.85rem' }}>
                  🥇 O'rnim: {progress.my_rank}-o'rin / jami {progress.total_participants}
                </span>
              )}
            </div>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            gap: '0.75rem',
          }}>
            {days.map((day) => {
              const status = getDayStatus(day);
              const cfg = STATUS_CONFIG[status];
              const canEnter = status === 'today' || status === 'completed';

              return (
                <div
                  key={day.day_number}
                  id={`day-card-${day.day_number}`}
                  className="fade-in"
                  style={{
                    background: cfg.bg,
                    border: `2px solid ${cfg.border}`,
                    borderRadius: 'var(--radius-md)',
                    padding: '1rem',
                    cursor: 'pointer',
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    position: 'relative',
                  }}
                  onClick={() => handleDayClick(day, status)}
                  onMouseEnter={(e) => {
                    if (canEnter) {
                      e.currentTarget.style.transform = 'translateY(-3px)';
                      e.currentTarget.style.boxShadow = '0 8px 24px rgba(137,180,250,0.2)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = '';
                    e.currentTarget.style.boxShadow = '';
                  }}
                >
                  <div style={{ fontSize: '1.5rem', fontWeight: 800, color: cfg.textColor, marginBottom: '0.25rem' }}>
                    {day.day_number}
                  </div>
                  <div style={{ fontSize: '1.1rem', marginBottom: '0.4rem' }}>{cfg.icon}</div>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-sub)', marginBottom: '0.5rem' }}>
                    {day.title || `Kun ${day.day_number}`}
                  </div>
                  <div style={{ fontSize: '0.68rem', fontWeight: 700, color: cfg.textColor }}>
                    {cfg.label}
                  </div>

                  {day.score != null && (
                    <div style={{
                      position: 'absolute', top: '0.5rem', right: '0.5rem',
                      background: 'var(--bg-surface0)',
                      borderRadius: '999px',
                      padding: '0.15rem 0.5rem',
                      fontSize: '0.7rem', fontWeight: 700,
                      color: day.score >= 70 ? 'var(--success)' : day.score >= 40 ? 'var(--warning)' : 'var(--danger)',
                    }}>
                      {day.score}/100
                    </div>
                  )}

                  {status === 'locked' && (
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                      {day.opens_on}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
