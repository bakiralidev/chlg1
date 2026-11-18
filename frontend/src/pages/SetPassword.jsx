import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { api } from '../api/client';
import { useAuthStore } from '../store/authStore';

export default function SetPassword() {
  const navigate = useNavigate();
  const { isAuthenticated, user, updateUser } = useAuthStore();
  const [form, setForm] = useState({ password: '', confirm: '' });
  const [loading, setLoading] = useState(false);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user && !user.must_change_password) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      toast.error('Parollar mos kelmadi');
      return;
    }
    if (form.password.length < 8 || !/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) {
      toast.error("Parol kamida 8 belgi, harf va raqamdan iborat bo'lishi kerak");
      return;
    }

    setLoading(true);
    try {
      await api.setPassword(form.password);
      updateUser({ must_change_password: false });
      toast.success("Yangi parol o'rnatildi!");
      navigate('/dashboard');
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail[0]?.msg : (detail || 'Xato yuz berdi');
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-centered" style={{ background: 'radial-gradient(ellipse at top, #1a1a2e 0%, var(--bg-base) 70%)' }}>
      <div className="auth-wrapper fade-in">
        <div className="auth-card">
          <div className="auth-logo">
            <h1>🔐 Yangi parol o'rnatish</h1>
            <p>Davom etish uchun doimiy parolingizni o'rnating</p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="set-password">Yangi parol (kamida 8 belgi, harf va raqam)</label>
              <input
                id="set-password"
                type="password"
                name="password"
                className="form-input"
                placeholder="••••••••"
                value={form.password}
                onChange={handleChange}
                autoComplete="new-password"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="set-confirm">Parolni tasdiqlang</label>
              <input
                id="set-confirm"
                type="password"
                name="confirm"
                className="form-input"
                placeholder="••••••••"
                value={form.confirm}
                onChange={handleChange}
                autoComplete="new-password"
                required
              />
            </div>

            <button id="set-password-submit" type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? <span className="spinner" /> : null}
              {loading ? 'Saqlanmoqda...' : 'Parolni saqlash'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
