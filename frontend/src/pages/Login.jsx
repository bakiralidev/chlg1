import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { api } from '../api/client';
import { useAuthStore } from '../store/authStore';

const BOT_URL = import.meta.env.VITE_TELEGRAM_BOT_URL || 'https://t.me/pychallenge_uz_bot';

export default function Login() {
  const navigate = useNavigate();
  const loginAction = useAuthStore((s) => s.login);
  const [form, setForm] = useState({ login: '', password: '' });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.login || !form.password) {
      toast.error('Login va parolni kiriting');
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.login(form);
      const user = {
        id: data.user_id,
        login: data.login,
        username: data.username,
        full_name: data.full_name,
        is_admin: data.is_admin,
        status: data.status,
        must_change_password: data.must_change_password,
        consent_version: data.consent_version,
        rules_version: data.rules_version,
        needs_consent: data.needs_consent,
      };
      loginAction(user, data.access_token);
      toast.success('Xush kelibsiz!');
      if (data.must_change_password) {
        navigate('/set-password');
      } else {
        navigate('/dashboard');
      }
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
              <label className="form-label" htmlFor="login-username">Login</label>
              <input
                id="login-username"
                type="text"
                name="login"
                className="form-input"
                placeholder="u123456"
                value={form.login}
                onChange={handleChange}
                autoComplete="username"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="login-password">Parol (yoki bir martalik parol)</label>
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

            <button id="login-submit" type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? <span className="spinner" /> : null}
              {loading ? 'Kirish...' : 'Kirish'}
            </button>
          </form>

          <p className="auth-footer" style={{ lineHeight: 1.5 }}>
            Ro'yxatdan o'tish va parolni tiklash uchun Telegram botga o'ting:{' '}
            <a href={BOT_URL} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)', fontWeight: 600 }}>
              Telegram bot
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
