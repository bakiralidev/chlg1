import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { api } from '../../api/client';
import Navbar from '../../components/Navbar';

export default function DayManager() {
  const { id: challengeId } = useParams();
  const [days, setDays] = useState([]);
  const [form, setForm] = useState({ day_number: 1, title: '', time_limit_secs: 900 });
  const [loading, setLoading] = useState(false);

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
      setDays((prev) => [...prev, { ...form }].sort((a, b) => a.day_number - b.day_number));
      setForm((prev) => ({ ...prev, day_number: prev.day_number + 1, title: '' }));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Xato');
    } finally {
      setLoading(false);
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
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem', maxWidth: '720px' }}>
          <div className="fade-in">
            <h1 style={{ fontSize: '1.6rem', marginBottom: '0.5rem' }}>📅 Kunlarni boshqarish</h1>
            <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
              Challenge ID: <code style={{ color: 'var(--accent)' }}>{challengeId}</code>
            </p>

            {/* Add day form */}
            <div className="card" style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ marginBottom: '1.25rem', fontSize: '1rem' }}>➕ Kun qo'shish</h3>
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
                    <label className="form-label" htmlFor="day-title">Sarlavha</label>
                    <input
                      id="day-title"
                      type="text"
                      name="title"
                      className="form-input"
                      placeholder="Massivlar"
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
                  {loading ? 'Qo\'shilmoqda...' : '➕ Qo\'shish'}
                </button>
              </form>
            </div>

            {/* Days list */}
            {days.length > 0 && (
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
                      </tr>
                    </thead>
                    <tbody>
                      {days.map((d) => (
                        <tr key={d.day_number}>
                          <td><strong style={{ color: 'var(--accent)' }}>#{d.day_number}</strong></td>
                          <td>{d.title || <span style={{ color: 'var(--text-dim)' }}>—</span>}</td>
                          <td>{formatTime(d.time_limit_secs)}</td>
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
