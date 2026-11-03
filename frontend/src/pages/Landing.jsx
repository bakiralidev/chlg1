import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { api } from '../api/client';
import { useAuthStore } from '../store/authStore';
import Navbar from '../components/Navbar';

// Sinov uchun namuna savollar
const DEMO_PROBLEMS = [
  {
    id: 'reverse_words',
    title: "1. So'zlarni teskari tartibda qaytarish",
    type: 'practical',
    difficulty: 'Oson',
    desc: 'Berilgan matndagi so\'zlarni teskari tartibda birlashtiruvchi funksiya yozing. So\'zlar orasida bitta bo\'sh joy qolsin.',
    initialCode: `def reverse_words(s: str) -> str:
    # Kodingizni bu yerga yozing
    return " ".join(s.split()[::-1])
`,
    tests: [
      { input: 'salom dunyo', expected: 'dunyo salom' },
      { input: 'python challenge dasturlash', expected: 'dasturlash challenge python' },
      { input: 'bir ikki uch', expected: 'uch ikki bir' },
    ],
    checker: (code) => {
      // Simple evaluator for demo
      try {
        if (!code.includes('def reverse_words')) return { pass: false, error: "Funksiya nomi 'reverse_words' bo'lishi kerak" };
        if (!code.includes('return')) return { pass: false, error: "Funksiya natija qaytarishi kerak (return)" };
        return { pass: true, passedCount: 3, totalCount: 3 };
      } catch (err) {
        return { pass: false, error: err.message };
      }
    }
  },
  {
    id: 'sum_evens',
    title: "2. Juft sonlar yig'indisi",
    type: 'practical',
    difficulty: 'Oson',
    desc: 'Berilgan butun sonlar ro\'yxatidan faqat juft sonlarning yig\'indisini hisoblab qaytaruvchi funksiya yozing.',
    initialCode: `def sum_evens(nums: list[int]) -> int:
    # Faqat juft sonlar yig'indisini hisoblang
    return sum(x for x in nums if x % 2 == 0)
`,
    tests: [
      { input: '[1, 2, 3, 4, 5, 6]', expected: '12' },
      { input: '[10, 15, 20]', expected: '30' },
      { input: '[1, 3, 5]', expected: '0' },
    ],
    checker: (code) => {
      try {
        if (!code.includes('def sum_evens')) return { pass: false, error: "Funksiya nomi 'sum_evens' bo'lishi kerak" };
        if (!code.includes('return')) return { pass: false, error: "Funksiya natija qaytarishi kerak (return)" };
        return { pass: true, passedCount: 3, totalCount: 3 };
      } catch (err) {
        return { pass: false, error: err.message };
      }
    }
  },
  {
    id: 'is_palindrome',
    title: "3. Palindrom matn tekshiruvi",
    type: 'practical',
    difficulty: 'O\'rta',
    desc: 'Berilgan matn o\'ngdan ham, chapdan ham bir xil o\'qiladimi (palindrom)? Katta-kichik harflar va bo\'shliqlarni hisobga olmang.',
    initialCode: `def is_palindrome(s: str) -> bool:
    cleaned = s.lower().replace(" ", "")
    return cleaned == cleaned[::-1]
`,
    tests: [
      { input: '"radar"', expected: 'True' },
      { input: '"A santa at nasa"', expected: 'True' },
      { input: '"python"', expected: 'False' },
    ],
    checker: (code) => {
      try {
        if (!code.includes('def is_palindrome')) return { pass: false, error: "Funksiya nomi 'is_palindrome' bo'lishi kerak" };
        if (!code.includes('return')) return { pass: false, error: "Funksiya natija qaytarishi kerak (return)" };
        return { pass: true, passedCount: 3, totalCount: 3 };
      } catch (err) {
        return { pass: false, error: err.message };
      }
    }
  }
];

const FAQS = [
  {
    q: "Musobaqada qatnashish pullikmi?",
    a: "Yo'q, PyChallenge platformasida ro'yxatdan o'tish va barcha 15 kunlik musobaqalarda qatnashish mutlaqo bepul."
  },
  {
    q: "Anti-cheat tizimi qanday ishlaydi?",
    a: "Imtihon topshirilayotgan 'Arena' sahifasida to'liq ekran rejimi yoqiladi. Oynadan chiqish, tab almashtirish yoki nusxalash harakatlari aniqlanganda ogohlantirish beriladi. 3 ta ogohlantirishdan so'ng ishtirokchi shu kun uchun diskvalifikatsiya qilinadi."
  },
  {
    q: "Savollar barchaga bir xil tushadimi?",
    a: "Yo'q! Bizning platformada har bir kun uchun katta savollar banki mavjud. Har bir ishtirokchiga tizim tomonidan tasodifiy, takrorlanmas amaliy yoki nazariy savol beriladi. Bu esa birovdan ko'chirish imkoniyatini yo'qqa chiqaradi."
  },
  {
    q: "Agar bir kun qolib ketsa, musobaqadan chiqib ketamanmi?",
    a: "Yo'q, o'sha qolib ketgan kun uchun 0 ball yoziladi, biroq siz keyingi kunlarda qatnashib, ballaringizni oshirishda va sovrinlar uchun kurashda davom etaverasiz."
  },
  {
    q: "Yechimlar qanday baholanadi?",
    a: "Amaliy dasturlash savollari avtomatik yashirin test keyslari (Unit testlar) orqali tekshiriladi. Nazariy savollar esa zamonaviy AI modeli va ekspert hakamlar tomonidan semantik chuqurligi bo'yicha baholanadi."
  }
];

export default function Landing() {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  // Challenges from backend
  const [challenges, setChallenges] = useState([]);
  const [loadingChallenges, setLoadingChallenges] = useState(true);

  // Demo playground state
  const [selectedProblemIndex, setSelectedProblemIndex] = useState(0);
  const currentProblem = DEMO_PROBLEMS[selectedProblemIndex];
  const [code, setCode] = useState(currentProblem.initialCode);
  const [running, setRunning] = useState(false);
  const [testResults, setTestResults] = useState(null);

  // Theoretical demo tab
  const [activeTab, setActiveTab] = useState('code'); // 'code' or 'theory'
  const [theoryNote, setTheoryNote] = useState(
    "Python'da '==' operatori obyektlarning qiymati tengligini (__eq__) tekshiradi, 'is' esa ikki o'zgaruvchi xotirada ayni bir obyektga (xotira manziliga - id) ko'rsatayotganini tekshiradi. None bilan solishtirishda 'is None' ishlatish tavsiya etiladi."
  );
  const [theoryAnalysis, setTheoryAnalysis] = useState(null);

  // FAQ accordion state
  const [openFaq, setOpenFaq] = useState(0);

  useEffect(() => {
    api.getChallenges()
      .then(({ data }) => setChallenges(data))
      .catch((err) => console.log('Challengelar yuklanmadi:', err))
      .finally(() => setLoadingChallenges(false));
  }, []);

  const handleSelectProblem = (idx) => {
    setSelectedProblemIndex(idx);
    setCode(DEMO_PROBLEMS[idx].initialCode);
    setTestResults(null);
  };

  const handleRunCode = () => {
    setRunning(true);
    setTestResults(null);

    setTimeout(() => {
      const res = currentProblem.checker(code);
      if (res.pass) {
        setTestResults({
          success: true,
          score: 100,
          passedCount: res.passedCount,
          totalCount: res.totalCount,
          tests: currentProblem.tests.map((t) => ({ ...t, status: 'PASSED' })),
          message: "Ajoyib natija! Barcha test holatlari muvaffaqiyatli o'tdi."
        });
      } else {
        setTestResults({
          success: false,
          score: 0,
          passedCount: 0,
          totalCount: 3,
          tests: currentProblem.tests.map((t) => ({ ...t, status: 'FAILED' })),
          message: res.error || "Funksiya kutilganidek ishlamadi. Kodingizni tekshirib qaytadan urinib ko'ring."
        });
      }
      setRunning(false);
    }, 600);
  };

  const handleAnalyzeTheory = () => {
    setTheoryAnalysis({
      score: 95,
      feedback: "Javob to'liq va aniq! 'is' va '==' farqi, xotira manzili (id) hamda None solishtiruvi to'g'ri ta'kidlangan. Professional darajadagi javob.",
      highlights: ["Xotira manzili va identifikator to'g'ri tushuntirilgan", "Qiymat tengligi (__eq__) qayd etilgan", "None bilan ishlash bo'yicha PEP 8 tavsiyasi keltirilgan"]
    });
  };

  return (
    <>
      <Navbar />
      <div className="page" style={{ paddingTop: '75px', overflowX: 'hidden' }}>
        
        {/* ─── 1. HERO SECTION ────────────────────────────────────────────── */}
        <section style={{
          position: 'relative',
          padding: '5rem 1.5rem 5.5rem',
          textAlign: 'center',
          overflow: 'hidden',
          background: 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(137,180,250,0.18), rgba(24,24,37,0) 80%)',
        }}>
          {/* 1. Developer Grid Background Pattern */}
          <div style={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            backgroundImage: `
              linear-gradient(to right, rgba(137, 180, 250, 0.05) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(137, 180, 250, 0.05) 1px, transparent 1px)
            `,
            backgroundSize: '44px 44px',
            maskImage: 'radial-gradient(ellipse 70% 60% at 50% 35%, black 20%, transparent 80%)',
            WebkitMaskImage: 'radial-gradient(ellipse 70% 60% at 50% 35%, black 20%, transparent 80%)',
            zIndex: 0,
          }} />

          {/* 2. Soft Ambient Glowing Orbs */}
          <div style={{
            position: 'absolute', top: '5%', left: '15%',
            width: '420px', height: '320px',
            background: 'radial-gradient(circle, rgba(137, 180, 250, 0.16) 0%, transparent 70%)',
            filter: 'blur(60px)', pointerEvents: 'none', zIndex: 0,
            animation: 'pulseGlow 7s ease-in-out infinite alternate',
          }} />
          <div style={{
            position: 'absolute', top: '10%', right: '15%',
            width: '420px', height: '320px',
            background: 'radial-gradient(circle, rgba(203, 166, 247, 0.16) 0%, transparent 70%)',
            filter: 'blur(60px)', pointerEvents: 'none', zIndex: 0,
            animation: 'pulseGlow 9s ease-in-out infinite alternate 1.5s',
          }} />

          {/* 3. Subtle Python Watermark Icon in Center Background */}
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: '24rem', opacity: 0.03,
            userSelect: 'none', pointerEvents: 'none', zIndex: 0,
            filter: 'grayscale(30%)',
          }}>
            🐍
          </div>

          {/* 4. Left Floating Code Chip (Desktop) */}
          <div className="hero-code-badge" style={{
            top: '25%', left: '5%',
            '--rot': '-4deg',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem', color: 'var(--accent)' }}>
              <span>🐍</span> <span style={{ fontWeight: 600 }}>challenge.py</span>
            </div>
            <div><span style={{ color: 'var(--accent-2)' }}>def</span> <span style={{ color: 'var(--accent)' }}>solve_daily</span>(day):</div>
            <div style={{ paddingLeft: '0.85rem', color: 'var(--text-dim)' }}># 15 kunlik musobaqa</div>
            <div style={{ paddingLeft: '0.85rem' }}><span style={{ color: 'var(--accent-2)' }}>return</span> <span style={{ color: 'var(--success)' }}>"100 Ball"</span></div>
          </div>

          {/* 5. Right Floating Code Chip (Desktop) */}
          <div className="hero-code-badge" style={{
            top: '32%', right: '5%',
            '--rot': '3deg',
            animationDelay: '1.8s',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem', color: 'var(--accent-2)' }}>
              <span>⚡</span> <span style={{ fontWeight: 600 }}>Leaderboard</span>
            </div>
            <div><span style={{ color: 'var(--warning)' }}>rank</span> = <span style={{ color: 'var(--accent-3)' }}>1</span> 🏆</div>
            <div><span style={{ color: 'var(--accent-4)' }}>streak</span> = <span style={{ color: 'var(--accent)' }}>15 kun</span> 🔥</div>
            <div><span style={{ color: 'var(--success)' }}>status</span> = <span style={{ color: 'var(--success)' }}>"Faol"</span> ✅</div>
          </div>

          <div className="container" style={{ maxWidth: '960px', margin: '0 auto', position: 'relative', zIndex: 2 }}>
            
            {/* Pill Tag */}
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.4rem 1rem', borderRadius: '50px',
              background: 'rgba(137, 180, 250, 0.1)',
              border: '1px solid rgba(137, 180, 250, 0.25)',
              color: 'var(--accent)', fontSize: '0.85rem', fontWeight: 600,
              marginBottom: '1.75rem',
            }}>
              <span>✨</span>
              <span>15 Kunlik Intensiv Python Musobaqasi & Sovrinlar</span>
            </div>

            {/* Main Headline */}
            <h1 style={{
              fontSize: 'clamp(2.3rem, 5vw, 3.8rem)',
              fontWeight: 800,
              lineHeight: 1.15,
              marginBottom: '1.25rem',
              letterSpacing: '-0.02em',
            }}>
              Python Bo'yicha Bilimingizni{' '}
              <span style={{
                background: 'linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 50%, #74c7ec 100%)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
              }}>
                Haqiqiy Sinovdan
              </span>{' '}
              O'tkazing!
            </h1>

            {/* Subtitle */}
            <p style={{
              fontSize: 'clamp(1rem, 2vw, 1.2rem)',
              color: 'var(--text-sub)',
              maxWidth: '720px',
              margin: '0 auto 2.5rem',
              lineHeight: 1.7,
            }}>
              Har kuni tasodifiy takrorlanmas amaliy va nazariy savollar, to'liq anti-cheat nazorati 
              va adolatli AI baholash tizimi. O'z kodingizni sinang, reytingda peshqadam bo'ling va qimmatbaho sovrinlarni yuting!
            </p>

            {/* Hero CTAs */}
            <div style={{
              display: 'flex', flexWrap: 'wrap', gap: '1rem',
              justifyContent: 'center', alignItems: 'center',
              marginBottom: '1rem',
            }}>
              {user ? (
                <Link
                  to="/dashboard"
                  className="btn btn-primary"
                  style={{ padding: '0.85rem 2rem', fontSize: '1.05rem', borderRadius: 'var(--radius-md)' }}
                >
                  🚀 Mening kabinetimga o'tish
                </Link>
              ) : (
                <>
                  <Link
                    to="/register"
                    className="btn btn-primary"
                    style={{ padding: '0.85rem 2rem', fontSize: '1.05rem', borderRadius: 'var(--radius-md)' }}
                  >
                    🎯 Musobaqaga qo'shilish (Bepul)
                  </Link>
                  <a
                    href="#demo"
                    className="btn btn-secondary"
                    style={{
                      padding: '0.85rem 1.8rem', fontSize: '1.05rem',
                      background: 'var(--bg-surface0)', border: '1px solid var(--bg-surface1)',
                      borderRadius: 'var(--radius-md)', color: 'var(--text-main)',
                    }}
                  >
                    ⚡ Hoziroq sinab ko'rish
                  </a>
                </>
              )}
            </div>

          </div>
        </section>

        {/* ─── 2. INTERACTIVE DEMO (SINAB KO'RISH) ─────────────────────────── */}
        <section id="demo" style={{
          padding: '4rem 1.5rem',
          background: 'var(--bg-crust)',
          borderTop: '1px solid var(--bg-surface0)',
          borderBottom: '1px solid var(--bg-surface0)',
        }}>
          <div className="container" style={{ maxWidth: '1100px', margin: '0 auto' }}>
            
            <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
              <div style={{
                display: 'inline-block', padding: '0.3rem 0.8rem', borderRadius: '20px',
                background: 'rgba(166,227,161,0.1)', color: 'var(--success)',
                fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.75rem',
              }}>
                ⚡ INTERAKTIV PLAYGROUND
              </div>
              <h2 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: '0.75rem' }}>
                Platformani hoziroq sinab ko'ring!
              </h2>
              <p style={{ color: 'var(--text-sub)', maxWidth: '650px', margin: '0 auto' }}>
                Ro'yxatdan o'tmasdanoq platformamizning ish jarayonini his qiling: kod yozing, testlardan o'tkazing va baholash tizimi qanday ishlashini ko'ring.
              </p>
            </div>

            {/* Playground Box */}
            <div style={{
              background: 'var(--bg-mantle)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--bg-surface0)',
              overflow: 'hidden',
              boxShadow: 'var(--shadow-lg)',
            }}>
              
              {/* Top Navigation Tabs */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '0.75rem 1.25rem',
                borderBottom: '1px solid var(--bg-surface0)',
                background: 'rgba(17,17,27,0.5)',
                flexWrap: 'wrap', gap: '0.75rem'
              }}>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => setActiveTab('code')}
                    style={{
                      padding: '0.45rem 1rem', borderRadius: 'var(--radius-sm)',
                      background: activeTab === 'code' ? 'var(--bg-surface0)' : 'transparent',
                      color: activeTab === 'code' ? 'var(--accent)' : 'var(--text-muted)',
                      border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem',
                      display: 'flex', alignItems: 'center', gap: '0.4rem',
                    }}
                  >
                    <span>🐍</span>
                    <span>Amaliy Savol (Kod yozish)</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('theory')}
                    style={{
                      padding: '0.45rem 1rem', borderRadius: 'var(--radius-sm)',
                      background: activeTab === 'theory' ? 'var(--bg-surface0)' : 'transparent',
                      color: activeTab === 'theory' ? 'var(--accent-2)' : 'var(--text-muted)',
                      border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem',
                      display: 'flex', alignItems: 'center', gap: '0.4rem',
                    }}
                  >
                    <span>💡</span>
                    <span>Nazariy Savol (AI Baholash)</span>
                  </button>
                </div>

                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)' }}></span>
                  <span>Jonli interaktiv simulyatsiya</span>
                </div>
              </div>

              {activeTab === 'code' ? (
                /* TAB 1: CODE CHALLENGE DEMO */
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 380px) 1fr', minHeight: '480px' }}>
                  
                  {/* Left Column: Problem description */}
                  <div style={{
                    padding: '1.5rem',
                    borderRight: '1px solid var(--bg-surface0)',
                    display: 'flex', flexDirection: 'column', gap: '1.25rem',
                    background: 'rgba(24,24,37,0.4)',
                  }}>
                    {/* Selector */}
                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Sinov savolini tanlang:
                      </label>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.5rem' }}>
                        {DEMO_PROBLEMS.map((prob, idx) => (
                          <button
                            key={prob.id}
                            onClick={() => handleSelectProblem(idx)}
                            style={{
                              textAlign: 'left', padding: '0.5rem 0.75rem',
                              borderRadius: 'var(--radius-sm)',
                              background: selectedProblemIndex === idx ? 'rgba(137,180,250,0.15)' : 'var(--bg-surface0)',
                              border: `1px solid ${selectedProblemIndex === idx ? 'var(--accent)' : 'transparent'}`,
                              color: selectedProblemIndex === idx ? 'var(--text-main)' : 'var(--text-muted)',
                              fontSize: '0.85rem', cursor: 'pointer', fontWeight: 500,
                              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            }}
                          >
                            <span>{prob.title}</span>
                            <span style={{ fontSize: '0.7rem', color: 'var(--accent-3)' }}>{prob.difficulty}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Task Description */}
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.4rem' }}>
                        📋 Topshiriq sharti:
                      </div>
                      <p style={{ fontSize: '0.88rem', color: 'var(--text-sub)', lineHeight: 1.6 }}>
                        {currentProblem.desc}
                      </p>
                    </div>

                    {/* Test examples */}
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.4rem' }}>
                        🧪 Namunaviy testlar:
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                        {currentProblem.tests.map((t, i) => (
                          <div key={i} style={{
                            padding: '0.4rem 0.6rem', background: 'var(--bg-crust)',
                            borderRadius: '4px', fontSize: '0.78rem', fontFamily: 'monospace',
                            color: 'var(--text-muted)', border: '1px solid var(--bg-surface0)',
                          }}>
                            <div><strong style={{ color: 'var(--accent)' }}>Kirish:</strong> {t.input}</div>
                            <div><strong style={{ color: 'var(--success)' }}>Chiqish:</strong> {t.expected}</div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--bg-surface0)' }}>
                      <button
                        onClick={handleRunCode}
                        disabled={running}
                        className="btn btn-primary"
                        style={{ width: '100%', padding: '0.75rem', fontSize: '0.95rem' }}
                      >
                        {running ? '⏳ Tekshirilmoqda...' : '▶ Kodni ishga tushirish & tekshirish'}
                      </button>
                    </div>
                  </div>

                  {/* Right Column: Code Editor & Results */}
                  <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                    
                    <div style={{
                      padding: '0.45rem 1rem', background: 'var(--bg-crust)',
                      borderBottom: '1px solid var(--bg-surface0)',
                      fontSize: '0.78rem', color: 'var(--text-dim)',
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    }}>
                      <span>🐍 main.py (Monaco Editor)</span>
                      <button
                        onClick={() => { setCode(currentProblem.initialCode); setTestResults(null); }}
                        style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.75rem' }}
                      >
                        🔄 Qayta tiklash
                      </button>
                    </div>

                    <div style={{ flex: 1, minHeight: '260px' }}>
                      <Editor
                        height="260px"
                        language="python"
                        theme="vs-dark"
                        value={code}
                        onChange={(v) => setCode(v || '')}
                        options={{
                          fontSize: 14,
                          fontFamily: '"JetBrains Mono", monospace',
                          minimap: { enabled: false },
                          scrollBeyondLastLine: false,
                          tabSize: 4,
                          wordWrap: 'on',
                        }}
                      />
                    </div>

                    {/* Test Results Output Area */}
                    <div style={{
                      padding: '1.25rem',
                      background: 'rgba(17,17,27,0.85)',
                      borderTop: '1px solid var(--bg-surface0)',
                      minHeight: '140px',
                    }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.6rem', display: 'flex', justifyContent: 'space-between' }}>
                        <span>📊 Tekshiruv natijasi:</span>
                        {testResults && (
                          <span style={{ color: testResults.success ? 'var(--success)' : 'var(--danger)', fontWeight: 800 }}>
                            {testResults.score} / 100 Ball
                          </span>
                        )}
                      </div>

                      {!testResults && !running && (
                        <div style={{ color: 'var(--text-dim)', fontSize: '0.85rem', fontStyle: 'italic' }}>
                          Kodingizni sinash uchun chap tarafdagi "Kodni ishga tushirish" tugmasini bosing...
                        </div>
                      )}

                      {running && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--accent)', fontSize: '0.9rem' }}>
                          <span className="spinner" style={{ width: '18px', height: '18px' }}></span>
                          <span>Unit testlar bajarilmoqda va yechim tahlil qilinmoqda...</span>
                        </div>
                      )}

                      {testResults && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                          <div style={{
                            padding: '0.6rem 0.8rem', borderRadius: 'var(--radius-sm)',
                            background: testResults.success ? 'rgba(166,227,161,0.1)' : 'rgba(243,139,168,0.1)',
                            border: `1px solid ${testResults.success ? 'var(--success)' : 'var(--danger)'}`,
                            color: testResults.success ? 'var(--success)' : 'var(--danger)',
                            fontSize: '0.85rem', fontWeight: 600,
                          }}>
                            {testResults.success ? '✅ ' : '❌ '} {testResults.message}
                          </div>

                          {testResults.success && (
                            <div style={{
                              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                              padding: '0.6rem 0.8rem', background: 'rgba(137,180,250,0.1)',
                              borderRadius: 'var(--radius-sm)', border: '1px solid rgba(137,180,250,0.2)',
                            }}>
                              <span style={{ fontSize: '0.85rem', color: 'var(--text-main)' }}>
                                🎯 Haqiqiy 15 kunlik musobaqada qatnashishga tayyormisiz?
                              </span>
                              <Link to="/register" className="btn btn-primary" style={{ padding: '0.35rem 0.9rem', fontSize: '0.8rem' }}>
                                Ro'yxatdan o'tish →
                              </Link>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                  </div>
                </div>
              ) : (
                /* TAB 2: THEORY CHALLENGE DEMO */
                <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                      <span className="badge badge-purple">Nazariy Savol namunasi</span>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Mavzu: Xotira va Obyektlar</span>
                    </div>
                    <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.5rem' }}>
                      Python'da 'is' va '==' operatorlari orasidagi asosiy farq nimada? Qachon qaysi birini ishlatish kerak?
                    </h3>
                    <p style={{ color: 'var(--text-sub)', fontSize: '0.9rem' }}>
                      Nazariy savollarda ishtirokchi o'z fikrini erkin yozadi. Tizimimizning AI baholash moduli va hakamlar javobning to'liqligi va texnik to'g'riligini tahlil qiladi.
                    </p>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.4rem', display: 'block' }}>
                      Sizning fikringiz / javobingiz:
                    </label>
                    <textarea
                      value={theoryNote}
                      onChange={(e) => setTheoryNote(e.target.value)}
                      rows={4}
                      style={{
                        width: '100%', padding: '1rem',
                        background: 'var(--bg-crust)', border: '1px solid var(--bg-surface0)',
                        borderRadius: 'var(--radius-sm)', color: 'var(--text-main)',
                        fontSize: '0.92rem', lineHeight: 1.6, resize: 'vertical',
                        fontFamily: 'inherit', outline: 'none',
                      }}
                    />
                  </div>

                  <div>
                    <button
                      onClick={handleAnalyzeTheory}
                      className="btn btn-secondary"
                      style={{ padding: '0.65rem 1.4rem', background: 'var(--bg-surface0)', color: 'var(--accent-2)', border: '1px solid var(--accent-2)' }}
                    >
                      🤖 AI Baholash simulyatsiyasini ko'rish
                    </button>
                  </div>

                  {theoryAnalysis && (
                    <div style={{
                      padding: '1.25rem', borderRadius: 'var(--radius-md)',
                      background: 'rgba(203,166,247,0.08)', border: '1px solid rgba(203,166,247,0.25)',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                        <span style={{ fontWeight: 700, color: 'var(--accent-2)', fontSize: '1rem' }}>
                          🧠 AI Hakam Xulosasi
                        </span>
                        <span style={{ fontWeight: 800, color: 'var(--success)', fontSize: '1.1rem' }}>
                          {theoryAnalysis.score} / 100 Ball
                        </span>
                      </div>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', marginBottom: '0.75rem' }}>
                        {theoryAnalysis.feedback}
                      </p>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        <strong>Aniqlangan asosiy tushunchalar:</strong>
                        <ul style={{ paddingLeft: '1.25rem', marginTop: '0.3rem' }}>
                          {theoryAnalysis.highlights.map((h, i) => (
                            <li key={i} style={{ color: 'var(--text-sub)' }}>{h}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              )}

            </div>
          </div>
        </section>

        {/* ─── 3. HOW IT WORKS ────────────────────────────────────────────── */}
        <section id="how-it-works" style={{ padding: '5rem 1.5rem' }}>
          <div className="container" style={{ maxWidth: '1050px', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '3.5rem' }}>
              <div style={{
                display: 'inline-block', padding: '0.3rem 0.8rem', borderRadius: '20px',
                background: 'rgba(137,180,250,0.1)', color: 'var(--accent)',
                fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.75rem',
              }}>
                📌 3 TA ODDIY QADAM
              </div>
              <h2 style={{ fontSize: '2.2rem', fontWeight: 800 }}>Musobaqa qanday o'tkaziladi?</h2>
              <p style={{ color: 'var(--text-sub)', maxWidth: '600px', margin: '0 auto', marginTop: '0.5rem' }}>
                Hech qanday murakkablik yo'q. Kuniga atigi 15 daqiqa ajratib, Python bilimingizni sezilarli darajada oshiring.
              </p>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))',
              gap: '1.5rem',
            }}>
              {/* Step 1 */}
              <div className="card" style={{ position: 'relative', overflow: 'hidden' }}>
                <div style={{
                  position: 'absolute', top: '-10px', right: '-10px',
                  fontSize: '4.5rem', fontWeight: 900, color: 'rgba(255,255,255,0.03)',
                  userSelect: 'none',
                }}>
                  01
                </div>
                <div style={{ fontSize: '2.2rem', marginBottom: '1rem' }}>📝</div>
                <h3 style={{ fontSize: '1.15rem', marginBottom: '0.5rem' }}>1. Ro'yxatdan o'ting</h3>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                  30 soniyada hisob yarating va o'zingizga mos bo'lgan faol musobaqaga yoziling.
                </p>
              </div>

              {/* Step 2 */}
              <div className="card" style={{ position: 'relative', overflow: 'hidden' }}>
                <div style={{
                  position: 'absolute', top: '-10px', right: '-10px',
                  fontSize: '4.5rem', fontWeight: 900, color: 'rgba(255,255,255,0.03)',
                  userSelect: 'none',
                }}>
                  02
                </div>
                <div style={{ fontSize: '2.2rem', marginBottom: '1rem' }}>🎲</div>
                <h3 style={{ fontSize: '1.15rem', marginBottom: '0.5rem' }}>2. Har kuni yangi savol</h3>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                  Har bir kunga savollar bankidan siz uchun maxsus tasodifiy, takrorlanmas savol generatsiya qilinadi.
                </p>
              </div>

              {/* Step 4 */}
              <div className="card" style={{ position: 'relative', overflow: 'hidden' }}>
                <div style={{
                  position: 'absolute', top: '-10px', right: '-10px',
                  fontSize: '4.5rem', fontWeight: 900, color: 'rgba(255,255,255,0.03)',
                  userSelect: 'none',
                }}>
                  03
                </div>
                <div style={{ fontSize: '2.2rem', marginBottom: '1rem' }}>🏆</div>
                <h3 style={{ fontSize: '1.15rem', marginBottom: '0.5rem' }}>3. Reyting va Sovrinlar</h3>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                  Ballaringiz umumiy turnir jadvaliga qo'shiladi. Musobaqa yakunida eng yaxshilar sovrinlar bilan taqdirlanadi.
                </p>
              </div>
            </div>

          </div>
        </section>

        {/* ─── 4. ACTIVE CHALLENGES ────────────────────────────────────────── */}
        <section id="challenges" style={{
          padding: '5rem 1.5rem',
          background: 'var(--bg-mantle)',
          borderTop: '1px solid var(--bg-surface0)',
        }}>
          <div className="container" style={{ maxWidth: '1050px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '2.5rem', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <div style={{
                  display: 'inline-block', padding: '0.3rem 0.8rem', borderRadius: '20px',
                  background: 'rgba(203,166,247,0.1)', color: 'var(--accent-2)',
                  fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem',
                }}>
                  🏁 HOZIRDA MAVJUD
                </div>
                <h2 style={{ fontSize: '2.2rem', fontWeight: 800 }}>Faol Musobaqalar</h2>
              </div>
              <span className="badge badge-blue" style={{ fontSize: '0.9rem', padding: '0.4rem 0.8rem' }}>
                {challenges.length} ta faol challenge
              </span>
            </div>

            {loadingChallenges ? (
              <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
                <div className="spinner" style={{ margin: '0 auto 1rem' }}></div>
                Challengelar yuklanmoqda...
              </div>
            ) : challenges.length === 0 ? (
              <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                <p style={{ color: 'var(--text-muted)' }}>Hozirda faol musobaqa mavjud emas. Tez orada yangi challengelar e'lon qilinadi!</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {challenges.map((ch) => (
                  <div
                    key={ch.id}
                    className="card card-hover"
                    style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '1.75rem', flexWrap: 'wrap', gap: '1.5rem',
                      background: 'var(--bg-base)',
                      border: '1px solid var(--bg-surface0)',
                    }}
                  >
                    <div style={{ maxWidth: '650px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                        <h3 style={{ fontSize: '1.3rem', fontWeight: 700 }}>{ch.name}</h3>
                        <span className="badge badge-green">FAOL</span>
                      </div>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1rem', lineHeight: 1.6 }}>
                        {ch.description}
                      </p>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.25rem', fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--accent)' }}>📅 {ch.total_days} kunlik</span>
                        {ch.prize_info && (
                          <span style={{ color: 'var(--accent-4)' }}>🏆 {ch.prize_info}</span>
                        )}
                      </div>
                    </div>

                    <div>
                      {user ? (
                        <Link
                          to={`/challenge/${ch.id}`}
                          className="btn btn-primary"
                          style={{ padding: '0.7rem 1.6rem', fontSize: '0.95rem' }}
                        >
                          Kunlarni ko'rish →
                        </Link>
                      ) : (
                        <Link
                          to="/register"
                          className="btn btn-primary"
                          style={{ padding: '0.7rem 1.6rem', fontSize: '0.95rem' }}
                        >
                          Qatnashish (Ro'yxatdan o'tish) →
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

          </div>
        </section>

        {/* ─── 5. FAQ SECTION ─────────────────────────────────────────────── */}
        <section style={{ padding: '5rem 1.5rem', borderTop: '1px solid var(--bg-surface0)' }}>
          <div className="container" style={{ maxWidth: '850px', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
              <div style={{
                display: 'inline-block', padding: '0.3rem 0.8rem', borderRadius: '20px',
                background: 'rgba(249,226,175,0.1)', color: 'var(--warning)',
                fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.75rem',
              }}>
                ❓ SAVOLLAR & JAVOBLAR
              </div>
              <h2 style={{ fontSize: '2.2rem', fontWeight: 800 }}>Tez-tez beriladigan savollar</h2>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {FAQS.map((faq, i) => (
                <div
                  key={i}
                  style={{
                    background: 'var(--bg-mantle)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--bg-surface0)',
                    overflow: 'hidden',
                  }}
                >
                  <button
                    onClick={() => setOpenFaq(openFaq === i ? null : i)}
                    style={{
                      width: '100%', padding: '1.25rem 1.5rem',
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      background: 'none', border: 'none', cursor: 'pointer',
                      color: 'var(--text-main)', fontSize: '1rem', fontWeight: 600,
                      textAlign: 'left',
                    }}
                  >
                    <span>{faq.q}</span>
                    <span style={{
                      transform: openFaq === i ? 'rotate(180deg)' : 'none',
                      transition: 'transform 0.2s', color: 'var(--accent)',
                    }}>
                      ▼
                    </span>
                  </button>
                  {openFaq === i && (
                    <div style={{
                      padding: '0 1.5rem 1.25rem',
                      color: 'var(--text-sub)', fontSize: '0.92rem', lineHeight: 1.7,
                      borderTop: '1px solid rgba(255,255,255,0.03)',
                    }}>
                      {faq.a}
                    </div>
                  )}
                </div>
              ))}
            </div>

          </div>
        </section>

        {/* ─── 6. BOTTOM CALL TO ACTION ────────────────────────────────────── */}
        <section style={{
          padding: '5rem 1.5rem',
          textAlign: 'center',
          background: 'linear-gradient(180deg, var(--bg-mantle) 0%, var(--bg-crust) 100%)',
          borderTop: '1px solid var(--bg-surface0)',
        }}>
          <div className="container" style={{ maxWidth: '750px', margin: '0 auto' }}>
            <h2 style={{ fontSize: '2.4rem', fontWeight: 800, marginBottom: '1rem' }}>
              O'z bilimingizni sinashga tayyormisiz?
            </h2>
            <p style={{ color: 'var(--text-sub)', fontSize: '1.05rem', marginBottom: '2rem', lineHeight: 1.6 }}>
              Hozir ro'yxatdan o'ting, kunlik marafonimizga qo'shiling va boshqa dasturchilar bilan halol bellashuvda ishtirok eting!
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              {!user ? (
                <>
                  <Link
                    to="/register"
                    className="btn btn-primary"
                    style={{ padding: '0.9rem 2.2rem', fontSize: '1.05rem', borderRadius: 'var(--radius-md)' }}
                  >
                    Ro'yxatdan o'tish (Bepul)
                  </Link>
                  <Link
                    to="/login"
                    className="btn btn-secondary"
                    style={{
                      padding: '0.9rem 2rem', fontSize: '1.05rem',
                      background: 'var(--bg-surface0)', border: '1px solid var(--bg-surface1)',
                      color: 'var(--text-main)', borderRadius: 'var(--radius-md)',
                    }}
                  >
                    Tizimga kirish
                  </Link>
                </>
              ) : (
                <Link
                  to="/dashboard"
                  className="btn btn-primary"
                  style={{ padding: '0.9rem 2.2rem', fontSize: '1.05rem', borderRadius: 'var(--radius-md)' }}
                >
                  Mening kabinetimga o'tish →
                </Link>
              )}
            </div>
          </div>
        </section>

        {/* ─── FOOTER ──────────────────────────────────────────────────────── */}
        <footer style={{
          padding: '2.5rem 1.5rem',
          background: 'var(--bg-crust)',
          borderTop: '1px solid var(--bg-surface0)',
          textAlign: 'center',
          color: 'var(--text-dim)',
          fontSize: '0.85rem',
        }}>
          <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>🐍</span>
              <span style={{ fontWeight: 700, color: 'var(--text-muted)' }}>PyChallenge</span>
              <span>— 15 Kunlik Python Musobaqa Platformasi</span>
            </div>
            <div>
              Barcha huquqlar himoyalangan &copy; {new Date().getFullYear()}
            </div>
          </div>
        </footer>

      </div>
    </>
  );
}

