import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import { toast } from 'react-hot-toast';
import Navbar from '../../components/Navbar';
import AdminNav from '../../components/AdminNav';

export default function AdminDashboard() {
  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Admin uchun barcha challengelar (draft ham)
    api.getAdminChallenges()
      .then(({ data }) => setChallenges(data))
      .catch(() => toast.error('Challengelar yuklanmadi'))
      .finally(() => setLoading(false));
  }, []);

  const handleActivate = async (id, name) => {
    if (!confirm(`"${name}" ni faollashtirmoqchimisiz?`)) return;
    try {
      await api.activateChallenge(id);
      toast.success('Challenge faollashtirildi!');
      setChallenges((prev) =>
        prev.map((c) => c.id === id ? { ...c, status: 'active' } : c)
      );
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Xato');
    }
  };

  const handleFinalize = async (id, name) => {
    if (!confirm(`"${name}" ni yakunlamoqchimisiz? Natijalar hisoblanadi.`)) return;
    try {
      await api.finalizeChallenge(id);
      toast.success('Challenge yakunlandi!');
      setChallenges((prev) =>
        prev.map((c) => c.id === id ? { ...c, status: 'ended' } : c)
      );
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Xato');
    }
  };

  const handleDelete = async (id, name) => {
    if (!confirm(`"${name}" challengeni butunlay o'chirmoqchimisiz? Barcha kunlar va savollar o'chib ketadi!`)) return;
    try {
      await api.deleteChallenge(id);
      toast.success('Challenge o\'chirildi');
      setChallenges((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'O\'chirishda xatolik');
    }
  };

  const handleDownloadZip = async (id, name) => {
    try {
      toast('ZIP tayyorlanmoqda...', { icon: '📦' });
      const response = await api.exportSubmissionsZip(id);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${name.replace(/ /g, '_')}_submissions.zip`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('ZIP yuklab olishda xato');
    }
  };

  const STATUS_BADGE = {
    draft:  <span className="badge badge-gray">Draft</span>,
    active: <span className="badge badge-green">Faol</span>,
    ended:  <span className="badge badge-purple">Yakunlangan</span>,
  };

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem' }}>
          <AdminNav />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
            <div>
              <h1 style={{ fontSize: '1.8rem', marginBottom: '0.25rem' }}>👑 Admin Panel</h1>
              <p style={{ color: 'var(--text-muted)' }}>Challengelar, ishtirokchilar va natijalarni boshqarish</p>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <Link to="/admin/challenge/new" id="create-challenge-btn" className="btn btn-primary">
                + Yangi Challenge
              </Link>
            </div>
          </div>

          {loading ? (
            <div className="loading-page" style={{ minHeight: '200px' }}>
              <div className="spinner" />
            </div>
          ) : challenges.length === 0 ? (
            <div className="empty-state">
              <div className="icon">📋</div>
              <h3>Challenge yo'q</h3>
              <p>Birinchi challengeni yarating</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {challenges.map((ch) => (
                <div key={ch.id} className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                        <h3 style={{ fontSize: '1.15rem' }}>{ch.name}</h3>
                        {STATUS_BADGE[ch.status] || <span className="badge badge-gray">{ch.status}</span>}
                      </div>
                      <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.85rem', color: 'var(--text-dim)', flexWrap: 'wrap' }}>
                        <span>📅 {ch.total_days} kun</span>
                        <span>🗓 {new Date(ch.start_date).toLocaleDateString('uz-UZ')}</span>
                        {ch.prize_info && <span>🏆 {ch.prize_info}</span>}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <Link
                        to={`/admin/submissions?challenge_id=${ch.id}`}
                        className="btn btn-secondary"
                        style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem' }}
                      >
                        📝 Yechimlar & Baholash
                      </Link>
                      <button
                        className="btn btn-ghost"
                        style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem' }}
                        onClick={() => handleDownloadZip(ch.id, ch.name)}
                        title="Barcha topshirilgan yechimlarni ZIP arxiv holatida yuklab olish"
                      >
                        📦 ZIP
                      </button>
                      <Link
                        to={`/admin/challenge/${ch.id}/days`}
                        id={`manage-days-${ch.id}`}
                        className="btn btn-ghost"
                        style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem' }}
                      >
                        📅 Kunlar
                      </Link>
                      <Link
                        to={`/admin/challenge/${ch.id}/questions`}
                        id={`manage-questions-${ch.id}`}
                        className="btn btn-ghost"
                        style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem' }}
                      >
                        ❓ Savollar
                      </Link>
                      <Link
                        to={`/admin/challenge/${ch.id}/edit`}
                        id={`edit-challenge-${ch.id}`}
                        className="btn btn-ghost"
                        style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem' }}
                      >
                        ✏️ Tahrirlash
                      </Link>
                      {ch.status === 'draft' && (
                        <button
                          id={`activate-challenge-${ch.id}`}
                          className="btn btn-primary"
                          style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem' }}
                          onClick={() => handleActivate(ch.id, ch.name)}
                        >
                          ▶ Faollashtirish
                        </button>
                      )}
                      {ch.status === 'active' && (
                        <button
                          id={`finalize-challenge-${ch.id}`}
                          className="btn btn-danger"
                          style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem' }}
                          onClick={() => handleFinalize(ch.id, ch.name)}
                        >
                          🏁 Yakunlash
                        </button>
                      )}
                      <button
                        id={`delete-challenge-${ch.id}`}
                        className="btn btn-ghost"
                        style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem', color: 'var(--danger)' }}
                        onClick={() => handleDelete(ch.id, ch.name)}
                      >
                        🗑 O'chirish
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
