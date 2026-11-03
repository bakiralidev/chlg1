import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { api } from '../../api/client';
import { toast } from 'react-hot-toast';
import Navbar from '../../components/Navbar';
import AdminNav from '../../components/AdminNav';

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0s';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

function GradeModal({ submissionId, onClose, onGraded }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [score, setScore] = useState(0);
  const [result, setResult] = useState('graded');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.getSubmissionDetail(submissionId)
      .then(({ data: sub }) => {
        setData(sub);
        setScore(sub.score || 0);
        setResult(sub.result || (sub.score >= 60 ? 'pass' : 'graded'));
      })
      .catch((err) => {
        toast.error(err.response?.data?.detail || 'Ma\'lumotlarni yuklab bo\'lmadi');
        onClose();
      })
      .finally(() => setLoading(false));
  }, [submissionId, onClose]);

  const handleSave = async (e) => {
    e.preventDefault();
    const numScore = parseInt(score, 10);
    if (isNaN(numScore) || numScore < 0 || numScore > 100) {
      toast.error('Ball 0 dan 100 gacha bo\'lishi kerak');
      return;
    }

    setSaving(true);
    try {
      const res = await api.gradeSubmission(submissionId, {
        score: numScore,
        result,
        notes: notes.trim() || undefined,
      });
      toast.success(res.data?.message || 'Yechim muvaffaqiyatli baholandi!');
      onGraded(submissionId, numScore, result);
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Baholashda xatolik yuz berdi');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="modal-overlay">
        <div className="modal" style={{ maxWidth: 500, textAlign: 'center', padding: '3rem' }}>
          <div className="spinner" />
          <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>Yuklanmoqda...</p>
        </div>
      </div>
    );
  }

  const isPractical = data.question?.question_type === 'practical';

  return (
    <div className="modal-overlay" style={{ padding: '1rem', zIndex: 1000 }}>
      <div className="modal fade-in" style={{
        maxWidth: 960,
        width: '100%',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        padding: 0,
        overflow: 'hidden',
        border: '1px solid var(--border-color)',
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '1.25rem 1.75rem',
          background: 'var(--bg-surface0)',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexShrink: 0,
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontSize: '1.2rem' }}>{isPractical ? '🖥️' : '📝'}</span>
              <h3 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--text-main)', fontWeight: 700 }}>
                {data.day?.day_number}-kun: {data.question?.title}
              </h3>
              <span className={`badge ${isPractical ? 'badge-blue' : 'badge-purple'}`}>
                {isPractical ? 'Amaliy' : 'Nazariy'}
              </span>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Ishtirokchi: <strong>{data.user?.username}</strong> ({data.user?.email}) · Topshirildi: {data.submitted_at ? new Date(data.submitted_at).toLocaleString('uz-UZ') : 'Topshirilmagan'}
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn btn-ghost"
            style={{ fontSize: '1.2rem', padding: '0.25rem 0.6rem', color: 'var(--text-muted)' }}
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Savol sharti */}
          <div style={{ background: 'var(--bg-mantle)', borderRadius: 10, padding: '1.25rem', border: '1px solid var(--bg-surface0)' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent)', marginBottom: '0.5rem' }}>
              📋 SAVOL MATNI:
            </div>
            {data.question?.body_text ? (
              <div
                dangerouslySetInnerHTML={{ __html: data.question.body_text }}
                style={{ lineHeight: 1.6, color: 'var(--text-main)', fontSize: '0.95rem' }}
              />
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>Savol matni mavjud emas</p>
            )}
          </div>

          {/* Ishtirokchi yechimi */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-2)' }}>
                {isPractical ? '🐍 ISHTIROKCHI YOZGAN KODI:' : '📝 ISHTIROKCHI JAVOBI (NOTE):'}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Sarflangan vaqt: <strong>{formatDuration(data.time_spent_secs)}</strong> · Qoidabuzarliklar: <strong>{data.violations_count || 0} ta</strong>
              </div>
            </div>

            {isPractical ? (
              <div style={{ height: '260px', border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
                <Editor
                  height="100%"
                  language="python"
                  theme="vs-dark"
                  value={data.code || '# Kod yozilmagan'}
                  options={{ readOnly: true, fontSize: 13, minimap: { enabled: false } }}
                />
              </div>
            ) : (
              <div style={{
                background: 'var(--bg-surface0)',
                border: '1px solid var(--border-color)',
                borderRadius: 8,
                padding: '1.25rem',
                minHeight: '120px',
                whiteSpace: 'pre-wrap',
                color: 'var(--text-main)',
                fontSize: '0.95rem',
                lineHeight: 1.6,
              }}>
                {data.note_content || 'Javob matni kiritilmagan.'}
              </div>
            )}

            {isPractical && data.note_content && (
              <div style={{ marginTop: '0.75rem', background: 'var(--bg-surface0)', padding: '0.75rem 1rem', borderRadius: 8, fontSize: '0.9rem' }}>
                <span style={{ color: 'var(--accent)', fontWeight: 600 }}>Izoh: </span>
                <span style={{ color: 'var(--text-secondary)' }}>{data.note_content}</span>
              </div>
            )}
          </div>

          {/* Qoidabuzarliklar jurnali */}
          {data.violations?.length > 0 && (
            <div style={{ background: 'rgba(243, 139, 168, 0.1)', border: '1px solid var(--danger)', borderRadius: 8, padding: '0.75rem 1rem' }}>
              <div style={{ color: 'var(--danger)', fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                ⚠️ Qayd etilgan qoidabuzarliklar ({data.violations.length} ta):
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                {data.violations.map((v, i) => (
                  <li key={i}>
                    {v.violation_type} — {new Date(v.created_at).toLocaleTimeString('uz-UZ')}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* AI baholar (agar mavjud bo'lsa) */}
          {data.ai_scores?.length > 0 && (
            <div style={{ background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.25)', borderRadius: 8, padding: '0.75rem 1rem' }}>
              <div style={{ color: 'var(--accent)', fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                🤖 AI Agent Baholari:
              </div>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                {data.ai_scores.map((s, i) => (
                  <span key={i} className="badge badge-purple" style={{ fontSize: '0.8rem' }}>
                    {s.category}: {s.score}/10
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Baholash formasi */}
          <form onSubmit={handleSave} style={{
            background: 'var(--bg-surface0)',
            border: '1px solid var(--border-color)',
            borderRadius: 10,
            padding: '1.25rem',
          }}>
            <h4 style={{ margin: '0 0 1rem 0', color: 'var(--text-main)', fontSize: '1rem', fontWeight: 600 }}>
              ⭐ Yechimni baholash
            </h4>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                  BALL (0 - 100) *
                </label>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={score}
                    onChange={(e) => setScore(e.target.value)}
                    style={{
                      width: '120px',
                      padding: '0.55rem',
                      background: 'var(--bg-primary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 8,
                      color: 'var(--text-main)',
                      fontSize: '1.1rem',
                      fontWeight: 700,
                      outline: 'none',
                    }}
                    required
                  />
                  <div style={{ display: 'flex', gap: '0.35rem' }}>
                    {[25, 50, 75, 100].map((quick) => (
                      <button
                        key={quick}
                        type="button"
                        onClick={() => setScore(quick)}
                        className="btn btn-secondary"
                        style={{ padding: '0.35rem 0.6rem', fontSize: '0.75rem' }}
                      >
                        {quick}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                  NATIJA HOLATI
                </label>
                <select
                  value={result}
                  onChange={(e) => setResult(e.target.value)}
                  className="form-input"
                  style={{
                    padding: '0.55rem',
                    background: 'var(--bg-primary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 8,
                    color: 'var(--text-main)',
                    fontSize: '0.9rem',
                  }}
                >
                  <option value="graded">Baholandi (Graded)</option>
                  <option value="pass">Muvaffaqiyatli (Pass)</option>
                  <option value="fail">Qoniqarsiz (Fail)</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: '1.25rem' }}>
              <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                ADMINNING IZOHI / MASLAHATI (IXTIYORIY)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Talaba yechimi haqida izoh yoki tahlil yozing..."
                style={{
                  width: '100%',
                  minHeight: '70px',
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 8,
                  padding: '0.75rem',
                  color: 'var(--text-main)',
                  fontSize: '0.9rem',
                  outline: 'none',
                  resize: 'vertical',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                type="button"
                onClick={onClose}
                disabled={saving}
                className="btn btn-secondary"
              >
                Bekor qilish
              </button>
              <button
                type="submit"
                disabled={saving}
                className="btn btn-primary"
                style={{ padding: '0.6rem 1.5rem', fontWeight: 600 }}
              >
                {saving ? 'Saqlanmoqda...' : '💾 Ballni Saqlash'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function SubmissionsReview() {
  const [searchParams] = useSearchParams();
  const userIdParam = searchParams.get('user_id') || '';

  const [submissions, setSubmissions] = useState([]);
  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [selectedChallenge, setSelectedChallenge] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [search, setSearch] = useState('');

  // Active grading modal
  const [activeSubmissionId, setActiveSubmissionId] = useState(null);

  useEffect(() => {
    api.getAdminChallenges()
      .then(({ data }) => setChallenges(data))
      .catch(() => {});
  }, []);

  const fetchSubmissions = () => {
    setLoading(true);
    const params = {
      challenge_id: selectedChallenge || undefined,
      user_id: userIdParam || undefined,
      status: selectedStatus || undefined,
      search: search || undefined,
    };
    api.getSubmissions(params)
      .then(({ data }) => setSubmissions(data))
      .catch(() => toast.error('Yechimlar yuklanmadi'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSubmissions();
  }, [selectedChallenge, selectedStatus, userIdParam]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchSubmissions();
  };

  const handleGraded = (id, newScore, newResult) => {
    setSubmissions((prev) =>
      prev.map((sub) => (sub.id === id ? { ...sub, score: newScore, result: newResult } : sub))
    );
  };

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem' }}>
          <AdminNav />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '0.25rem' }}>
                📝 Yechimlar va Baholash
              </h1>
              <p style={{ color: 'var(--text-muted)' }}>
                Ishtirokchilar tomonidan topshirilgan amaliy va nazariy yechimlarni ko'rish va ball qo'yish
              </p>
            </div>
          </div>

          {/* Filters Bar */}
          <div className="card" style={{ padding: '1rem 1.25rem', marginBottom: '1.5rem', background: 'var(--bg-mantle)' }}>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <div style={{ minWidth: '200px' }}>
                <select
                  value={selectedChallenge}
                  onChange={(e) => setSelectedChallenge(e.target.value)}
                  className="form-input"
                  style={{ padding: '0.5rem', fontSize: '0.85rem' }}
                >
                  <option value="">Barcha Challengelar</option>
                  {challenges.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>

              <div style={{ minWidth: '180px' }}>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="form-input"
                  style={{ padding: '0.5rem', fontSize: '0.85rem' }}
                >
                  <option value="">Barcha Holatlar</option>
                  <option value="ungraded">⚠️ Baholanmagan (0 ball)</option>
                  <option value="graded">⭐ Baholangan (&gt;0 ball)</option>
                  <option value="disqualified">🚫 Diskvalifikatsiya</option>
                  <option value="submitted">✅ Topshirilgan</option>
                  <option value="auto_submitted">⏰ Avto-topshirilgan</option>
                </select>
              </div>

              <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '0.5rem', flex: 1, minWidth: '240px' }}>
                <input
                  type="text"
                  placeholder="Ism, email yoki savol bo'yicha..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{
                    flex: 1,
                    padding: '0.5rem 0.9rem',
                    background: 'var(--bg-surface0)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 8,
                    color: 'var(--text-main)',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
                <button type="submit" className="btn btn-secondary" style={{ padding: '0.5rem 0.9rem', fontSize: '0.85rem' }}>
                  Filtrlash
                </button>
              </form>
            </div>
          </div>

          {/* Submissions Table */}
          {loading ? (
            <div className="loading-page" style={{ minHeight: '200px' }}>
              <div className="spinner" />
              <span>Yechimlar yuklanmoqda...</span>
            </div>
          ) : submissions.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '3.5rem', color: 'var(--text-muted)' }}>
              Hech qanday yechim topilmadi
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: 'hidden', border: '1px solid var(--border-color)' }}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-surface0)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      <th style={{ padding: '1rem 1.25rem' }}>ISHTIROKCHI</th>
                      <th style={{ padding: '1rem' }}>KUN & SAVOL</th>
                      <th style={{ padding: '1rem', textAlign: 'center' }}>TURI</th>
                      <th style={{ padding: '1rem', textAlign: 'center' }}>SARFLANGAN VAQT</th>
                      <th style={{ padding: '1rem', textAlign: 'center' }}>OGOHLANTIRISH</th>
                      <th style={{ padding: '1rem', textAlign: 'center' }}>HOLAT</th>
                      <th style={{ padding: '1rem', textAlign: 'center' }}>BALL</th>
                      <th style={{ padding: '1rem 1.25rem', textAlign: 'right' }}>BAHOLASH</th>
                    </tr>
                  </thead>
                  <tbody>
                    {submissions.map((sub, idx) => {
                      const isDq = sub.session_status === 'disqualified';
                      const isPractical = sub.question?.question_type === 'practical';

                      return (
                        <tr
                          key={sub.id}
                          style={{
                            borderBottom: idx === submissions.length - 1 ? 'none' : '1px solid var(--bg-surface0)',
                            transition: 'background 0.15s',
                          }}
                        >
                          <td style={{ padding: '1rem 1.25rem' }}>
                            <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.9rem' }}>
                              {sub.user?.username}
                            </div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                              {sub.user?.email}
                            </div>
                          </td>
                          <td style={{ padding: '1rem' }}>
                            <div style={{ fontSize: '0.85rem', color: 'var(--accent)', fontWeight: 600 }}>
                              {sub.day?.day_number}-kun
                            </div>
                            <div style={{ fontSize: '0.9rem', color: 'var(--text-main)', maxWidth: '280px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {sub.question?.title}
                            </div>
                          </td>
                          <td style={{ padding: '1rem', textAlign: 'center' }}>
                            <span className={`badge ${isPractical ? 'badge-blue' : 'badge-purple'}`} style={{ fontSize: '0.8rem' }}>
                              {isPractical ? 'Amaliy' : 'Nazariy'}
                            </span>
                          </td>
                          <td style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                            {formatDuration(sub.time_spent_secs)}
                          </td>
                          <td style={{ padding: '1rem', textAlign: 'center' }}>
                            {sub.violations_count > 0 ? (
                              <span className="badge badge-danger" style={{ fontSize: '0.8rem' }}>
                                ⚠️ {sub.violations_count} ta
                              </span>
                            ) : (
                              <span style={{ color: 'var(--success)', fontSize: '0.85rem' }}>0 ta</span>
                            )}
                          </td>
                          <td style={{ padding: '1rem', textAlign: 'center' }}>
                            {isDq ? (
                              <span className="badge badge-danger">Diskvalifikatsiya</span>
                            ) : sub.session_status === 'auto_submitted' ? (
                              <span className="badge badge-gray">Avto-yuborilgan</span>
                            ) : (
                              <span className="badge badge-green">Topshirildi</span>
                            )}
                          </td>
                          <td style={{ padding: '1rem', textAlign: 'center' }}>
                            {sub.score > 0 ? (
                              <span className="badge badge-green" style={{ fontSize: '0.9rem', fontWeight: 700 }}>
                                {sub.score} ball
                              </span>
                            ) : (
                              <span className="badge badge-gray" style={{ fontSize: '0.8rem' }}>
                                0 ball
                              </span>
                            )}
                          </td>
                          <td style={{ padding: '1rem 1.25rem', textAlign: 'right' }}>
                            <button
                              onClick={() => setActiveSubmissionId(sub.id)}
                              className="btn btn-primary"
                              style={{ padding: '0.45rem 0.9rem', fontSize: '0.85rem', fontWeight: 600 }}
                            >
                              👁️ Ko'rish &amp; Baholash
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {activeSubmissionId && (
        <GradeModal
          submissionId={activeSubmissionId}
          onClose={() => setActiveSubmissionId(null)}
          onGraded={handleGraded}
        />
      )}
    </>
  );
}

