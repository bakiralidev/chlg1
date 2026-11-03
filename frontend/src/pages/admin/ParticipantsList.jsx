import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { toast } from 'react-hot-toast';
import Navbar from '../../components/Navbar';
import AdminNav from '../../components/AdminNav';

export default function ParticipantsList() {
  const navigate = useNavigate();
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const fetchParticipants = (searchQuery = '') => {
    setLoading(true);
    api.getParticipants({ search: searchQuery || undefined })
      .then(({ data }) => setParticipants(data))
      .catch(() => toast.error('Ishtirokchilar ro\'yxatini yuklab bo\'lmadi'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchParticipants();
  }, []);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchParticipants(search);
  };

  const totalSubmissions = participants.reduce((acc, p) => acc + (p.submissions_count || 0), 0);
  const totalDq = participants.reduce((acc, p) => acc + (p.disqualified_count || 0), 0);

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem' }}>
          <AdminNav />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '0.25rem' }}>
                👥 Ishtirokchilar
              </h1>
              <p style={{ color: 'var(--text-muted)' }}>
                Platformada ro'yxatdan o'tgan barcha talabalar va ularning faolligi
              </p>
            </div>

            <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                placeholder="Ism yoki email bo'yicha qidirish..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{
                  padding: '0.55rem 1rem',
                  background: 'var(--bg-surface0)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 8,
                  color: 'var(--text-main)',
                  width: '280px',
                  fontSize: '0.9rem',
                  outline: 'none',
                }}
              />
              <button type="submit" className="btn btn-secondary">
                🔍 Qidirish
              </button>
            </form>
          </div>

          {/* Stat cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '1rem',
            marginBottom: '2rem',
          }}>
            <div className="card" style={{ padding: '1.25rem', textAlign: 'center', background: 'var(--bg-mantle)' }}>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent)' }}>
                {participants.length}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                Jami Ro'yxatdan O'tganlar
              </div>
            </div>
            <div className="card" style={{ padding: '1.25rem', textAlign: 'center', background: 'var(--bg-mantle)' }}>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--success)' }}>
                {totalSubmissions}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                Topshirilgan Yechimlar
              </div>
            </div>
            <div className="card" style={{ padding: '1.25rem', textAlign: 'center', background: 'var(--bg-mantle)' }}>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--danger)' }}>
                {totalDq}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                Qayd Etilgan Diskvalifikatsiyalar
              </div>
            </div>
          </div>

          {/* Table */}
          {loading ? (
            <div className="loading-page" style={{ minHeight: '200px' }}>
              <div className="spinner" />
              <span>Yuklanmoqda...</span>
            </div>
          ) : participants.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              Ishtirokchilar topilmadi
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: 'hidden', border: '1px solid var(--border-color)' }}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-surface0)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      <th style={{ padding: '1rem 1.25rem' }}>ISHTIROKCHI</th>
                      <th style={{ padding: '1rem' }}>RO'YXATDAN O'TGAN</th>
                      <th style={{ padding: '1rem', textAlign: 'center' }}>YECHIMLAR</th>
                      <th style={{ padding: '1rem', textAlign: 'center' }}>QOIDABUZARLIK</th>
                      <th style={{ padding: '1rem', textAlign: 'center' }}>JAMI BALL</th>
                      <th style={{ padding: '1rem 1.25rem', textAlign: 'right' }}>AMALLAR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {participants.map((p, idx) => (
                      <tr
                        key={p.id}
                        style={{
                          borderBottom: idx === participants.length - 1 ? 'none' : '1px solid var(--bg-surface0)',
                          transition: 'background 0.15s',
                        }}
                      >
                        <td style={{ padding: '1rem 1.25rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <div style={{
                              width: 38,
                              height: 38,
                              borderRadius: '50%',
                              background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontWeight: 700,
                              color: '#fff',
                              fontSize: '0.95rem',
                              flexShrink: 0,
                            }}>
                              {p.username?.[0]?.toUpperCase() || 'U'}
                            </div>
                            <div>
                              <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.95rem' }}>
                                {p.username}
                              </div>
                              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                {p.email}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {new Date(p.created_at).toLocaleDateString('uz-UZ', { year: 'numeric', month: 'short', day: 'numeric' })}
                        </td>
                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                          <span className="badge badge-purple" style={{ fontSize: '0.85rem' }}>
                            {p.submissions_count} ta
                          </span>
                        </td>
                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                          {p.disqualified_count > 0 ? (
                            <span className="badge badge-danger">
                              🚫 {p.disqualified_count} marta DQ
                            </span>
                          ) : (
                            <span style={{ color: 'var(--success)', fontSize: '0.85rem' }}>
                              ✅ Qoida buzmagan
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                          <span className="badge badge-green" style={{ fontSize: '0.95rem', fontWeight: 700, padding: '0.35rem 0.75rem' }}>
                            ⭐ {p.total_score} ball
                          </span>
                        </td>
                        <td style={{ padding: '1rem 1.25rem', textAlign: 'right' }}>
                          <button
                            onClick={() => navigate(`/admin/submissions?user_id=${p.id}`)}
                            className="btn btn-secondary"
                            style={{ padding: '0.45rem 0.9rem', fontSize: '0.85rem' }}
                          >
                            📝 Yechimlarini ko'rish
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

