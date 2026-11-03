import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { api } from '../api/client';
import { useAuthStore } from '../store/authStore';

export default function Register() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [form, setForm] = useState({ username: '', email: '', password: '', confirm: '' });
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
      const { data } = await api.register({
        username: form.username,
        email: form.email,
        password: form.password,
      });
      const user = {
        id: data.user_id,
        username: data.username,
        is_admin: data.is_admin,
      };
      login(user, data.access_token);
      toast.success('Ro\'yxatdan o\'tdingiz!');
      navigate('/dashboard');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Ro\'yxatdan o\'tish xatosi';
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
            <p>Yangi akkaunt yaratish</p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="reg-username">Foydalanuvchi nomi</label>
              <input
                id="reg-username"
                type="text"
                name="username"
                className="form-input"
                placeholder="john_doe"
                value={form.username}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="reg-email">Email</label>
              <input
                id="reg-email"
                type="email"
                name="email"
                className="form-input"
                placeholder="email@example.com"
                value={form.email}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="reg-password">Parol</label>
              <input
                id="reg-password"
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
              <label className="form-label" htmlFor="reg-confirm">Parolni tasdiqlang</label>
              <input
                id="reg-confirm"
                type="password"
                name="confirm"
                className="form-input"
                placeholder="••••••••"
                value={form.confirm}
                onChange={handleChange}
                required
              />
            </div>

            <button id="register-submit" type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? <span className="spinner" /> : null}
              {loading ? 'Ro\'yxatdan o\'tilmoqda...' : 'Ro\'yxatdan o\'tish'}
            </button>
          </form>

          <p className="auth-footer">
            Akkauntingiz bormi? <Link to="/login">Kirish</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
