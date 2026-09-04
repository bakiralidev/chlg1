import { useEffect, useState } from 'react';

export default function CountdownTimer({ targetDate, label = 'Boshlanishiga' }) {
  const [timeLeft, setTimeLeft] = useState(null);
  const [expired, setExpired] = useState(false);

  useEffect(() => {
    const compute = () => {
      const diff = new Date(targetDate).getTime() - Date.now();
      if (diff <= 0) {
        setExpired(true);
        setTimeLeft(null);
        return;
      }
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setTimeLeft({ d, h, m, s });
    };

    compute();
    const interval = setInterval(compute, 1000);
    return () => clearInterval(interval);
  }, [targetDate]);

  if (expired) return null;
  if (!timeLeft) return null;

  return (
    <div style={{
      display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem',
    }}>
      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        {label}
      </span>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        {[
          { v: timeLeft.d, l: 'kun' },
          { v: timeLeft.h, l: 'soat' },
          { v: timeLeft.m, l: 'min' },
          { v: timeLeft.s, l: 'son' },
        ].map(({ v, l }) => (
          <div key={l} style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            background: 'var(--bg-surface0)',
            borderRadius: 'var(--radius-sm)',
            padding: '0.4rem 0.6rem',
            minWidth: '44px',
          }}>
            <span style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 700, fontSize: '1.1rem', color: 'var(--accent)',
            }}>
              {String(v).padStart(2, '0')}
            </span>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>{l}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
