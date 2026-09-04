import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { api } from '../api/client';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.forgotPassword(email);
      setSent(true);
      toast.success('Havolani emailga yubordik!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Xato yuz berdi');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-centered">
      <div className="auth-wrapper fade-in">
        <div className="auth-card">
          <div className="auth-logo">
            <h1>🔑 Parolni tiklash</h1>
            <p>Emailingizga havola yuboramiz</p>
          </div>

          {sent ? (
            <div style={{ textAlign: 'center', padding: '1rem 0' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📧</div>
              <h3 style={{ color: 'var(--success)', marginBottom: '0.5rem' }}>Yuborildi!</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                <strong>{email}</strong> manziliga tiklash havolasini yubordik.
                Spam papkasini ham tekshiring.
              </p>
              <Link to="/login" className="btn btn-secondary" style={{ marginTop: '1.5rem', display: 'inline-flex' }}>
                Loginга qaytish
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label" htmlFor="forgot-email">Email manzilingiz</label>
                <input
                  id="forgot-email"
                  type="email"
                  className="form-input"
                  placeholder="email@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <button id="forgot-submit" type="submit" className="btn btn-primary btn-full" disabled={loading}>
                {loading ? <span className="spinner" /> : null}
                {loading ? 'Yuborilmoqda...' : 'Havola yuborish'}
              </button>
              <p className="auth-footer" style={{ marginTop: '1rem' }}>
                <Link to="/login">← Loginга qaytish</Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
