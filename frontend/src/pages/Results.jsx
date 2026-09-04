import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { toast } from 'react-hot-toast';
import Navbar from '../components/Navbar';

export default function Results() {
  const { challengeId } = useParams();
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getLeaderboard(challengeId)
      .then(({ data }) => setLeaderboard(data))
      .catch(() => toast.error('Natijalar yuklanmadi'))
      .finally(() => setLoading(false));
  }, [challengeId]);

  const MEDAL = ['🥇', '🥈', '🥉'];

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem', maxWidth: '800px' }}>
          <div className="fade-in">
            <div className="section-title">
              <h2>🏆 Natijalar Jadvali</h2>
            </div>

            {loading ? (
              <div className="loading-page" style={{ minHeight: '200px' }}>
                <div className="spinner" />
              </div>
            ) : leaderboard.length === 0 ? (
              <div className="empty-state">
                <div className="icon">⏳</div>
                <h3>Challenge hali tugamagan</h3>
                <p>Natijalar challenge yakunlanganidan keyin ko'rinadi</p>
                <Link to={`/challenge/${challengeId}`} className="btn btn-secondary" style={{ marginTop: '1rem', display: 'inline-flex' }}>
                  Roadmapga qaytish
                </Link>
              </div>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>O'rin</th>
                      <th>Foydalanuvchi</th>
                      <th>Bajarilgan kunlar</th>
                      <th>Umumiy ball</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.map((entry, i) => (
                      <tr key={entry.user_id} style={{
                        background: i === 0 ? 'rgba(250,179,135,0.05)' : 'transparent',
                      }}>
                        <td>
                          <span style={{ fontSize: '1.2rem' }}>
                            {MEDAL[i] || `#${entry.rank}`}
                          </span>
                        </td>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                            {entry.username}
                          </div>
                          {entry.is_winner && (
                            <span className="badge badge-yellow" style={{ marginTop: '0.25rem' }}>G'olib</span>
                          )}
                        </td>
                        <td>
                          <span style={{ color: 'var(--accent)' }}>{entry.days_completed}</span>
                          <span style={{ color: 'var(--text-dim)' }}> kun</span>
                        </td>
                        <td>
                          <strong style={{ color: 'var(--success)', fontSize: '1.05rem' }}>
                            {entry.total_score}
                          </strong>
                          <span style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}> ball</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
