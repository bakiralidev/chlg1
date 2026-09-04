import { useState } from 'react';
import { useParams } from 'react-router-dom';
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
  const [form, setForm] = useState({ ...EMPTY_QUESTION, challenge_day_id: '' });
  const [loading, setLoading] = useState(false);
  const [added, setAdded] = useState([]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  // Test cases boshqaruvi
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
      toast.error('Kun ID ni kiriting');
      return;
    }
    if (!form.title || !form.body_svg) {
      toast.error('Nom va savol matnini kiriting');
      return;
    }
    if (form.test_cases.some((tc) => !tc.input || !tc.expected)) {
      toast.error('Barcha test keyslarni to\'ldiring');
      return;
    }

    setLoading(true);
    try {
      await api.addQuestion(form);
      toast.success('Savol qo\'shildi!');
      setAdded((prev) => [...prev, form.title]);
      setForm({ ...EMPTY_QUESTION, challenge_day_id: form.challenge_day_id });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Xato');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem', maxWidth: '800px' }}>
          <div className="fade-in">
            <h1 style={{ fontSize: '1.6rem', marginBottom: '0.5rem' }}>❓ Savol qo'shish</h1>
            <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
              Challenge ID: <code style={{ color: 'var(--accent)' }}>{challengeId}</code>
            </p>

            {added.length > 0 && (
              <div className="card" style={{ marginBottom: '1.5rem', borderColor: 'var(--success)' }}>
                <p style={{ color: 'var(--success)', fontWeight: 600, marginBottom: '0.5rem' }}>
                  ✅ Qo'shilgan savollar:
                </p>
                {added.map((title, i) => (
                  <div key={i} style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>• {title}</div>
                ))}
              </div>
            )}

            <div className="card">
              <form onSubmit={handleSubmit}>
                {/* Kun ID */}
                <div className="form-group">
                  <label className="form-label" htmlFor="q-day-id">Kun ID (challenge_day_id) *</label>
                  <input
                    id="q-day-id"
                    type="text"
                    name="challenge_day_id"
                    className="form-input"
                    placeholder="UUID"
                    value={form.challenge_day_id}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label" htmlFor="q-title">Savol nomi *</label>
                    <input
                      id="q-title"
                      type="text"
                      name="title"
                      className="form-input"
                      placeholder="Ikki sonni qo'shish"
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

                {/* SVG body */}
                <div className="form-group">
                  <label className="form-label" htmlFor="q-svg">Savol matni (SVG/HTML) *</label>
                  <textarea
                    id="q-svg"
                    name="body_svg"
                    className="form-input"
                    placeholder="<p>Ikki sonni qabul qilib, ularning yig'indisini qaytaring.</p>"
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
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '0.5rem' }}>Preview:</div>
                    <div dangerouslySetInnerHTML={{ __html: form.body_svg }} />
                  </div>
                )}

                {/* Starter code */}
                <div className="form-group">
                  <label className="form-label" htmlFor="q-starter">Starter kod</label>
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
                <div style={{ marginBottom: '1.2rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <label className="form-label" style={{ margin: 0 }}>
                      Test keyslar *
                    </label>
                    <button type="button" onClick={addTestCase} className="btn btn-ghost" style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem' }}>
                      + Qo'shish
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
                          placeholder="Input: 2 3"
                          value={tc.input}
                          onChange={(e) => updateTestCase(i, 'input', e.target.value)}
                          style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.82rem' }}
                        />
                      </div>
                      <div>
                        <input
                          id={`tc-expected-${i}`}
                          className="form-input mono"
                          placeholder="Expected: 5"
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
                  {loading ? 'Qo\'shilmoqda...' : '➕ Savol qo\'shish'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
