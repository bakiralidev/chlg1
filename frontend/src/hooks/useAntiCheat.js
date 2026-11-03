import { useEffect, useRef, useCallback } from 'react';
import { api } from '../api/client';

/**
 * Anti-cheat hook:
 * - Fullscreen chiqish → violation
 * - Tab almashtirish (visibilitychange) → violation
 * - Ctrl+V bloklash
 * - Keystroke tezligi (>650 belgi/min) → violation
 * - Multi-monitor aniqlash
 * - F12 (DevTools) bloklash
 */
export function useAntiCheat({ sessionId, onViolation, enabled = true }) {
  const keystrokeTimestamps = useRef([]);
  const lastKeystrokeCheck = useRef(Date.now());

  const reportViolation = useCallback(async (type) => {
    if (!sessionId || !enabled) return;
    try {
      const { data } = await api.reportViolation(sessionId, type);
      onViolation?.(data);
    } catch (e) {
      console.error('Violation report xatosi:', e);
    }
  }, [sessionId, enabled, onViolation]);

  useEffect(() => {
    if (!enabled || !sessionId) return;

    // 1. Fullscreen request
    const requestFullscreen = () => {
      const el = document.documentElement;
      if (el.requestFullscreen) el.requestFullscreen();
      else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
    };
    requestFullscreen();

    // 2. Fullscreen chiqish → violation
    const handleFullscreenChange = () => {
      if (!document.fullscreenElement) {
        reportViolation('fullscreen_exit');
      }
    };

    // 3. Tab almashtirish → violation
    const handleVisibilityChange = () => {
      if (document.hidden) {
        reportViolation('tab_switch');
      }
    };

    // 4. Ctrl+V, Ctrl+C, Ctrl+X bloklash + F12
    const handleKeyDown = (e) => {
      // F12
      if (e.key === 'F12') {
        e.preventDefault();
        return;
      }
      // Ctrl+V (paste)
      if (e.ctrlKey && e.key === 'v') {
        e.preventDefault();
        reportViolation('paste_attempt');
        return;
      }
      // Ctrl+Shift+I, Ctrl+Shift+J (DevTools)
      if (e.ctrlKey && e.shiftKey && ['i', 'I', 'j', 'J'].includes(e.key)) {
        e.preventDefault();
        return;
      }

      // Keystroke tezligi tekshiruvi
      const now = Date.now();
      keystrokeTimestamps.current.push(now);

      // Oxirgi 1 soniyaning keystrokes
      const oneMinAgo = now - 60000;
      keystrokeTimestamps.current = keystrokeTimestamps.current.filter(t => t > oneMinAgo);

      if (keystrokeTimestamps.current.length > 650) {
        reportViolation('high_typing_speed');
        keystrokeTimestamps.current = []; // Reset
      }
    };

    // 5. Multi-monitor aniqlash
    const checkMultiMonitor = () => {
      if (window.screen.width > window.innerWidth * 1.5) {
        reportViolation('multi_monitor');
      }
    };
    const multiMonitorInterval = setInterval(checkMultiMonitor, 30000);

    // 6. Right-click bloklash
    const handleContextMenu = (e) => e.preventDefault();

    // 7. Sahifadan chiqish / tabni yopishdan ogohlantirish
    const handleBeforeUnload = (e) => {
      e.preventDefault();
      e.returnValue = 'Imtihon davom etmoqda! Sahifadan chiqsangiz qoidabuzarlik hisoblanadi.';
      return e.returnValue;
    };

    // Eventlarni ulash
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('contextmenu', handleContextMenu);
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('contextmenu', handleContextMenu);
      window.removeEventListener('beforeunload', handleBeforeUnload);
      clearInterval(multiMonitorInterval);
    };
  }, [sessionId, enabled, reportViolation]);
}
