import { useEffect, useState, useRef, useCallback } from 'react';

/**
 * Timer hook — serverdan kelgan expires_at asosida countdown
 * Vaqt tugaganda onExpire callback chaqiriladi
 */
export function useTimer({ expiresAt, onExpire }) {
  const [secondsLeft, setSecondsLeft] = useState(null);
  const [status, setStatus] = useState('normal'); // normal | warning | danger | expired
  const expiredCalled = useRef(false);
  const intervalRef = useRef(null);

  const compute = useCallback(() => {
    if (!expiresAt) return;
    const diff = Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000);

    if (diff <= 0) {
      setSecondsLeft(0);
      setStatus('expired');
      if (!expiredCalled.current) {
        expiredCalled.current = true;
        onExpire?.();
      }
      clearInterval(intervalRef.current);
      return;
    }

    setSecondsLeft(diff);
    if (diff <= 60)       setStatus('danger');
    else if (diff <= 300) setStatus('warning');
    else                  setStatus('normal');
  }, [expiresAt, onExpire]);

  useEffect(() => {
    compute();
    intervalRef.current = setInterval(compute, 1000);
    return () => clearInterval(intervalRef.current);
  }, [compute]);

  const format = (secs) => {
    if (secs === null) return '--:--';
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  };

  return {
    secondsLeft,
    formatted: format(secondsLeft),
    status, // normal | warning | danger | expired
    isExpired: status === 'expired',
  };
}
