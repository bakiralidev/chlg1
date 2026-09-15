import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { toast } from "react-hot-toast";
import { api } from "../api/client";
import { useAntiCheat } from "../hooks/useAntiCheat";
import { useTimer } from "../hooks/useTimer";
import { useAutosave } from "../hooks/useAutosave";

function ViolationModal({ count, max, isDisqualified, onClose }) {
  return (
    <div className="modal-overlay">
      <div className="modal fade-in" style={{
        borderColor: isDisqualified ? "var(--danger)" : "var(--warning)",
        boxShadow: isDisqualified ? "var(--glow-danger)" : "none",
      }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>
            {isDisqualified ? "🚫" : "⚠️"}
          </div>
          <h3 style={{ color: isDisqualified ? "var(--danger)" : "var(--warning)", marginBottom: "0.75rem" }}>
            {isDisqualified ? "Diskvalifikatsiya!" : "Ogohlantirish!"}
          </h3>
          <p style={{ color: "var(--text-muted)", marginBottom: "1.25rem" }}>
            {isDisqualified
              ? "Siz diskvalifikatsiya qilindingiz. Bu kun uchun 0 ball olasiz."
              : `Qoida buzilishi qayd etildi. ${count}/${max} ta ogohlantirish.`}
          </p>
          {!isDisqualified && (
            <button id="violation-close" onClick={onClose} className="btn btn-secondary">
              Tushundim, davom etaman
            </button>
          )}
          {isDisqualified && (
            <button id="dq-exit" onClick={() => window.history.back()} className="btn btn-danger">
              Chiqish
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ResultModal({ result, onClose }) {
  return (
    <div className="modal-overlay">
      <div className="modal fade-in">
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>✅</div>
          <h3 style={{ color: "var(--success)", marginBottom: "0.5rem" }}>
            Yechim qabul qilindi!
          </h3>
          <p style={{ color: "var(--text-muted)", marginBottom: "1.25rem" }}>
            {result?.message || "Yechimingiz muvaffaqiyatli saqlandi. Natija AI baholashidan keyin e'lon qilinadi."}
          </p>
          <button id="result-close" onClick={onClose} className="btn btn-primary">
            Yopish
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Arena() {
  const { dayId } = useParams();
  const navigate = useNavigate();
  const [sessionData, setSessionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState("");
  const codeRef = useRef("");
  const [note, setNote] = useState("");
  const noteRef = useRef("");
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [violationData, setViolationData] = useState(null);
  const [showViolation, setShowViolation] = useState(false);
  const typingStarted = useRef(false);

  useEffect(() => {
    api.enterDay(dayId)
      .then(({ data }) => {
        setSessionData(data);
        if (data.question_type === "practical") {
          const initial = data.previous_code || data.starter_code || "";
          setCode(initial);
          codeRef.current = initial;
        } else {
          const initial = data.previous_note || "";
          setNote(initial);
          noteRef.current = initial;
        }
      })
      .catch((err) => {
        toast.error(err.response?.data?.detail || "Sessiyaga kira olmadingiz");
        navigate("/");
      })
      .finally(() => setLoading(false));
  }, [dayId, navigate]);

  const handleExpire = useCallback(async () => {
    if (!sessionData?.session_id) return;
    toast("Vaqt tugadi! Avtomatik yuborilmoqda...", { icon: "⏰" });
    try {
      const payload = sessionData.question_type === "practical"
        ? { code: codeRef.current || "" }
        : { note_content: noteRef.current || "" };
      const { data } = await api.submitCode(sessionData.session_id, payload);
      setSubmitResult(data);
    } catch (e) {
      console.error("Avto-submit xato:", e);
    }
  }, [sessionData]);

  const { formatted, status: timerStatus, isExpired } = useTimer({
    expiresAt: sessionData?.expires_at,
    onExpire: handleExpire,
  });

  const handleViolation = useCallback((data) => {
    setViolationData(data);
    setShowViolation(true);
  }, []);

  useAntiCheat({
    sessionId: sessionData?.session_id,
    onViolation: handleViolation,
    enabled: !sessionData?.is_readonly,
  });

  useAutosave({
    sessionId: sessionData?.session_id,
    codeRef,
    noteRef,
    enabled: !sessionData?.is_readonly && !isExpired,
  });

  const handleFirstInput = () => {
    if (!typingStarted.current && sessionData?.session_id) {
      typingStarted.current = true;
      api.typingStart(sessionData.session_id, new Date().toISOString()).catch(() => {});
    }
  };

  const handleEditorChange = (value) => {
    setCode(value || "");
    codeRef.current = value || "";
    handleFirstInput();
  };

  const handleNoteChange = (e) => {
    setNote(e.target.value);
    noteRef.current = e.target.value;
    handleFirstInput();
  };

  const handleSubmit = async () => {
    if (!sessionData?.session_id || submitting) return;
    setSubmitting(true);
    try {
      const payload = sessionData.question_type === "practical"
        ? { code }
        : { note_content: note };
      const { data } = await api.submitCode(sessionData.session_id, payload);
      setSubmitResult(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Yuborishda xato");
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
  const timerClass = `timer-display ${timerStatus === "danger" ? "danger" : timerStatus === "warning" ? "warning" : ""}`;
  const isPractical = sessionData?.question_type === "practical";

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "var(--bg-crust)", overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 1.5rem", height: "56px", background: "var(--bg-mantle)", borderBottom: "1px solid var(--bg-surface0)", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span style={{ fontSize: "1.1rem" }}>{isPractical ? "🖥️" : "📝"}</span>
          <span style={{ fontWeight: 600, color: "var(--text-main)", fontSize: "0.95rem" }}>
            {sessionData?.question_title || "Savol"}
          </span>
          <span className={`badge ${isPractical ? "badge-blue" : "badge-purple"}`}>
            {isPractical ? "Amaliy" : "Nazariy"}
          </span>
          {isReadonly && <span className="badge badge-gray">Faqat ko'rish</span>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {!isReadonly && <div className={timerClass}>{formatted}</div>}
          {!isReadonly && !isExpired && (
            <button id="arena-submit" className="btn btn-primary" onClick={handleSubmit} disabled={submitting} style={{ padding: "0.5rem 1.2rem" }}>
              {submitting ? <span className="spinner" style={{ width: "14px", height: "14px" }} /> : null}
              {submitting ? "Yuborilmoqda..." : "✅ Yuborish"}
            </button>
          )}
          <button id="arena-exit" className="btn btn-ghost" onClick={() => navigate(-1)} style={{ padding: "0.5rem 0.75rem", fontSize: "0.85rem" }}>
            Chiqish
          </button>
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <div style={{ width: isPractical ? "40%" : "50%", minWidth: "320px", borderRight: "1px solid var(--bg-surface0)", overflow: "auto", padding: "1.5rem", background: "var(--bg-mantle)" }}>
          <span className="badge badge-purple" style={{ marginBottom: "0.75rem", display: "inline-block" }}>
            {isPractical ? "📋 Savol" : "📝 Topshiriq"}
          </span>
          {sessionData?.question_body ? (
            <div dangerouslySetInnerHTML={{ __html: sessionData.question_body }} style={{ maxWidth: "100%", lineHeight: 1.7, color: "var(--text-primary)" }} />
          ) : (
            <p style={{ color: "var(--text-dim)" }}>Savol matni yuklanmadi</p>
          )}
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {isPractical ? (
            <>
              <div style={{ padding: "0.5rem 1rem", background: "var(--bg-surface0)", borderBottom: "1px solid var(--bg-surface0)", fontSize: "0.78rem", color: "var(--text-dim)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span>🐍 Python 3 — Kod yozing</span>
                {!isReadonly && <span style={{ marginLeft: "auto" }}>Avto-saqlash: 30s da bir</span>}
              </div>
              <div style={{ flex: 1 }}>
                <Editor
                  height="100%"
                  language="python"
                  theme="vs-dark"
                  value={code}
                  onChange={handleEditorChange}
                  options={{ readOnly: isReadonly, fontSize: 14, fontFamily: '"JetBrains Mono", monospace', minimap: { enabled: false }, scrollBeyondLastLine: false, tabSize: 4, wordWrap: "on", formatOnPaste: false, contextmenu: false }}
                />
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "1.5rem" }}>
              <div style={{ marginBottom: "1rem", fontSize: "0.85rem", color: "var(--text-dim)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span>📝 Javob maydoningiz</span>
                {!isReadonly && <span style={{ marginLeft: "auto" }}>Avto-saqlash: 30s da bir</span>}
              </div>
              <textarea
                value={note}
                onChange={handleNoteChange}
                readOnly={isReadonly}
                placeholder={isReadonly ? "Faqat ko'rish rejimi." : "Bu yerga savol bo'yicha fikr-mulohazangizni yozing..."}
                style={{ flex: 1, width: "100%", background: "var(--bg-primary)", border: "1px solid var(--border-color)", borderRadius: 12, padding: "1.25rem", color: "var(--text-primary)", fontSize: "0.95rem", lineHeight: 1.7, resize: "none", fontFamily: "inherit", outline: "none", boxSizing: "border-box" }}
              />
              <div style={{ marginTop: "0.75rem", fontSize: "0.8rem", color: "var(--text-muted)", textAlign: "right" }}>
                {note.length} belgi
              </div>
            </div>
          )}
        </div>
      </div>

      {showViolation && violationData && (
        <ViolationModal count={violationData.violations_count} max={violationData.max_allowed} isDisqualified={violationData.is_disqualified} onClose={() => setShowViolation(false)} />
      )}
      {submitResult && (
        <ResultModal result={submitResult} onClose={() => { setSubmitResult(null); navigate(-1); }} />
      )}
    </div>
  );
}