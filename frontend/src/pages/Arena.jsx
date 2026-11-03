import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { toast } from "react-hot-toast";
import { api } from "../api/client";
import { useAntiCheat } from "../hooks/useAntiCheat";
import { useTimer } from "../hooks/useTimer";
import { useAutosave } from "../hooks/useAutosave";

function ViolationModal({ count, max, isDisqualified, onClose, onExit }) {
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
            <button id="dq-exit" onClick={onExit} className="btn btn-danger">
              Chiqish
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ExitConfirmModal({ count, max, onConfirm, onCancel, loading }) {
  const willBeDisqualified = count + 1 >= max;

  return (
    <div className="modal-overlay">
      <div className="modal fade-in" style={{
        maxWidth: 440,
        textAlign: "center",
        borderColor: willBeDisqualified ? "var(--danger)" : "var(--warning)",
      }}>
        <div style={{ fontSize: "2.8rem", marginBottom: "0.75rem" }}>
          {willBeDisqualified ? "🚫" : "⚠️"}
        </div>
        <h3 style={{
          marginBottom: "0.75rem",
          color: willBeDisqualified ? "var(--danger)" : "var(--warning)"
        }}>
          Haqiqatan ham chiqmoqchimisiz?
        </h3>
        <p style={{ color: "var(--text-muted)", marginBottom: "1rem", lineHeight: 1.6, fontSize: "0.95rem" }}>
          Diqqat! Imtihon davom etayotganda oynadan chiqish <strong>qoidabuzarlik</strong> hisoblanadi va ogohlantirish qayd etiladi.
        </p>

        <div style={{
          background: willBeDisqualified ? "rgba(243, 139, 168, 0.2)" : "rgba(250, 179, 135, 0.15)",
          border: `1px solid ${willBeDisqualified ? "var(--danger)" : "var(--warning)"}`,
          borderRadius: 8,
          padding: "0.75rem 1rem",
          marginBottom: "1.25rem",
          color: willBeDisqualified ? "var(--danger)" : "var(--warning)",
          fontSize: "0.9rem",
          fontWeight: 600,
          textAlign: "left",
        }}>
          {willBeDisqualified ? (
            <div>🚫 <strong>Bu oxirgi ogohlantirish ({count + 1}/{max}) bo'ladi!</strong> Siz to'liq diskvalifikatsiya qilinasiz va bu kun uchun 0 ball olasiz.</div>
          ) : (
            <div>⚠️ Chiqsangiz, ogohlantirish qayd etiladi: <strong>{count + 1} / {max}</strong>.<br/><span style={{ fontSize: "0.82rem", fontWeight: 400, color: "var(--text-muted)" }}>Jami {max} ta ogohlantirish qayd etilsa, musobaqadan diskvalifikatsiya bo'lasiz.</span></div>
          )}
        </div>

        <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center" }}>
          <button
            onClick={onCancel}
            disabled={loading}
            className="btn btn-secondary"
            style={{ flex: 1, padding: "0.6rem" }}
          >
            Imtihonda qolish
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="btn btn-danger"
            style={{ flex: 1, padding: "0.6rem" }}
          >
            {loading ? "Chiqilmoqda..." : "Baribir chiqish"}
          </button>
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

function TerminalPanel({
  output,
  running,
  onRun,
  isOpen,
  onToggle,
  onClear,
  tab,
  setTab,
  stdin,
  setStdin,
  isReadonly,
}) {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      background: "#0f111a",
      borderTop: "1px solid var(--bg-surface0)",
      height: isOpen ? "220px" : "36px",
      transition: "height 0.2s ease-in-out",
      overflow: "hidden",
      flexShrink: 0,
    }}>
      {/* Terminal Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0.35rem 0.85rem",
        background: "var(--bg-crust)",
        borderBottom: isOpen ? "1px solid var(--bg-surface0)" : "none",
        fontSize: "0.78rem",
        color: "var(--text-muted)",
        userSelect: "none",
      }}>
        {/* Left: toggle & tabs */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <button
            type="button"
            onClick={onToggle}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: "2px 4px",
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
              fontWeight: 600,
            }}
          >
            <span style={{ fontSize: "0.7rem" }}>{isOpen ? "▼" : "▲"}</span>
            <span>💻 Terminal</span>
          </button>

          {isOpen && (
            <div style={{ display: "flex", gap: "0.25rem", marginLeft: "0.5rem" }}>
              <button
                type="button"
                onClick={() => setTab("output")}
                style={{
                  padding: "0.2rem 0.6rem",
                  borderRadius: "4px",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  fontWeight: tab === "output" ? 600 : 400,
                  background: tab === "output" ? "var(--bg-surface0)" : "transparent",
                  color: tab === "output" ? "var(--accent)" : "var(--text-dim)",
                }}
              >
                Chiqish (Output)
              </button>
              <button
                type="button"
                onClick={() => setTab("input")}
                style={{
                  padding: "0.2rem 0.6rem",
                  borderRadius: "4px",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  fontWeight: tab === "input" ? 600 : 400,
                  background: tab === "input" ? "var(--bg-surface0)" : "transparent",
                  color: tab === "input" ? "var(--accent-2)" : "var(--text-dim)",
                }}
              >
                Kiritish (STDIN) {stdin ? "•" : ""}
              </button>
            </div>
          )}
        </div>

        {/* Right: status & actions */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          {running && (
            <span style={{ color: "var(--warning)", display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.75rem" }}>
              <span className="spinner" style={{ width: "12px", height: "12px" }} />
              Bajarilmoqda...
            </span>
          )}

          {!running && output && (
            <span style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              color: output.exitCode === 0 ? "var(--success)" : "var(--danger)",
            }}>
              {output.exitCode === 0 ? "✅ Tayyor" : "❌ Xatolik"} ({output.executionMs}ms)
            </span>
          )}

          {isOpen && output && (
            <button
              type="button"
              onClick={onClear}
              style={{
                background: "none",
                border: "none",
                color: "var(--text-dim)",
                cursor: "pointer",
                fontSize: "0.75rem",
              }}
              title="Terminalni tozalash"
            >
              Tozalash
            </button>
          )}

          <button
            type="button"
            onClick={onRun}
            disabled={running}
            className="btn btn-primary"
            style={{
              padding: "0.25rem 0.85rem",
              fontSize: "0.76rem",
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
            }}
            title="Kodni ishga tushirish (Ctrl+Enter)"
          >
            <span>▶</span>
            <span>{running ? "Kutilmoqda..." : "Ishga tushirish"}</span>
          </button>
        </div>
      </div>

      {/* Terminal Content Body */}
      {isOpen && (
        <div style={{
          flex: 1,
          overflow: "auto",
          padding: "0.75rem 1rem",
          fontFamily: "'JetBrains Mono', 'Consolas', monospace",
          fontSize: "0.85rem",
          lineHeight: 1.5,
          color: "var(--text-main)",
        }}>
          {tab === "input" ? (
            <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginBottom: "0.3rem" }}>
                Kodingizda input() ishlatilgan bo'lsa, har bir qatorda kiritiladigan qiymatni yozing:
              </div>
              <textarea
                value={stdin}
                onChange={(e) => setStdin(e.target.value)}
                placeholder={"Masalan:\n10\n20\nsalom"}
                style={{
                  flex: 1,
                  width: "100%",
                  background: "var(--bg-crust)",
                  border: "1px solid var(--bg-surface0)",
                  borderRadius: "4px",
                  color: "var(--text-main)",
                  fontFamily: "inherit",
                  fontSize: "0.85rem",
                  padding: "0.5rem",
                  resize: "none",
                  outline: "none",
                }}
              />
            </div>
          ) : (
            <div>
              {!output && !running && (
                <div style={{ color: "var(--text-dim)", fontStyle: "italic" }}>
                  $ Kodingizni sinash uchun yuqoridagi "▶ Ishga tushirish" tugmasini bosing yoki Ctrl+Enter bosing...
                </div>
              )}

              {running && (
                <div>
                  <div style={{ color: "var(--accent)" }}>$ python main.py</div>
                  <div style={{ color: "var(--warning)", marginTop: "0.25rem" }}>
                    ⏳ Dastur serverda bajarilmoqda...
                  </div>
                </div>
              )}

              {output && (
                <div>
                  <div style={{ color: "var(--text-dim)", marginBottom: "0.4rem" }}>
                    $ python main.py <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>({output.timestamp})</span>
                  </div>

                  {output.stdout && (
                    <div style={{ color: "#a6e3a1", whiteSpace: "pre-wrap", marginBottom: "0.4rem" }}>
                      {output.stdout}
                    </div>
                  )}

                  {output.stderr && (
                    <div style={{ color: "#f38ba8", whiteSpace: "pre-wrap", marginBottom: "0.4rem" }}>
                      {output.stderr}
                    </div>
                  )}

                  {!output.stdout && !output.stderr && (
                    <div style={{ color: "var(--text-dim)", fontStyle: "italic", marginBottom: "0.4rem" }}>
                      (Natija bo'sh: dastur ekranga hech narsa chop qilmadi. Natijani ko'rish uchun print(...) dan foydalaning)
                    </div>
                  )}

                  <div style={{
                    fontSize: "0.75rem",
                    color: "var(--text-dim)",
                    borderTop: "1px dashed var(--bg-surface1)",
                    paddingTop: "0.3rem",
                    marginTop: "0.5rem",
                  }}>
                    Jarayon yakunlandi: Exit code {output.exitCode} | Vaqt: {output.executionMs}ms
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
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
  const [showExitConfirm, setShowExitConfirm] = useState(false);
  const [exiting, setExiting] = useState(false);
  const typingStarted = useRef(false);

  // Terminal state for practical questions
  const [runningCode, setRunningCode] = useState(false);
  const [terminalOutput, setTerminalOutput] = useState(null);
  const [terminalOpen, setTerminalOpen] = useState(true);
  const [terminalTab, setTerminalTab] = useState("output"); // 'output' | 'input'
  const [stdinInput, setStdinInput] = useState("");

  // Scratchpad state for theoretical questions
  const [showScratchpad, setShowScratchpad] = useState(false);
  const [scratchCode, setScratchCode] = useState(
    "# Bu yerda Python kodini erkin sinab ko'rishingiz mumkin:\nimport math\n# print(math.sqrt(-1))\n\nimport cmath\n# print(cmath.sqrt(-1))\n"
  );
  const [scratchRunning, setScratchRunning] = useState(false);
  const [scratchOutput, setScratchOutput] = useState(null);
  const [scratchTerminalOpen, setScratchTerminalOpen] = useState(true);
  const [scratchTab, setScratchTab] = useState("output");
  const [scratchStdin, setScratchStdin] = useState("");

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
    if (data.is_disqualified) {
      setSessionData((prev) => (prev ? { ...prev, is_readonly: true } : prev));
    }
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

  // Run code in terminal
  const handleRunCode = async () => {
    if (!code || !code.trim()) {
      toast.error("Ishga tushirish uchun kod yozing!");
      return;
    }
    if (!sessionData?.session_id) return;

    setRunningCode(true);
    setTerminalOpen(true);
    setTerminalTab("output");

    try {
      const { data } = await api.runCode(sessionData.session_id, {
        code,
        input_data: stdinInput,
      });
      setTerminalOutput({
        stdout: data.stdout,
        stderr: data.stderr,
        exitCode: data.exit_code,
        executionMs: data.execution_ms,
        timestamp: new Date().toLocaleTimeString(),
      });
    } catch (err) {
      const msg = err.response?.data?.detail || "Kodni ishga tushirishda xatolik yuz berdi";
      setTerminalOutput({
        stdout: "",
        stderr: msg,
        exitCode: -1,
        executionMs: 0,
        timestamp: new Date().toLocaleTimeString(),
      });
    } finally {
      setRunningCode(false);
    }
  };

  // Run code in scratchpad (theoretical questions)
  const handleRunScratchCode = async () => {
    if (!scratchCode || !scratchCode.trim()) {
      toast.error("Sinash uchun kod yozing!");
      return;
    }
    if (!sessionData?.session_id) return;

    setScratchRunning(true);
    setScratchTerminalOpen(true);
    setScratchTab("output");

    try {
      const { data } = await api.runCode(sessionData.session_id, {
        code: scratchCode,
        input_data: scratchStdin,
      });
      setScratchOutput({
        stdout: data.stdout,
        stderr: data.stderr,
        exitCode: data.exit_code,
        executionMs: data.execution_ms,
        timestamp: new Date().toLocaleTimeString(),
      });
    } catch (err) {
      const msg = err.response?.data?.detail || "Kodni ishga tushirishda xatolik";
      setScratchOutput({
        stdout: "",
        stderr: msg,
        exitCode: -1,
        executionMs: 0,
        timestamp: new Date().toLocaleTimeString(),
      });
    } finally {
      setScratchRunning(false);
    }
  };

  // Hotkey: Ctrl+Enter or Cmd+Enter to run code
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (sessionData?.question_type === "practical") {
          handleRunCode();
        } else if (showScratchpad) {
          handleRunScratchCode();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [code, scratchCode, showScratchpad, sessionData]);

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

  const isReadonly = sessionData?.is_readonly || isExpired;
  const timerClass = `timer-display ${timerStatus === "danger" ? "danger" : timerStatus === "warning" ? "warning" : ""}`;
  const isPractical = sessionData?.question_type === "practical";

  const violationsCount = violationData?.violations_count ?? sessionData?.violations_count ?? 0;
  const maxViolations = violationData?.max_allowed ?? sessionData?.max_violations ?? 3;

  const handleExitClick = () => {
    if (isReadonly) {
      navigate("/");
      return;
    }
    setShowExitConfirm(true);
  };

  const handleConfirmExit = async () => {
    if (!sessionData?.session_id) {
      navigate("/");
      return;
    }
    setExiting(true);
    try {
      const { data } = await api.reportViolation(sessionData.session_id, "manual_exit");
      setShowExitConfirm(false);
      handleViolation(data);
      if (data.is_disqualified) {
        navigate("/");
      }
    } catch (err) {
      console.error("Chiqish xatosi:", err);
      navigate("/");
    } finally {
      setExiting(false);
    }
  };

  if (loading) {
    return (
      <div className="arena-loading">
        <div className="spinner" style={{ width: "40px", height: "40px" }} />
        <p style={{ color: "var(--text-muted)", marginTop: "1rem" }}>Arena yuklanmoqda...</p>
      </div>
    );
  }

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "var(--bg-base)" }}>
      {/* Header */}
      <div style={{
        height: "56px",
        background: "var(--bg-mantle)",
        borderBottom: "1px solid var(--bg-surface0)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 1.25rem",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span style={{ fontSize: "1.2rem" }}>🐍</span>
          <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>
            {sessionData?.question_title || "Savol"}
          </span>
          <span className="badge badge-purple" style={{ fontSize: "0.7rem" }}>
            {isPractical ? "AMALIY" : "NAZARIY"}
          </span>
          {isReadonly && (
            <span className="badge badge-blue" style={{ fontSize: "0.7rem" }}>
              FAKAT KO'RISH
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          {!isReadonly && (
            <div
              style={{
                padding: "0.35rem 0.75rem",
                borderRadius: "8px",
                fontSize: "0.85rem",
                fontWeight: 600,
                background: violationsCount > 0 ? "rgba(243, 139, 168, 0.15)" : "var(--bg-surface0)",
                color: violationsCount > 0 ? "var(--danger)" : "var(--text-muted)",
                border: `1px solid ${violationsCount > 0 ? "var(--danger)" : "var(--bg-surface1)"}`,
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
              }}
              title={`Qoidabuzarliklar: ${violationsCount} / ${maxViolations}. ${maxViolations} ta bo'lsa diskvalifikatsiya.`}
            >
              <span>⚠️</span>
              <span>{violationsCount}/{maxViolations}</span>
            </div>
          )}
          {!isReadonly && <div className={timerClass}>{formatted}</div>}
          {!isReadonly && !isExpired && (
            <button id="arena-submit" className="btn btn-primary" onClick={handleSubmit} disabled={submitting} style={{ padding: "0.5rem 1.2rem" }}>
              {submitting ? <span className="spinner" style={{ width: "14px", height: "14px" }} /> : null}
              {submitting ? "Yuborilmoqda..." : "✅ Yuborish"}
            </button>
          )}
          <button id="arena-exit" className="btn btn-ghost" onClick={handleExitClick} style={{ padding: "0.5rem 0.75rem", fontSize: "0.85rem" }}>
            Chiqish
          </button>
        </div>
      </div>

      {/* Main Workspace Area */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Left: Question description */}
        <div style={{ width: isPractical ? "40%" : "45%", minWidth: "320px", borderRight: "1px solid var(--bg-surface0)", overflow: "auto", padding: "1.5rem", background: "var(--bg-mantle)" }}>
          <span className="badge badge-purple" style={{ marginBottom: "0.75rem", display: "inline-block" }}>
            {isPractical ? "📋 Savol sharti" : "📝 Topshiriq"}
          </span>
          {sessionData?.question_body ? (
            <div dangerouslySetInnerHTML={{ __html: sessionData.question_body }} style={{ maxWidth: "100%", lineHeight: 1.7, color: "var(--text-primary)" }} />
          ) : (
            <p style={{ color: "var(--text-dim)" }}>Savol matni yuklanmadi</p>
          )}
        </div>

        {/* Right: Coding / Answer Space */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--bg-base)" }}>
          {isPractical ? (
            <>
              {/* Practical Editor Header */}
              <div style={{
                padding: "0.45rem 1rem",
                background: "var(--bg-surface0)",
                borderBottom: "1px solid var(--bg-surface0)",
                fontSize: "0.78rem",
                color: "var(--text-dim)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexShrink: 0,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span>🐍 Python 3 — main.py</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.8rem" }}>
                  {!isReadonly && <span>Avto-saqlash: 30s da bir</span>}
                  <button
                    type="button"
                    onClick={handleRunCode}
                    disabled={runningCode}
                    className="btn btn-primary"
                    style={{
                      padding: "0.25rem 0.75rem",
                      fontSize: "0.75rem",
                      borderRadius: "4px",
                    }}
                  >
                    {runningCode ? "Kutilmoqda..." : "▶ Ishga tushirish (Ctrl+Enter)"}
                  </button>
                </div>
              </div>

              {/* Monaco Editor */}
              <div style={{ flex: 1, overflow: "hidden" }}>
                <Editor
                  height="100%"
                  language="python"
                  theme="vs-dark"
                  value={code}
                  onChange={handleEditorChange}
                  options={{
                    readOnly: isReadonly,
                    fontSize: 14,
                    fontFamily: '"JetBrains Mono", monospace',
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    tabSize: 4,
                    wordWrap: "on",
                    formatOnPaste: false,
                    contextmenu: false,
                  }}
                />
              </div>

              {/* Practical Terminal */}
              <TerminalPanel
                output={terminalOutput}
                running={runningCode}
                onRun={handleRunCode}
                isOpen={terminalOpen}
                onToggle={() => setTerminalOpen(!terminalOpen)}
                onClear={() => setTerminalOutput(null)}
                tab={terminalTab}
                setTab={setTerminalTab}
                stdin={stdinInput}
                setStdin={setStdinInput}
                isReadonly={isReadonly}
              />
            </>
          ) : (
            /* Theoretical Questions View */
            <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "1.25rem", overflow: "hidden" }}>
              {/* Header with Scratchpad Button */}
              <div style={{
                marginBottom: "0.75rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexShrink: 0,
              }}>
                <div style={{ fontSize: "0.85rem", color: "var(--text-dim)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span>📝 Javob maydoningiz</span>
                  {!isReadonly && <span style={{ marginLeft: "0.5rem", color: "var(--text-dim)", fontSize: "0.75rem" }}>(Avto-saqlash: 30s)</span>}
                </div>

                {/* Scratchpad Toggle Button */}
                <button
                  type="button"
                  onClick={() => setShowScratchpad(!showScratchpad)}
                  style={{
                    padding: "0.35rem 0.85rem",
                    borderRadius: "6px",
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    background: showScratchpad ? "rgba(203, 166, 247, 0.2)" : "var(--bg-surface0)",
                    color: showScratchpad ? "var(--accent-2)" : "var(--text-sub)",
                    border: `1px solid ${showScratchpad ? "var(--accent-2)" : "var(--bg-surface1)"}`,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.4rem",
                    transition: "all 0.2s",
                  }}
                >
                  <span>💻</span>
                  <span>{showScratchpad ? "Terminalni yashirish" : "Python Sinov Terminali (Scratchpad)"}</span>
                </button>
              </div>

              {/* If scratchpad is open: split between Scratchpad editor + terminal and Answer Textarea */}
              {showScratchpad && (
                <div style={{
                  marginBottom: "1rem",
                  background: "var(--bg-crust)",
                  borderRadius: "10px",
                  border: "1px solid var(--accent-2)",
                  overflow: "hidden",
                  display: "flex",
                  flexDirection: "column",
                  height: "280px",
                  flexShrink: 0,
                  boxShadow: "0 6px 24px rgba(0,0,0,0.4)",
                }}>
                  <div style={{
                    padding: "0.4rem 0.85rem",
                    background: "rgba(203, 166, 247, 0.12)",
                    borderBottom: "1px solid var(--bg-surface0)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: "0.78rem",
                    color: "var(--accent-2)",
                  }}>
                    <span>💡 Python Sinov Muhiti — Kod yozib, natijani tekshirib ko'rishingiz mumkin</span>
                    <button
                      type="button"
                      onClick={handleRunScratchCode}
                      disabled={scratchRunning}
                      className="btn btn-primary"
                      style={{ padding: "0.2rem 0.6rem", fontSize: "0.74rem" }}
                    >
                      {scratchRunning ? "Kutilmoqda..." : "▶ Ishga tushirish (Ctrl+Enter)"}
                    </button>
                  </div>

                  <div style={{ flex: 1, minHeight: "100px" }}>
                    <Editor
                      height="100%"
                      language="python"
                      theme="vs-dark"
                      value={scratchCode}
                      onChange={(v) => setScratchCode(v || "")}
                      options={{
                        fontSize: 13,
                        fontFamily: '"JetBrains Mono", monospace',
                        minimap: { enabled: false },
                        tabSize: 4,
                        wordWrap: "on",
                      }}
                    />
                  </div>

                  <TerminalPanel
                    output={scratchOutput}
                    running={scratchRunning}
                    onRun={handleRunScratchCode}
                    isOpen={scratchTerminalOpen}
                    onToggle={() => setScratchTerminalOpen(!scratchTerminalOpen)}
                    onClear={() => setScratchOutput(null)}
                    tab={scratchTab}
                    setTab={setScratchTab}
                    stdin={scratchStdin}
                    setStdin={setScratchStdin}
                    isReadonly={false}
                  />
                </div>
              )}

              {/* Main Answer Textarea */}
              <textarea
                value={note}
                onChange={handleNoteChange}
                readOnly={isReadonly}
                placeholder={isReadonly ? "Faqat ko'rish rejimi." : "Bu yerga savol bo'yicha batafsil javob va fikr-mulohazangizni yozing..."}
                style={{
                  flex: 1,
                  width: "100%",
                  background: "var(--bg-primary)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 12,
                  padding: "1.25rem",
                  color: "var(--text-primary)",
                  fontSize: "0.95rem",
                  lineHeight: 1.7,
                  resize: "none",
                  fontFamily: "inherit",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
              <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "var(--text-muted)", textAlign: "right", flexShrink: 0 }}>
                {note.length} belgi
              </div>
            </div>
          )}
        </div>
      </div>

      {showExitConfirm && (
        <ExitConfirmModal
          count={violationsCount}
          max={maxViolations}
          onConfirm={handleConfirmExit}
          onCancel={() => setShowExitConfirm(false)}
          loading={exiting}
        />
      )}

      {showViolation && violationData && (
        <ViolationModal
          count={violationData.violations_count}
          max={violationData.max_allowed}
          isDisqualified={violationData.is_disqualified}
          onClose={() => setShowViolation(false)}
          onExit={() => navigate("/")}
        />
      )}

      {submitResult && (
        <ResultModal result={submitResult} onClose={() => { setSubmitResult(null); navigate("/"); }} />
      )}
    </div>
  );
}
