import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { api } from '../../api/client';
import Navbar from '../../components/Navbar';

const EMPTY_QUESTION = {
  challenge_day_id: '',
  title: '',
  body_svg: '',
  difficulty: 'medium',
  starter_code: 'def solution():\n    pass\n',
  test_cases: [{ input: '', expected: '' }],
};

export default function QuestionForm() {
  const { id: challengeId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [days, setDays] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [form, setForm] = useState({ ...EMPTY_QUESTION, challenge_day_id: searchParams.get('dayId') || '' });
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  const loadData = async () => {
    setFetching(true);
    try {
      const [daysRes, qRes] = await Promise.all([
        api.getDays(challengeId),
        api.getChallengeQuestions(challengeId).catch(() => ({ data: [] })),
      ]);

      const sortedDays = daysRes.data.sort((a, b) => a.day_number - b.day_number);
      setDays(sortedDays);
      setQuestions(qRes.data || []);

      const currentDayId = searchParams.get('dayId');
      if (currentDayId && sortedDays.some((d) => d.id === currentDayId)) {
        setForm((prev) => ({ ...prev, challenge_day_id: currentDayId }));
      } else if (sortedDays.length > 0 && !form.challenge_day_id) {
        setForm((prev) => ({ ...prev, challenge_day_id: sortedDays[0].id }));
      }
    } catch {
      toast.error('Ma\'lumotlarni yuklab bo\'lmadi');
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [challengeId]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const addTestCase = () => {
    setForm((prev) => ({
      ...prev,
      test_cases: [...prev.test_cases, { input: '', expected: '' }],
    }));
  };

  const removeTestCase = (i) => {
    setForm((prev) => ({
      ...prev,
      test_cases: prev.test_cases.filter((_, idx) => idx !== i),
    }));
  };

  const updateTestCase = (i, field, value) => {
    setForm((prev) => ({
      ...prev,
      test_cases: prev.test_cases.map((tc, idx) =>
        idx === i ? { ...tc, [field]: value } : tc
      ),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.challenge_day_id) {
      toast.error('Iltimos, kunni tanlang');
      return;
    }
    if (!form.title || !form.body_svg) {
      toast.error('Nom va savol matnini kiriting');
      return;
    }
    if (form.test_cases.some((tc) => !tc.input.trim() || !tc.expected.trim())) {
      toast.error('Barcha test keyslarni (input va expected) to\'ldiring');
      return;
    }

    setLoading(true);
    try {
      await api.addQuestion(form);
      toast.success('Savol muvaffaqiyatli qo\'shildi!');
      setForm({ ...EMPTY_QUESTION, challenge_day_id: form.challenge_day_id });
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Xato yuz berdi');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteQuestion = async (qId, title) => {
    if (!confirm(`"${title}" savolini o'chirishni tasdiqlaysizmi?`)) return;
    try {
      await api.deleteQuestion(qId);
      toast.success('Savol o\'chirildi');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'O\'chirishda xatolik');
    }
  };

  const DIFFICULTY_BADGE = {
    easy: <span className="badge badge-green">Oson</span>,
    medium: <span className="badge badge-blue">O'rta</span>,
    hard: <span className="badge badge-red">Qiyin</span>,
  };

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem', maxWidth: '850px' }}>
          <div className="fade-in">
            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem' }}>
              <button
                onClick={() => navigate('/admin')}
                className="btn btn-ghost"
                style={{ padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}
              >
                ⬅ Admin panelga qaytish
              </button>
              <button
                onClick={() => navigate(`/admin/challenge/${challengeId}/days`)}
                className="btn btn-ghost"
                style={{ padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}
              >
                📅 Kunlarni boshqarish
              </button>
            </div>

            <div style={{ marginBottom: '2rem' }}>
              <h1 style={{ fontSize: '1.6rem', marginBottom: '0.25rem' }}>❓ Savollarni boshqarish</h1>
              <p style={{ color: 'var(--text-muted)' }}>
                Challenge ID: <code style={{ color: 'var(--accent)' }}>{challengeId}</code>
              </p>
            </div>

            {fetching ? (
              <div className="loading-page" style={{ minHeight: '120px' }}>
                <div className="spinner" />
              </div>
            ) : days.length === 0 ? (
              <div className="card empty-state" style={{ marginBottom: '2rem' }}>
                <div className="icon">⚠️</div>
                <h3>Kunlar mavjud emas</h3>
                <p style={{ marginBottom: '1rem' }}>
                  Savol qo'shishdan oldin kamida bitta kun yaratishingiz kerak.
                </p>
                <Link to={`/admin/challenge/${challengeId}/days`} className="btn btn-primary">
                  📅 Kun qo'shish bo'limiga o'tish
                </Link>
              </div>
            ) : (
              <div className="card" style={{ marginBottom: '2rem' }}>
                <h3 style={{ marginBottom: '1.25rem', fontSize: '1.1rem' }}>➕ Yangi savol qo'shish</h3>
                <form onSubmit={handleSubmit}>
                  {/* Kun tanlash dropdown */}
                  <div className="form-group">
                    <label className="form-label" htmlFor="q-day-id">Qaysi kun uchun? *</label>
                    <select
                      id="q-day-id"
                      name="challenge_day_id"
                      className="form-input"
                      value={form.challenge_day_id}
                      onChange={handleChange}
                      required
                    >
                      <option value="">-- Kunni tanlang --</option>
                      {days.map((d) => (
                        <option key={d.id} value={d.id}>
                          #{d.day_number}-kun {d.title ? `— ${d.title}` : ''}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid-2">
                    <div className="form-group">
                      <label className="form-label" htmlFor="q-title">Savol nomi *</label>
                      <input
                        id="q-title"
                        type="text"
                        name="title"
                        className="form-input"
                        placeholder="Masalan: Ikki sonning yig'indisi"
                        value={form.title}
                        onChange={handleChange}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label" htmlFor="q-difficulty">Qiyinlik darajasi *</label>
                      <select
                        id="q-difficulty"
                        name="difficulty"
                        className="form-input"
                        value={form.difficulty}
                        onChange={handleChange}
                      >
                        <option value="easy">Oson</option>
                        <option value="medium">O'rta</option>
                        <option value="hard">Qiyin</option>
                      </select>
                    </div>
                  </div>

                  {/* Body SVG or HTML */}
                  <div className="form-group">
                    <label className="form-label" htmlFor="q-svg">
                      Savol matni (HTML yoki SVG) *
                    </label>
                    <textarea
                      id="q-svg"
                      name="body_svg"
                      className="form-input"
                      placeholder="<p>Berilgan ikki sonni qabul qilib, ularning yig'indisini hisoblaydigan funksiya yozing.</p>"
                      value={form.body_svg}
                      onChange={handleChange}
                      rows={5}
                      required
                    />
                  </div>

                  {/* Preview */}
                  {form.body_svg && (
                    <div style={{
                      background: 'var(--bg-surface0)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '1rem',
                      marginBottom: '1.2rem',
                      fontSize: '0.9rem',
                    }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '0.5rem' }}>Ko'rinishi (Preview):</div>
                      <div dangerouslySetInnerHTML={{ __html: form.body_svg }} />
                    </div>
                  )}

                  {/* Starter code */}
                  <div className="form-group">
                    <label className="form-label" htmlFor="q-starter">Boshlang'ich kod (Starter code)</label>
                    <textarea
                      id="q-starter"
                      name="starter_code"
                      className="form-input mono"
                      value={form.starter_code}
                      onChange={handleChange}
                      rows={4}
                      style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.85rem' }}
                    />
                  </div>

                  {/* Test cases */}
                  <div style={{ marginBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                      <label className="form-label" style={{ margin: 0 }}>
                        Test keyslar (Input → Kutilgan natija) *
                      </label>
                      <button type="button" onClick={addTestCase} className="btn btn-ghost" style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem' }}>
                        + Test keys qo'shish
                      </button>
                    </div>

                    {form.test_cases.map((tc, i) => (
                      <div key={i} style={{
                        display: 'grid', gridTemplateColumns: '1fr 1fr auto',
                        gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'start',
                      }}>
                        <div>
                          <input
                            id={`tc-input-${i}`}
                            className="form-input mono"
                            placeholder="Input: masalan, 2\n3"
                            value={tc.input}
                            onChange={(e) => updateTestCase(i, 'input', e.target.value)}
                            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.82rem' }}
                          />
                        </div>
                        <div>
                          <input
                            id={`tc-expected-${i}`}
                            className="form-input mono"
                            placeholder="Expected: masalan, 5"
                            value={tc.expected}
                            onChange={(e) => updateTestCase(i, 'expected', e.target.value)}
                            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.82rem' }}
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => removeTestCase(i)}
                          className="btn btn-danger"
                          style={{ padding: '0.4rem 0.6rem', fontSize: '0.8rem' }}
                          disabled={form.test_cases.length === 1}
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>

                  <button id="question-submit" type="submit" className="btn btn-primary" disabled={loading}>
                    {loading ? <span className="spinner" /> : null}
                    {loading ? 'Qo\'shilmoqda...' : '➕ Savolni saqlash'}
                  </button>
                </form>
              </div>
            )}

            {/* Questions list */}
            {questions.length > 0 && (
              <div className="card">
                <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>
                  Mavjud savollar ({questions.length} ta)
                </h3>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Kun</th>
                        <th>Savol nomi</th>
                        <th>Qiyinlik</th>
                        <th>Testlar</th>
                        <th style={{ textAlign: 'right' }}>Amallar</th>
                      </tr>
                    </thead>
                    <tbody>
                      {questions.map((q) => (
                        <tr key={q.id}>
                          <td>
                            <strong style={{ color: 'var(--accent)' }}>
                              #{q.day_number}-kun
                            </strong>
                            {q.day_title && (
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginLeft: '0.3rem' }}>
                                ({q.day_title})
                              </span>
                            )}
                          </td>
                          <td><strong>{q.title}</strong></td>
                          <td>{DIFFICULTY_BADGE[q.difficulty] || q.difficulty}</td>
                          <td>
                            <span className="badge badge-gray">
                              {Array.isArray(q.test_cases) ? q.test_cases.length : 0} ta
                            </span>
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <button
                              onClick={() => handleDeleteQuestion(q.id, q.title)}
                              className="btn btn-danger"
                              style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem' }}
                            >
                              🗑 O'chirish
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
