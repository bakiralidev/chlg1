import { useEffect, useRef } from "react";
import { api } from "../api/client";

export function useAutosave({ sessionId, codeRef, noteRef, enabled = true }) {
  const lastSaved = useRef({ code: "", note: "" });
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!enabled || !sessionId) return;

    const save = async () => {
      const currentCode = codeRef?.current || null;
      const currentNote = noteRef?.current || null;
      const codeChanged = currentCode !== null && currentCode !== lastSaved.current.code;
      const noteChanged = currentNote !== null && currentNote !== lastSaved.current.note;
      if (!codeChanged && !noteChanged) return;

      try {
        const payload = {};
        if (codeChanged && currentCode) payload.code = currentCode;
        if (noteChanged && currentNote) payload.note_content = currentNote;
        await api.autosave(sessionId, payload);
        if (codeChanged) lastSaved.current.code = currentCode;
        if (noteChanged) lastSaved.current.note = currentNote;
        console.log("[Autosave] Saqlandi:", new Date().toLocaleTimeString());
      } catch (e) {
        console.warn("[Autosave] Xato:", e.message);
      }
    };

    intervalRef.current = setInterval(save, 30000);
    return () => {
      clearInterval(intervalRef.current);
      save();
    };
  }, [sessionId, enabled, codeRef, noteRef]);
}