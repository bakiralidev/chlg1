import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { api } from '../api/client';

export default function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [form, setForm] = useState({ password: '', confirm: '' });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      toast.error('Parollar mos kelmadi');
      return;
    }
    if (form.password.length < 6) {
      toast.error('Parol kamida 6 belgidan iborat bo\'lishi kerak');
      return;
    }
    setLoading(true);
    try {
      await api.resetPassword({ token, new_password: form.password });
      toast.success('Parol muvaffaqiyatli yangilandi!');
      navigate('/login');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Havola yaroqsiz yoki muddati o\'tgan');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="page-centered">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <p style={{ color: 'var(--danger)' }}>⚠️ Yaroqsiz havola</p>
          <Link to="/login" className="btn btn-secondary" style={{ marginTop: '1rem', display: 'inline-flex' }}>
            Loginга qaytish
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page-centered">
      <div className="auth-wrapper fade-in">
        <div className="auth-card">
          <div className="auth-logo">
            <h1>🔐 Yangi parol</h1>
            <p>Yangi parolingizni kiriting</p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="reset-password">Yangi parol</label>
              <input
                id="reset-password"
                type="password"
                name="password"
                className="form-input"
                placeholder="••••••••"
                value={form.password}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="reset-confirm">Parolni tasdiqlang</label>
              <input
                id="reset-confirm"
                type="password"
                name="confirm"
                className="form-input"
                placeholder="••••••••"
                value={form.confirm}
                onChange={handleChange}
                required
              />
            </div>
            <button id="reset-submit" type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? <span className="spinner" /> : null}
              {loading ? 'Saqlanmoqda...' : 'Parolni yangilash'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
