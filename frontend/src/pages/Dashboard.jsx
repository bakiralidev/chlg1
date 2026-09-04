import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { toast } from 'react-hot-toast';
import Navbar from '../components/Navbar';
import CountdownTimer from '../components/CountdownTimer';

export default function Dashboard() {
  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getChallenges()
      .then(({ data }) => setChallenges(data))
      .catch(() => toast.error('Challengelarni yuklab bo\'lmadi'))
      .finally(() => setLoading(false));
  }, []);

  const now = new Date();

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem' }}>
          {/* Hero */}
          <div className="fade-in" style={{ marginBottom: '3rem', textAlign: 'center' }}>
            <h1 style={{
              fontSize: '2.8rem', fontWeight: 800, marginBottom: '0.75rem',
              background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
            }}>
              🐍 30 Kunlik Python Challenge
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '1.05rem', maxWidth: '560px', margin: '0 auto' }}>
              Har kuni yangi savol. Kod yozing, ball to'plang, g'olib bo'ling!
            </p>
          </div>

          {/* Challenges */}
          <div className="section-title">
            <h2>Faol Challengelar</h2>
            <span className="badge badge-blue">{challenges.length} ta</span>
          </div>

          {loading ? (
            <div className="loading-page" style={{ minHeight: '200px' }}>
              <div className="spinner" />
              <span>Yuklanmoqda...</span>
            </div>
          ) : challenges.length === 0 ? (
            <div className="empty-state">
              <div className="icon">🏁</div>
              <h3>Hozircha faol challenge yo'q</h3>
              <p>Admin yangi challenge qo'shishini kuting</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {challenges.map((ch) => {
                const started = new Date(ch.start_date) <= now;
                const endDate = new Date(ch.end_date);
                const daysLeft = Math.ceil((endDate - now) / 86400000);

                return (
                  <div key={ch.id} className="card fade-in" style={{ position: 'relative', overflow: 'hidden' }}>
                    {/* Gradient accent bar */}
                    <div style={{
                      position: 'absolute', top: 0, left: 0, right: 0, height: '3px',
                      background: started
                        ? 'linear-gradient(90deg, var(--accent), var(--accent-2))'
                        : 'linear-gradient(90deg, var(--bg-surface1), var(--bg-surface2))',
                    }} />

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                          <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>{ch.name}</h3>
                          {started
                            ? <span className="badge badge-green">Faol</span>
                            : <span className="badge badge-gray">Kutilmoqda</span>}
                        </div>

                        {ch.description && (
                          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                            {ch.description}
                          </p>
                        )}

                        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                          <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>
                            📅 <strong style={{ color: 'var(--text-sub)' }}>{ch.total_days}</strong> kun
                          </div>
                          {started && daysLeft > 0 && (
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>
                              ⏳ <strong style={{ color: 'var(--warning)' }}>{daysLeft}</strong> kun qoldi
                            </div>
                          )}
                          {ch.prize_info && (
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>
                              🏆 <strong style={{ color: 'var(--accent-4)' }}>{ch.prize_info}</strong>
                            </div>
                          )}
                        </div>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.75rem' }}>
                        {!started && <CountdownTimer targetDate={ch.start_date} />}
                        {started && (
                          <Link
                            to={`/challenge/${ch.id}`}
                            id={`challenge-enter-${ch.id}`}
                            className="btn btn-primary"
                          >
                            Kunlarni ko'rish →
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
