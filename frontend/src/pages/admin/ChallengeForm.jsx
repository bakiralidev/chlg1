import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { api } from '../../api/client';
import Navbar from '../../components/Navbar';

export default function ChallengeForm() {
  const { id } = useParams(); // undefined = yangi, mavjud = tahrirlash
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [form, setForm] = useState({
    name: '',
    description: '',
    total_days: 30,
    start_date: '',
    prize_info: '',
    max_violations: 3,
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isEdit) {
      setLoading(true);
      api.getAdminChallenge(id)
        .then(({ data }) => {
          let dateStr = '';
          if (data.start_date) {
            const d = new Date(data.start_date);
            const pad = (n) => String(n).padStart(2, '0');
            dateStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
          }
          setForm({
            name: data.name || '',
            description: data.description || '',
            total_days: data.total_days || 30,
            start_date: dateStr,
            prize_info: data.prize_info || '',
            max_violations: data.max_violations ?? 3,
          });
        })
        .catch(() => {
          toast.error('Challenge ma\'lumotlarini yuklab bo\'lmadi');
        })
        .finally(() => setLoading(false));
    }
  }, [id, isEdit]);

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === 'number' ? Number(value) : value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.start_date) {
      toast.error('Nom va boshlanish sanasini kiriting');
      return;
    }
    setLoading(true);
    try {
      const payload = {
        ...form,
        start_date: new Date(form.start_date).toISOString(),
      };
      if (isEdit) {
        await api.updateChallenge(id, payload);
        toast.success('Challenge yangilandi!');
      } else {
        await api.createChallenge(payload);
        toast.success('Challenge yaratildi!');
      }
      navigate('/admin');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Xato yuz berdi');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem', maxWidth: '640px' }}>
          <div className="fade-in">
            <button
              onClick={() => navigate('/admin')}
              className="btn btn-ghost"
              style={{ marginBottom: '1rem', padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}
            >
              ⬅ Admin panelga qaytish
            </button>
            <h1 style={{ fontSize: '1.6rem', marginBottom: '0.5rem' }}>
              {isEdit ? '✏️ Challengeni tahrirlash' : '+ Yangi Challenge yaratish'}
            </h1>
            <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
              {isEdit ? 'Ma\'lumotlarni yangilang' : 'Yangi challenge ma\'lumotlarini kiriting'}
            </p>

            <div className="card">
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label className="form-label" htmlFor="ch-name">Challenge nomi *</label>
                  <input
                    id="ch-name"
                    type="text"
                    name="name"
                    className="form-input"
                    placeholder="Python Challenge #1"
                    value={form.name}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="ch-desc">Tavsif</label>
                  <textarea
                    id="ch-desc"
                    name="description"
                    className="form-input"
                    placeholder="Challenge haqida qisqacha ma'lumot..."
                    value={form.description}
                    onChange={handleChange}
                    rows={3}
                  />
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label" htmlFor="ch-days">Kunlar soni *</label>
                    <input
                      id="ch-days"
                      type="number"
                      name="total_days"
                      className="form-input"
                      min={1}
                      max={90}
                      value={form.total_days}
                      onChange={handleChange}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="ch-violations">Max buzilish soni</label>
                    <input
                      id="ch-violations"
                      type="number"
                      name="max_violations"
                      className="form-input"
                      min={1}
                      max={10}
                      value={form.max_violations}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="ch-start">Boshlanish sanasi *</label>
                  <input
                    id="ch-start"
                    type="datetime-local"
                    name="start_date"
                    className="form-input"
                    value={form.start_date}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="ch-prize">Mukofot ma'lumoti</label>
                  <input
                    id="ch-prize"
                    type="text"
                    name="prize_info"
                    className="form-input"
                    placeholder="1 million so'm naqd pul"
                    value={form.prize_info}
                    onChange={handleChange}
                  />
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                  <button
                    id="challenge-form-submit"
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading}
                  >
                    {loading ? <span className="spinner" /> : null}
                    {loading ? 'Saqlanmoqda...' : isEdit ? 'Yangilash' : 'Yaratish'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => navigate('/admin')}
                  >
                    Bekor qilish
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
