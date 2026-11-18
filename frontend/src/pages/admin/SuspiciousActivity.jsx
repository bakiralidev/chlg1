import { useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';
import { api } from '../../api/client';
import Navbar from '../../components/Navbar';
import AdminNav from '../../components/AdminNav';

export default function SuspiciousActivity() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSuspiciousActivity()
      .then(({ data: res }) => setData(res))
      .catch(() => toast.error("Shubhali holatlarni yuklab bo'lmadi"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem' }}>
          <AdminNav />
          <h1 style={{ fontSize: '1.6rem', marginBottom: '0.75rem' }}>🕵️ Shubhali holatlar hisoboti</h1>
          <div style={{
            padding: '0.85rem 1rem',
            borderRadius: '8px',
            background: 'rgba(250, 179, 135, 0.12)',
            border: '1px solid var(--warning)',
            color: 'var(--warning)',
            fontSize: '0.9rem',
            marginBottom: '1.5rem',
          }}>
            ⚠️ {data?.warning || "Diqqat: bir xil IP manzil — ayni xonadon yoki umumiy tarmoq bo'lishi mumkin. Bu sahifa faqat ko'rish uchun, avtomatik diskvalifikatsiya qilinmaydi."}
          </div>

          {loading ? (
            <div className="loading-page" style={{ minHeight: '200px' }}><div className="spinner" /></div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div className="card">
                <h3 style={{ marginBottom: '0.75rem' }}>🌐 Bir xil IP + User-Agent guruhlari ({data?.shared_ip_ua?.length || 0})</h3>
                {(!data?.shared_ip_ua || data.shared_ip_ua.length === 0) ? (
                  <p style={{ color: 'var(--text-dim)' }}>Topilmadi</p>
                ) : (
                  data.shared_ip_ua.map((grp, i) => (
                    <div key={i} style={{ padding: '0.75rem', borderBottom: '1px solid var(--bg-surface0)' }}>
                      <div><strong>IP:</strong> {grp.ip}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>{grp.user_agent}</div>
                      <div style={{ marginTop: '0.35rem' }}>
                        {grp.users.map((u) => (
                          <span key={u.user_id} className="badge badge-blue" style={{ marginRight: '0.4rem' }}>
                            {u.login} ({u.full_name})
                          </span>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="card">
                <h3 style={{ marginBottom: '0.75rem' }}>🧬 O'xshash yechimlar (&ge; 90%) ({data?.similar_solutions?.length || 0})</h3>
                {(!data?.similar_solutions || data.similar_solutions.length === 0) ? (
                  <p style={{ color: 'var(--text-dim)' }}>Topilmadi</p>
                ) : (
                  data.similar_solutions.map((item, i) => (
                    <div key={i} style={{ padding: '0.6rem 0', borderBottom: '1px solid var(--bg-surface0)' }}>
                      <strong>{item.question_title}</strong> — {Math.round(item.similarity * 100)}% o'xshash:{' '}
                      <code>{item.user_a.login}</code> ↔ <code>{item.user_b.login}</code>
                    </div>
                  ))
                )}
              </div>

              <div className="card">
                <h3 style={{ marginBottom: '0.75rem' }}>⚡ Juda tez yuborilgan yechimlar ({data?.fast_solutions?.length || 0})</h3>
                {(!data?.fast_solutions || data.fast_solutions.length === 0) ? (
                  <p style={{ color: 'var(--text-dim)' }}>Topilmadi</p>
                ) : (
                  data.fast_solutions.map((item, i) => (
                    <div key={i} style={{ padding: '0.6rem 0', borderBottom: '1px solid var(--bg-surface0)' }}>
                      <code>{item.user_login}</code> — <strong>{item.question_title}</strong>: {item.time_spent_secs}s (ball: {item.score})
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
