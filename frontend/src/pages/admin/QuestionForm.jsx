import { useState, useEffect } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import api from "../../api/client";
import Editor from "@monaco-editor/react";

export default function QuestionForm() {
  const { challengeId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const dayId = searchParams.get("dayId");

  const [days, setDays] = useState([]);
  const [selectedDayId, setSelectedDayId] = useState(dayId || "");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    title: "",
    question_type: "practical",
    difficulty: "medium",
    body_text: "",
    starter_code: "def solution():\n    pass",
  });

  useEffect(() => {
    api.get(`/api/admin/challenges/${challengeId}/days`)
      .then(r => setDays(r.data))
      .catch(() => {});
  }, [challengeId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedDayId) return setError("Kun tanlang");
    if (!form.title.trim()) return setError("Savol nomi kiriting");
    if (!form.body_text.trim()) return setError("Savol matni kiriting");

    setLoading(true);
    setError("");
    try {
      await api.post("/api/admin/questions", {
        challenge_day_id: selectedDayId,
        title: form.title,
        question_type: form.question_type,
        body_text: form.body_text,
        difficulty: form.difficulty,
        starter_code: form.question_type === "practical" ? form.starter_code : "",
        test_cases: null,
      });
      setSuccess("Savol muvaffaqiyatli qo'shildi!");
      setForm({ title: "", question_type: "practical", difficulty: "medium", body_text: "", starter_code: "def solution():\n    pass" });
      setTimeout(() => navigate(`/admin/challenge/${challengeId}/questions?dayId=${selectedDayId}`), 1500);
    } catch (err) {
      setError(err.response?.data?.detail || "Xatolik yuz berdi");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-primary)", padding: "2rem 1rem" }}>
      <div style={{ maxWidth: 800, margin: "0 auto" }}>
        <div style={{ marginBottom: "2rem" }}>
          <button onClick={() => navigate(`/admin/challenge/${challengeId}/questions${dayId ? `?dayId=${dayId}` : ""}`)} style={{ background: "transparent", border: "1px solid var(--border-color)", color: "var(--text-secondary)", padding: "0.5rem 1rem", borderRadius: 8, cursor: "pointer", marginBottom: "1rem" }}>
            Orqaga
          </button>
          <h1 style={{ color: "var(--text-primary)", fontSize: "1.8rem", fontWeight: 700, margin: 0 }}>
            Yangi Savol Qo'shish
          </h1>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <div className="form-group">
            <label className="form-label">QAYSI KUN UCHUN? *</label>
            <select value={selectedDayId} onChange={e => setSelectedDayId(e.target.value)} className="form-input" required>
              <option value="">Kun tanlang...</option>
              {days.map(d => (
                <option key={d.id} value={d.id}>#{d.day_number}-kun — {d.title || "nomsiz"}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">SAVOL NOMI *</label>
            <input type="text" className="form-input" placeholder="Masalan: Ikki sonning yig'indisi" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} required />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="form-group">
              <label className="form-label">SAVOL TURI *</label>
              <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem" }}>
                {[{ value: "practical", label: "Amaliy", icon: "🖥️", desc: "Kod yozish" }, { value: "theoretical", label: "Nazariy", icon: "📝", desc: "Izoh yozish" }].map(opt => (
                  <label key={opt.value} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", padding: "1rem", borderRadius: 12, border: `2px solid ${form.question_type === opt.value ? "var(--accent-primary)" : "var(--border-color)"}`, background: form.question_type === opt.value ? "rgba(99,102,241,0.1)" : "var(--bg-secondary)", cursor: "pointer", transition: "all 0.2s" }}>
                    <input type="radio" value={opt.value} checked={form.question_type === opt.value} onChange={e => setForm({ ...form, question_type: e.target.value })} style={{ display: "none" }} />
                    <span style={{ fontSize: "1.5rem", marginBottom: "0.25rem" }}>{opt.icon}</span>
                    <span style={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "0.9rem" }}>{opt.label}</span>
                    <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>{opt.desc}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">QIYINLIK DARAJASI *</label>
              <select value={form.difficulty} onChange={e => setForm({ ...form, difficulty: e.target.value })} className="form-input">
                <option value="easy">Oson</option>
                <option value="medium">O'rta</option>
                <option value="hard">Qiyin</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">SAVOL MATNI *</label>
            <textarea className="form-input" placeholder="Savol matnini kiriting. HTML ham qo'llasa bo'ladi..." value={form.body_text} onChange={e => setForm({ ...form, body_text: e.target.value })} rows={6} style={{ resize: "vertical", fontFamily: "inherit" }} required />
          </div>

          {form.question_type === "practical" && (
            <div className="form-group">
              <label className="form-label">BOSHLANG'ICH KOD (Starter Code)</label>
              <div style={{ border: "1px solid var(--border-color)", borderRadius: 12, overflow: "hidden", minHeight: 200 }}>
                <Editor
                  height="200px"
                  defaultLanguage="python"
                  theme="vs-dark"
                  value={form.starter_code}
                  onChange={val => setForm({ ...form, starter_code: val || "" })}
                  options={{ minimap: { enabled: false }, fontSize: 14, lineNumbers: "on", scrollBeyondLastLine: false, padding: { top: 12, bottom: 12 } }}
                />
              </div>
            </div>
          )}

          {error && <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: "0.75rem 1rem", color: "#ef4444" }}>❌ {error}</div>}
          {success && <div style={{ background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.3)", borderRadius: 10, padding: "0.75rem 1rem", color: "#22c55e" }}>✅ {success}</div>}

          <button type="submit" disabled={loading} style={{ background: loading ? "var(--bg-tertiary)" : "linear-gradient(135deg, var(--accent-primary), #8b5cf6)", color: "white", border: "none", borderRadius: 12, padding: "1rem 2rem", fontSize: "1rem", fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", transition: "all 0.2s" }}>
            {loading ? "Saqlanmoqda..." : "Savolni Qo'shish"}
          </button>
        </form>
      </div>
    </div>
  );
}