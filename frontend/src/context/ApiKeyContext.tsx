"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

/* ── Constants ────────────────────────────────────────────────────────────── */

const STORAGE_KEY = "lra_gemini_api_key";
const EXPIRY_KEY = "lra_gemini_api_key_expiry";
const TTL_MS = 60 * 60 * 1000; // 1 hour

/* ── Context shape ────────────────────────────────────────────────────────── */

interface ApiKeyCtx {
  /** The current API key (empty string = use server default). */
  apiKey: string;
  /** Whether a BYOK key is active and not expired. */
  hasKey: boolean;
  /** Minutes remaining before expiry (0 when no key). */
  minutesLeft: number;
  /** Set a new key (resets the 1-hour timer). */
  setApiKey: (key: string) => void;
  /** Clear the stored key immediately. */
  clearApiKey: () => void;
}

const ApiKeyContext = createContext<ApiKeyCtx>({
  apiKey: "",
  hasKey: false,
  minutesLeft: 0,
  setApiKey: () => {},
  clearApiKey: () => {},
});

/* ── Provider ─────────────────────────────────────────────────────────────── */

export function ApiKeyProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKeyState] = useState("");
  const [minutesLeft, setMinutesLeft] = useState(0);

  /* Hydrate from localStorage on mount */
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    const expiry = localStorage.getItem(EXPIRY_KEY);
    if (stored && expiry) {
      const remaining = Number(expiry) - Date.now();
      if (remaining > 0) {
        setApiKeyState(stored);
        setMinutesLeft(Math.ceil(remaining / 60_000));
      } else {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(EXPIRY_KEY);
      }
    }
  }, []);

  /* Countdown timer — update every 30s */
  useEffect(() => {
    if (!apiKey) return;
    const id = setInterval(() => {
      const expiry = Number(localStorage.getItem(EXPIRY_KEY) ?? "0");
      const remaining = expiry - Date.now();
      if (remaining <= 0) {
        setApiKeyState("");
        setMinutesLeft(0);
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(EXPIRY_KEY);
      } else {
        setMinutesLeft(Math.ceil(remaining / 60_000));
      }
    }, 30_000);
    return () => clearInterval(id);
  }, [apiKey]);

  const setApiKey = useCallback((key: string) => {
    const trimmed = key.trim();
    if (!trimmed) return;
    localStorage.setItem(STORAGE_KEY, trimmed);
    localStorage.setItem(EXPIRY_KEY, String(Date.now() + TTL_MS));
    setApiKeyState(trimmed);
    setMinutesLeft(60);
  }, []);

  const clearApiKey = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(EXPIRY_KEY);
    setApiKeyState("");
    setMinutesLeft(0);
  }, []);

  return (
    <ApiKeyContext.Provider
      value={{
        apiKey,
        hasKey: apiKey.length > 0,
        minutesLeft,
        setApiKey,
        clearApiKey,
      }}
    >
      {children}
    </ApiKeyContext.Provider>
  );
}

export const useApiKey = () => useContext(ApiKeyContext);
