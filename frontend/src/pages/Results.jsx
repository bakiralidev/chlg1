import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import Navbar from '../components/Navbar';

export default function Results() {
  const { challengeId } = useParams();
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lockedMsg, setLockedMsg] = useState('');

  useEffect(() => {
    api.getLeaderboard(challengeId)
      .then(({ data }) => {
        setLeaderboard(data.leaderboard || []);
      })
      .catch((err) => {
        setLockedMsg(err.response?.data?.detail || 'Challenge hali tugamagan');
      })
      .finally(() => setLoading(false));
  }, [challengeId]);

  const MEDAL = ['🥇', '🥈', '🥉'];

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem', maxWidth: '840px' }}>
          <div className="fade-in">
            <div className="section-title">
              <h2>🏆 Natijalar Jadvali</h2>
            </div>

            {loading ? (
              <div className="loading-page" style={{ minHeight: '200px' }}>
                <div className="spinner" />
              </div>
            ) : lockedMsg || leaderboard.length === 0 ? (
              <div className="empty-state">
                <div className="icon">⏳</div>
                <h3>{lockedMsg || 'Challenge hali tugamagan'}</h3>
                <p>To'liq natijalar jadvali challenge yakunlanganidan keyin ochiladi</p>
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
                    {leaderboard.map((entry) => (
                      <tr key={entry.user_id} style={{
                        background: entry.rank === 1 ? 'rgba(250,179,135,0.05)' : 'transparent',
                      }}>
                        <td>
                          <span style={{ fontSize: '1.15rem' }}>
                            {entry.rank <= 3 ? MEDAL[entry.rank - 1] : `#${entry.rank}`}
                          </span>
                          {entry.is_tie && (
                            <span className="badge badge-purple" style={{ marginLeft: '0.4rem', fontSize: '0.7rem' }}>Tenglik</span>
                          )}
                        </td>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                            {entry.full_name || entry.username}
                          </div>
                          {entry.is_winner && (
                            <span className="badge badge-yellow" style={{ marginTop: '0.25rem' }}>
                              G'olib {entry.prize_amount ? `(${entry.prize_amount.toLocaleString()} so'm)` : ''}
                            </span>
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
