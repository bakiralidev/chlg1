import { useEffect, useRef } from 'react';
import { api } from '../api/client';

/**
 * Autosave hook — kodni 30 soniyada bir backendga saqlaydi
 */
export function useAutosave({ sessionId, codeRef, enabled = true }) {
  const lastSaved = useRef('');
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!enabled || !sessionId) return;

    const save = async () => {
      const currentCode = codeRef.current;
      if (!currentCode || currentCode === lastSaved.current) return;

      try {
        await api.autosave(sessionId, currentCode);
        lastSaved.current = currentCode;
        console.log('[Autosave] Saqlandi:', new Date().toLocaleTimeString());
      } catch (e) {
        console.warn('[Autosave] Xato:', e.message);
      }
    };

    intervalRef.current = setInterval(save, 30000);

    return () => {
      clearInterval(intervalRef.current);
      // Chiqishda ham saqlash
      save();
    };
  }, [sessionId, enabled, codeRef]);
}
