import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { toast } from 'react-hot-toast';
import { api } from '../api/client';
import { useAntiCheat } from '../hooks/useAntiCheat';
import { useTimer } from '../hooks/useTimer';
import { useAutosave } from '../hooks/useAutosave';

// ─── Violation Modal ────────────────────────────────────────────
function ViolationModal({ count, max, isDisqualified, onClose }) {
  return (
    <div className="modal-overlay">
      <div className="modal fade-in" style={{
        borderColor: isDisqualified ? 'var(--danger)' : 'var(--warning)',
        boxShadow: isDisqualified ? 'var(--glow-danger)' : 'none',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>
            {isDisqualified ? '🚫' : '⚠️'}
          </div>
          <h3 style={{
            color: isDisqualified ? 'var(--danger)' : 'var(--warning)',
            marginBottom: '0.75rem',
          }}>
            {isDisqualified ? 'Diskvalifikatsiya!' : 'Ogohlantirish!'}
          </h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
            {isDisqualified
              ? 'Siz diskvalifikatsiya qilindingiz. Bu kun uchun 0 ball olasiz.'
              : `Qoida buzilishi qayd etildi. ${count}/${max} ta ogohlantirish.`}
          </p>
          {!isDisqualified && (
            <button id="violation-close" onClick={onClose} className="btn btn-secondary">
              Tushundim, davom etaman
            </button>
          )}
          {isDisqualified && (
            <button
              id="dq-exit"
              onClick={() => window.history.back()}
              className="btn btn-danger"
            >
              Chiqish
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Submit Result Modal ────────────────────────────────────────
function ResultModal({ result, onClose }) {
  const score = result?.score ?? 0;
  const isGood = score >= 7;
  return (
    <div className="modal-overlay">
      <div className="modal fade-in">
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>
            {isGood ? '🎉' : score > 0 ? '📊' : '❌'}
          </div>
          <h3 style={{
            color: isGood ? 'var(--success)' : score > 0 ? 'var(--warning)' : 'var(--danger)',
            marginBottom: '0.5rem',
          }}>
            {result?.message || `Natija: ${score}/10`}
          </h3>

          {result?.output && (
            <pre style={{
              background: 'var(--bg-surface0)',
              borderRadius: 'var(--radius-sm)',
              padding: '0.75rem',
              textAlign: 'left',
              fontSize: '0.78rem',
              color: 'var(--text-muted)',
              maxHeight: '200px',
              overflowY: 'auto',
              marginBottom: '1rem',
              fontFamily: 'JetBrains Mono, monospace',
            }}>
              {result.output}
            </pre>
          )}

          {result?.execution_ms && (
            <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginBottom: '1rem' }}>
              Ijro vaqti: {result.execution_ms}ms
            </p>
          )}

          <button id="result-close" onClick={onClose} className="btn btn-primary">
            Yopish
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Arena ─────────────────────────────────────────────────
export default function Arena() {
  const { dayId } = useParams();
  const navigate = useNavigate();

  const [sessionData, setSessionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState('');
  const codeRef = useRef('');

  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  const [violationData, setViolationData] = useState(null);
  const [showViolation, setShowViolation] = useState(false);

  // Session yuklash
  useEffect(() => {
    api.enterDay(dayId)
      .then(({ data }) => {
        setSessionData(data);
        const initial = data.previous_code || data.starter_code || '';
        setCode(initial);
        codeRef.current = initial;
      })
      .catch((err) => {
        toast.error(err.response?.data?.detail || 'Sessiyaga kira olmadingiz');
        navigate('/');
      })
      .finally(() => setLoading(false));
  }, [dayId, navigate]);

  // Vaqt tugaganida
  const handleExpire = useCallback(async () => {
    if (!sessionData?.session_id) return;
    toast('⏰ Vaqt tugadi! Avtomatik yuborilmoqda...', { icon: '⏰' });
    try {
      const { data } = await api.submitCode(sessionData.session_id, codeRef.current || '');
      setSubmitResult(data);
    } catch (e) {
      console.error('Avto-submit xato:', e);
    }
  }, [sessionData]);

  // Timer
  const { formatted, status: timerStatus, isExpired } = useTimer({
    expiresAt: sessionData?.expires_at,
    onExpire: handleExpire,
  });

  // Anti-cheat
  const handleViolation = useCallback((data) => {
    setViolationData(data);
    setShowViolation(true);
  }, []);

  useAntiCheat({
    sessionId: sessionData?.session_id,
    onViolation: handleViolation,
    enabled: !sessionData?.is_readonly,
  });

  // Autosave
  useAutosave({
    sessionId: sessionData?.session_id,
    codeRef,
    enabled: !sessionData?.is_readonly && !isExpired,
  });

  // Typing start
  const typingStarted = useRef(false);
  const handleEditorChange = (value) => {
    setCode(value || '');
    codeRef.current = value || '';

    if (!typingStarted.current && sessionData?.session_id) {
      typingStarted.current = true;
      api.typingStart(sessionData.session_id, new Date().toISOString()).catch(() => {});
    }
  };

  // Submit
  const handleSubmit = async () => {
    if (!sessionData?.session_id || submitting) return;
    setSubmitting(true);
    try {
      const { data } = await api.submitCode(sessionData.session_id, code);
      setSubmitResult(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Yuborishda xato');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
        <span>Sessiya yuklanmoqda...</span>
      </div>
    );
  }

  const isReadonly = sessionData?.is_readonly || isExpired;
  const timerClass = `timer-display ${timerStatus === 'danger' ? 'danger' : timerStatus === 'warning' ? 'warning' : ''}`;

  return (
    <div style={{
      height: '100vh', display: 'flex', flexDirection: 'column',
      background: 'var(--bg-crust)', overflow: 'hidden',
    }}>
      {/* Top bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 1.5rem', height: '56px',
        background: 'var(--bg-mantle)',
        borderBottom: '1px solid var(--bg-surface0)',
        flexShrink: 0,
      }}>
        {/* Question title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.1rem' }}>🧠</span>
          <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.95rem' }}>
            {sessionData?.question_title || 'Savol'}
          </span>
          {isReadonly && <span className="badge badge-gray">Faqat ko'rish</span>}
          {sessionData?.previous_score != null && (
            <span className="badge badge-green">{sessionData.previous_score}/10 ball</span>
          )}
        </div>

        {/* Timer + Submit */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {!isReadonly && (
            <div className={timerClass}>{formatted}</div>
          )}

          {!isReadonly && !isExpired && (
            <button
              id="arena-submit"
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={submitting}
              style={{ padding: '0.5rem 1.2rem' }}
            >
              {submitting ? <span className="spinner" style={{ width: '14px', height: '14px' }} /> : null}
              {submitting ? 'Yuborilmoqda...' : '✅ Yuborish'}
            </button>
          )}

          <button
            id="arena-exit"
            className="btn btn-ghost"
            onClick={() => navigate(-1)}
            style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}
          >
            Chiqish
          </button>
        </div>
      </div>

      {/* Main content: SVG + Editor */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left: Question SVG */}
        <div style={{
          width: '40%', minWidth: '320px', maxWidth: '560px',
          borderRight: '1px solid var(--bg-surface0)',
          overflow: 'auto',
          padding: '1.5rem',
          background: 'var(--bg-mantle)',
        }}>
          <div style={{ marginBottom: '0.75rem' }}>
            <span className="badge badge-purple" style={{ marginBottom: '0.75rem', display: 'inline-block' }}>
              Savol
            </span>
          </div>
          {sessionData?.question_svg ? (
            <div
              dangerouslySetInnerHTML={{ __html: sessionData.question_svg }}
              style={{ maxWidth: '100%' }}
            />
          ) : (
            <p style={{ color: 'var(--text-dim)' }}>Savol matni yuklanmadi</p>
          )}
        </div>

        {/* Right: Monaco Editor */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{
            padding: '0.5rem 1rem',
            background: 'var(--bg-surface0)',
            borderBottom: '1px solid var(--bg-surface0)',
            fontSize: '0.78rem', color: 'var(--text-dim)',
            display: 'flex', alignItems: 'center', gap: '0.5rem',
          }}>
            <span>🐍 Python 3</span>
            {!isReadonly && (
              <span style={{ marginLeft: 'auto' }}>Avto-saqlash: 30s da bir</span>
            )}
          </div>
          <div style={{ flex: 1 }}>
            <Editor
              height="100%"
              language="python"
              theme="vs-dark"
              value={code}
              onChange={handleEditorChange}
              options={{
                readOnly: isReadonly,
                fontSize: 14,
                fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                tabSize: 4,
                wordWrap: 'on',
                formatOnPaste: false,
                contextmenu: false,
              }}
            />
          </div>
        </div>
      </div>

      {/* Violation Modal */}
      {showViolation && violationData && (
        <ViolationModal
          count={violationData.violations_count}
          max={violationData.max_allowed}
          isDisqualified={violationData.is_disqualified}
          onClose={() => setShowViolation(false)}
        />
      )}

      {/* Result Modal */}
      {submitResult && (
        <ResultModal
          result={submitResult}
          onClose={() => { setSubmitResult(null); navigate(-1); }}
        />
      )}
    </div>
  );
}
