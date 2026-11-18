import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { api } from '../api/client';
import { useAuthStore } from '../store/authStore';

export default function ConsentModal() {
  const { user, updateUser, logout } = useAuthStore();
  const [loading, setLoading] = useState(false);

  const handleAgree = async () => {
    setLoading(true);
    try {
      const { data } = await api.acceptConsent();
      updateUser({
        consent_version: data.consent_version,
        rules_version: data.rules_version,
        needs_consent: false,
      });
      toast.success('Qoidalarga rozilik saqlandi');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Xatolik yuz berdi');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(10, 10, 20, 0.85)',
      backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '1rem',
    }}>
      <div className="card" style={{ maxWidth: '560px', width: '100%', padding: '2rem' }}>
        <h2 style={{ marginBottom: '0.75rem' }}>
          📋 Yangilangan qoidalar (v{user?.rules_version || 1})
        </h2>
        <p style={{ color: 'var(--text-sub)', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '1rem' }}>
          Platformadan foydalanishni davom ettirish uchun PyChallenge musobaqasining joriy qoidalari bilan
          tanishib, rozilik bildirishingiz shart:
        </p>
        <ul style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.7, paddingLeft: '1.25rem', marginBottom: '1.5rem' }}>
          <li>Har bir kunlik topshiriq Toshkent vaqti bilan 00:00 da ochiladi.</li>
          <li>Topshiriqlarni mustaqil bajarish shart; anti-cheat qoidalarini buzish diskvalifikatsiyaga olib keladi.</li>
          <li>Mukofot karta egasining ismi ro'yxatdan o'tishdagi ism-familiya bilan mos bo'lishi kerak.</li>
        </ul>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <button type="button" className="btn btn-ghost" onClick={logout} disabled={loading}>
            Chiqish
          </button>
          <button type="button" className="btn btn-primary" onClick={handleAgree} disabled={loading}>
            {loading ? 'Saqlanmoqda...' : '✅ Roziman'}
          </button>
        </div>
      </div>
    </div>
  );
}
