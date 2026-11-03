import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { toast } from 'react-hot-toast';
import Navbar from '../components/Navbar';

const STATUS_CONFIG = {
  today:       { bg: 'rgba(137,180,250,0.15)', border: 'var(--accent)',   label: 'Bugun',    icon: '🔥', textColor: 'var(--accent)' },
  open:        { bg: 'rgba(166,227,161,0.1)',  border: 'var(--success)',  label: 'Ochiq',    icon: '✅', textColor: 'var(--success)' },
  completed:   { bg: 'rgba(166,227,161,0.1)',  border: 'var(--success)',  label: 'Bajarildi',icon: '✅', textColor: 'var(--success)' },
  disqualified:{ bg: 'rgba(243,139,168,0.1)',  border: 'var(--danger)',   label: 'DQ',       icon: '🚫', textColor: 'var(--danger)' },
  expired:     { bg: 'rgba(108,112,134,0.1)',  border: 'var(--bg-surface1)', label: 'O\'tib ketdi', icon: '⏰', textColor: 'var(--text-dim)' },
  locked:      { bg: 'var(--bg-surface0)',      border: 'var(--bg-surface0)', label: 'Yopiq',    icon: '🔒', textColor: 'var(--text-dim)' },
};

function getDayStatus(day) {
  if (day.is_disqualified) return 'disqualified';
  if (day.is_completed) return 'completed';
  if (day.is_today) return 'today';
  if (day.is_expired) return 'expired';
  if (day.is_locked) return 'locked';
  return 'open';
}

export default function ChallengeRoadmap() {
  const { challengeId } = useParams();
  const navigate = useNavigate();
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [enteringDay, setEnteringDay] = useState(null);

  useEffect(() => {
    api.getMyProgress(challengeId)
      .then(({ data }) => setProgress(data))
      .catch(() => toast.error('Ma\'lumot yuklanmadi'))
      .finally(() => setLoading(false));
  }, [challengeId]);

  const handleEnterDay = (day) => {
    const targetId = day.day_id || `${challengeId}_day${day.day_number}`;
    navigate(`/arena/${targetId}`);
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
          {/* Header */}
          <div className="fade-in" style={{ marginBottom: '2rem' }}>
            <h1 style={{ fontSize: '1.8rem', marginBottom: '0.5rem' }}>
              🗺️ {progress?.challenge_name}
            </h1>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
              {completed}/{total} kun bajarildi
            </p>
            <div className="progress-bar" style={{ maxWidth: '400px' }}>
              <div className="progress-fill" style={{ width: `${pct}%` }} />
            </div>

            {progress?.my_total_score != null && (
              <div style={{ marginTop: '0.75rem' }}>
                <span className="badge badge-blue" style={{ fontSize: '0.85rem' }}>
                  Umumiy ball: {progress.my_total_score}
                </span>
              </div>
            )}
          </div>

          {/* Days grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            gap: '0.75rem',
          }}>
            {days.map((day) => {
              const status = getDayStatus(day);
              const cfg = STATUS_CONFIG[status];
              const canEnter = status === 'today' || status === 'open' || status === 'completed';

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
                    cursor: canEnter ? 'pointer' : 'default',
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    position: 'relative',
                  }}
                  onClick={() => canEnter && handleEnterDay(day)}
                  onMouseEnter={(e) => {
                    if (canEnter) {
                      e.currentTarget.style.transform = 'translateY(-3px)';
                      e.currentTarget.style.boxShadow = `0 8px 24px rgba(137,180,250,0.2)`;
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = '';
                    e.currentTarget.style.boxShadow = '';
                  }}
                >
                  {/* Day number */}
                  <div style={{
                    fontSize: '1.5rem', fontWeight: 800,
                    color: cfg.textColor, marginBottom: '0.25rem',
                  }}>
                    {day.day_number}
                  </div>

                  {/* Status icon */}
                  <div style={{ fontSize: '1.1rem', marginBottom: '0.4rem' }}>{cfg.icon}</div>

                  {/* Title */}
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-sub)', marginBottom: '0.5rem' }}>
                    {day.title || `Kun ${day.day_number}`}
                  </div>

                  {/* Badge */}
                  <div style={{ fontSize: '0.65rem', fontWeight: 700, color: cfg.textColor }}>
                    {status === 'today' ? 'Bugun (Yechish)' : status === 'open' ? 'Yechish mumkin' : cfg.label}
                  </div>

                  {/* Score (ertasi kundan) */}
                  {day.score != null && (
                    <div style={{
                      position: 'absolute', top: '0.5rem', right: '0.5rem',
                      background: 'var(--bg-surface0)',
                      borderRadius: '999px',
                      padding: '0.15rem 0.5rem',
                      fontSize: '0.7rem', fontWeight: 700,
                      color: day.score >= 7 ? 'var(--success)' : day.score >= 4 ? 'var(--warning)' : 'var(--danger)',
                    }}>
                      {day.score}/10
                    </div>
                  )}

                  {/* Opens on */}
                  {status === 'locked' && (
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                      {new Date(day.opens_on).toLocaleDateString('uz-UZ')}
                    </div>
                  )}

                  {/* Loading indicator */}
                  {enteringDay === day.day_number && (
                    <div style={{
                      position: 'absolute', inset: 0, display: 'flex',
                      alignItems: 'center', justifyContent: 'center',
                      background: 'rgba(0,0,0,0.5)', borderRadius: 'var(--radius-md)',
                    }}>
                      <div className="spinner" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Results link */}
          {progress?.my_total_score != null && (
            <div style={{ marginTop: '2rem', textAlign: 'center' }}>
              <a
                href={`/challenge/${challengeId}/results`}
                className="btn btn-secondary"
              >
                🏆 Natijalar jadvalini ko'rish
              </a>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
