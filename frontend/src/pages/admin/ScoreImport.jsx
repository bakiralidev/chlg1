import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import { toast } from "react-hot-toast";
import Navbar from "../../components/Navbar";
import AdminNav from "../../components/AdminNav";

const CAT_LABELS = { approach: "Yondashuv", correctness: "To'g'rilik", speed: "Tezlik", logic: "Mantiq", memory: "Xotira" };

export default function ScoreImport() {
  const navigate = useNavigate();
  const [challenges, setChallenges] = useState([]);
  const [selectedChallenge, setSelectedChallenge] = useState("");
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [aiScores, setAiScores] = useState([]);
  const [loadingScores, setLoadingScores] = useState(false);

  useEffect(() => {
    api.getAdminChallenges().then(r => setChallenges(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedChallenge) { setAiScores([]); return; }
    setLoadingScores(true);
    api.getAIScores(selectedChallenge).then(r => setAiScores(r.data)).catch(() => {}).finally(() => setLoadingScores(false));
  }, [selectedChallenge]);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.name.match(/\.(xlsx|xls)$/)) setFile(dropped);
    else toast.error("Faqat .xlsx yoki .xls fayl qabul qilinadi");
  };

  const handleImport = async () => {
    if (!selectedChallenge) return toast.error("Challenge tanlang");
    if (!file) return toast.error("Excel fayl yuklang");
    setLoading(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.importAIScores(selectedChallenge, formData);
      setResult(data);
      toast.success(`${data.imported_scores} ta ball muvaffaqiyatli kiritildi!`);
      api.getAIScores(selectedChallenge).then(r => setAiScores(r.data)).catch(() => {});
    } catch (err) {
      toast.error(err.response?.data?.detail || "Import xatoligi");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="container" style={{ paddingTop: "2rem", paddingBottom: "4rem" }}>
          <AdminNav />
          <div style={{ marginBottom: "2rem" }}>
            <h1 style={{ color: "var(--text-primary)", fontSize: "1.8rem", fontWeight: 700, margin: 0 }}>
              🤖 AI Baholash Import
            </h1>
          <p style={{ color: "var(--text-muted)", marginTop: "0.5rem" }}>
            AI agent tomonidan baholangan natijalarni Excel orqali yuklang. Tizim foydalanuvchilarni email bo'yicha avtomatik moslashtiradi.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
          <div>
            <div className="form-group" style={{ marginBottom: "1.5rem" }}>
              <label className="form-label">CHALLENGE TANLANG *</label>
              <select value={selectedChallenge} onChange={e => setSelectedChallenge(e.target.value)} className="form-input">
                <option value="">Challenge tanlang...</option>
                {challenges.map(c => <option key={c.id} value={c.id}>{c.name} ({c.status})</option>)}
              </select>
            </div>

            <div style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)", borderRadius: 12, padding: "1rem", marginBottom: "1.5rem" }}>
              <p style={{ color: "var(--accent-primary)", fontWeight: 600, marginBottom: "0.5rem" }}>Excel Ustunlari Formati:</p>
              <code style={{ fontSize: "0.8rem", color: "var(--text-secondary)", display: "block", lineHeight: 1.8 }}>
                email | day_number | approach | correctness | speed | logic | memory | notes
              </code>
              <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", marginTop: "0.5rem", marginBottom: 0 }}>
                * Barcha ball ustunlari 0-10 oraligida. day_number ixtiyoriy.
              </p>
            </div>

            <div
              onDrop={handleDrop}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onClick={() => document.getElementById("excel-file-input").click()}
              style={{ border: `2px dashed ${dragOver ? "var(--accent-primary)" : "var(--border-color)"}`, borderRadius: 16, padding: "2.5rem", textAlign: "center", cursor: "pointer", background: dragOver ? "rgba(99,102,241,0.08)" : "var(--bg-secondary)", transition: "all 0.2s", marginBottom: "1.5rem" }}
            >
              <input id="excel-file-input" type="file" accept=".xlsx,.xls" style={{ display: "none" }} onChange={e => { if (e.target.files[0]) setFile(e.target.files[0]); }} />
              <div style={{ fontSize: "3rem", marginBottom: "0.75rem" }}>📊</div>
              {file ? (
                <div>
                  <p style={{ color: "var(--success)", fontWeight: 600, marginBottom: "0.25rem" }}>✅ {file.name}</p>
                  <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", margin: 0 }}>{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div>
                  <p style={{ color: "var(--text-primary)", fontWeight: 600, marginBottom: "0.25rem" }}>Excel faylni shu yerga tashlang</p>
                  <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", margin: 0 }}>yoki bosib tanlang (.xlsx, .xls)</p>
                </div>
              )}
            </div>

            <button onClick={handleImport} disabled={loading || !file || !selectedChallenge} style={{ width: "100%", background: loading || !file || !selectedChallenge ? "var(--bg-tertiary)" : "linear-gradient(135deg, var(--accent-primary), #8b5cf6)", color: "white", border: "none", borderRadius: 12, padding: "1rem", fontSize: "1rem", fontWeight: 600, cursor: loading || !file || !selectedChallenge ? "not-allowed" : "pointer", transition: "all 0.2s" }}>
              {loading ? "Import qilinmoqda..." : "Balllarni Import Qilish"}
            </button>

            {result && (
              <div style={{ marginTop: "1.5rem", background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.2)", borderRadius: 12, padding: "1rem" }}>
                <p style={{ color: "var(--success)", fontWeight: 600, marginBottom: "0.75rem" }}>Import natijasi:</p>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
                  {[["Jami qatorlar", result.total_rows], ["Topilgan foydalanuvchilar", result.matched_users], ["Kiritilgan ballar", result.imported_scores], ["O'tkazib yuborilgan", result.skipped]].map(([label, val]) => (
                    <div key={label} style={{ background: "var(--bg-primary)", borderRadius: 8, padding: "0.5rem 0.75rem" }}>
                      <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>{label}</div>
                      <div style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: "1.2rem" }}>{val}</div>
                    </div>
                  ))}
                </div>
                {result.errors?.length > 0 && (
                  <div style={{ marginTop: "0.75rem" }}>
                    <p style={{ color: "var(--warning)", fontSize: "0.85rem", marginBottom: "0.5rem" }}>Xatoliklar:</p>
                    {result.errors.map((e, i) => <div key={i} style={{ color: "var(--text-muted)", fontSize: "0.8rem", lineHeight: 1.6 }}>• {e}</div>)}
                  </div>
                )}
              </div>
            )}
          </div>

          <div>
            <h2 style={{ color: "var(--text-primary)", fontSize: "1.2rem", fontWeight: 600, marginBottom: "1rem" }}>AI Baholash Natijalari</h2>
            {!selectedChallenge ? (
              <div style={{ background: "var(--bg-secondary)", borderRadius: 12, padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>Challenge tanlang</div>
            ) : loadingScores ? (
              <div style={{ textAlign: "center", padding: "2rem" }}><div className="spinner" /></div>
            ) : aiScores.length === 0 ? (
              <div style={{ background: "var(--bg-secondary)", borderRadius: 12, padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>Hali ball kiritilmagan</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {aiScores.map((user, idx) => (
                  <div key={user.user_id} style={{ background: "var(--bg-secondary)", borderRadius: 12, padding: "1rem", border: `1px solid ${idx === 0 ? "rgba(251,191,36,0.4)" : "var(--border-color)"}` }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
                      <span style={{ width: 28, height: 28, borderRadius: "50%", background: idx === 0 ? "#fbbf24" : idx === 1 ? "#9ca3af" : idx === 2 ? "#cd7c2f" : "var(--bg-tertiary)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.85rem", fontWeight: 700, color: idx < 3 ? "#000" : "var(--text-muted)" }}>
                        {idx + 1}
                      </span>
                      <div>
                        <div style={{ color: "var(--text-primary)", fontWeight: 600 }}>{user.username}</div>
                        <div style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>{user.email}</div>
                      </div>
                      <div style={{ marginLeft: "auto", textAlign: "right" }}>
                        <div style={{ color: "var(--accent-primary)", fontWeight: 700, fontSize: "1.1rem" }}>{user.total_score}</div>
                        <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>umumiy ball</div>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                      {Object.entries(user.days || {}).map(([day, cats]) =>
                        Object.entries(cats).map(([cat, val]) => (
                          <span key={`${day}-${cat}`} style={{ background: "var(--bg-primary)", borderRadius: 6, padding: "0.2rem 0.5rem", fontSize: "0.72rem", color: "var(--text-secondary)" }}>
                            {CAT_LABELS[cat] || cat}: <strong>{val.score}/10</strong>
                          </span>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  </>
);
}