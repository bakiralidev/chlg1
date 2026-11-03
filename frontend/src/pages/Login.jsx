import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { api } from '../api/client';
import { useAuthStore } from '../store/authStore';

export default function Login() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [form, setForm] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.email || !form.password) {
      toast.error('Email va parolni kiriting');
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.login(form);
      const user = {
        id: data.user_id,
        username: data.username,
        is_admin: data.is_admin,
      };
      login(user, data.access_token);
      toast.success("Xush kelibsiz!");
      navigate('/dashboard');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Kirish xatosi';
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
            <h1>🐍 PyChallenge</h1>
            <p>30 Kunlik Python Challenge Platformasi</p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="login-email">Email</label>
              <input
                id="login-email"
                type="email"
                name="email"
                className="form-input"
                placeholder="email@example.com"
                value={form.email}
                onChange={handleChange}
                autoComplete="email"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="login-password">Parol</label>
              <input
                id="login-password"
                type="password"
                name="password"
                className="form-input"
                placeholder="••••••••"
                value={form.password}
                onChange={handleChange}
                autoComplete="current-password"
                required
              />
            </div>

            <div style={{ textAlign: 'right', marginBottom: '1.2rem' }}>
              <Link to="/forgot-password" style={{ fontSize: '0.85rem' }}>
                Parolni unutdingizmi?
              </Link>
            </div>

            <button id="login-submit" type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? <span className="spinner" /> : null}
              {loading ? 'Kirish...' : 'Kirish'}
            </button>
          </form>

          <p className="auth-footer">
            Akkauntingiz yo'qmi?{' '}
            <Link to="/register">Ro'yxatdan o'ting</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
