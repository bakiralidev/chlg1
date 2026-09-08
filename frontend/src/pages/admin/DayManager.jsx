import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { api } from '../../api/client';
import Navbar from '../../components/Navbar';

export default function DayManager() {
  const { id: challengeId } = useParams();
  const navigate = useNavigate();
  const [days, setDays] = useState([]);
  const [form, setForm] = useState({ day_number: 1, title: '', time_limit_secs: 900 });
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  const loadDays = () => {
    setFetching(true);
    api.getDays(challengeId)
      .then(({ data }) => {
        const sorted = data.sort((a, b) => a.day_number - b.day_number);
        setDays(sorted);
        const maxDay = sorted.length > 0 ? Math.max(...sorted.map((d) => d.day_number)) : 0;
        setForm((prev) => ({ ...prev, day_number: maxDay + 1 }));
      })
      .catch(() => toast.error('Kunlarni yuklab bo\'lmadi'))
      .finally(() => setFetching(false));
  };

  useEffect(() => {
    loadDays();
  }, [challengeId]);

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === 'number' ? Number(value) : value }));
  };

  const handleAddDay = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.addDay({ ...form, challenge_id: challengeId });
      toast.success(`Kun ${form.day_number} qo'shildi!`);
      setForm((prev) => ({ ...prev, title: '' }));
      loadDays();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Xato yuz berdi');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDay = async (dayId, dayNumber) => {
    if (!confirm(`${dayNumber}-kunni o'chirishni tasdiqlaysizmi? Unga bog'langan savollar ham o'chadi.`)) return;
    try {
      await api.deleteDay(dayId);
      toast.success(`${dayNumber}-kun o'chirildi!`);
      loadDays();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'O\'chirishda xatolik');
    }
  };

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return s > 0 ? `${m} daqiqa ${s} soniya` : `${m} daqiqa`;
  };

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem', maxWidth: '760px' }}>
          <div className="fade-in">
            <button
              onClick={() => navigate('/admin')}
              className="btn btn-ghost"
              style={{ marginBottom: '1rem', padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}
            >
              ⬅ Admin panelga qaytish
            </button>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
              <div>
                <h1 style={{ fontSize: '1.6rem', marginBottom: '0.25rem' }}>📅 Kunlarni boshqarish</h1>
                <p style={{ color: 'var(--text-muted)' }}>
                  Challenge ID: <code style={{ color: 'var(--accent)' }}>{challengeId}</code>
                </p>
              </div>
              <Link to={`/admin/challenge/${challengeId}/questions`} className="btn btn-ghost" style={{ fontSize: '0.85rem' }}>
                ❓ Savollar sahifasiga o'tish
              </Link>
            </div>

            {/* Add day form */}
            <div className="card" style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ marginBottom: '1.25rem', fontSize: '1rem' }}>➕ Yangi kun qo'shish</h3>
              <form onSubmit={handleAddDay}>
                <div className="grid-3">
                  <div className="form-group">
                    <label className="form-label" htmlFor="day-number">Kun raqami *</label>
                    <input
                      id="day-number"
                      type="number"
                      name="day_number"
                      className="form-input"
                      min={1}
                      value={form.day_number}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label" htmlFor="day-title">Mavzu / Sarlavha</label>
                    <input
                      id="day-title"
                      type="text"
                      name="title"
                      className="form-input"
                      placeholder="Massivlar va ro'yxatlar"
                      value={form.title}
                      onChange={handleChange}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label" htmlFor="day-time">Vaqt limiti (soniya) *</label>
                    <input
                      id="day-time"
                      type="number"
                      name="time_limit_secs"
                      className="form-input"
                      min={60}
                      step={60}
                      value={form.time_limit_secs}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginBottom: '1rem' }}>
                  Vaqt limiti: <strong>{formatTime(form.time_limit_secs)}</strong>
                </div>
                <button id="add-day-submit" type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? <span className="spinner" /> : null}
                  {loading ? 'Qo\'shilmoqda...' : '➕ Kunni qo\'shish'}
                </button>
              </form>
            </div>

            {/* Days list */}
            {fetching ? (
              <div className="loading-page" style={{ minHeight: '120px' }}>
                <div className="spinner" />
              </div>
            ) : days.length === 0 ? (
              <div className="empty-state card">
                <div className="icon">📅</div>
                <h3>Hozircha kunlar qo'shilmagan</h3>
                <p>Yuqoridagi formadan foydalanib birinchi kunni qo'shing.</p>
              </div>
            ) : (
              <div className="card">
                <h3 style={{ marginBottom: '1rem', fontSize: '1rem' }}>
                  Qo'shilgan kunlar ({days.length} ta)
                </h3>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Kun</th>
                        <th>Sarlavha</th>
                        <th>Vaqt limiti</th>
                        <th style={{ textAlign: 'right' }}>Amallar</th>
                      </tr>
                    </thead>
                    <tbody>
                      {days.map((d) => (
                        <tr key={d.id || d.day_number}>
                          <td><strong style={{ color: 'var(--accent)' }}>#{d.day_number}</strong></td>
                          <td>{d.title || <span style={{ color: 'var(--text-dim)' }}>—</span>}</td>
                          <td>{formatTime(d.time_limit_secs)}</td>
                          <td style={{ textAlign: 'right' }}>
                            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                              <Link
                                to={`/admin/challenge/${challengeId}/questions?dayId=${d.id}`}
                                className="btn btn-ghost"
                                style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem' }}
                              >
                                ❓ Savol qo'shish
                              </Link>
                              <button
                                onClick={() => handleDeleteDay(d.id, d.day_number)}
                                className="btn btn-danger"
                                style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem' }}
                              >
                                🗑 O'chirish
                              </button>
                            </div>
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
      </div>
    </>
  );
}
