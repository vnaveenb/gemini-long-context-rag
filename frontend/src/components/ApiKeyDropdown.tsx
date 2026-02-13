"use client";

import { useState } from "react";
import { useApiKey } from "@/context/ApiKeyContext";

/**
 * Dropdown panel for entering / managing a Bring-Your-Own-Key Gemini API key.
 * Renders as a collapsible section at the bottom of the Sidebar.
 */
export function ApiKeyDropdown() {
  const { apiKey, hasKey, minutesLeft, setApiKey, clearApiKey } = useApiKey();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [showKey, setShowKey] = useState(false);

  const maskedKey = apiKey
    ? `${apiKey.slice(0, 6)}..${apiKey.slice(-4)}`
    : "";

  return (
    <div className="px-3 pb-4">
      {/* Toggle button */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-sm font-medium
                   text-[var(--sidebar-fg)] hover:bg-white/10 transition-colors"
      >
        <span className="flex items-center gap-2">
          <span className="text-lg">🔑</span>
          API Key
        </span>
        <span
          className={`w-2 h-2 rounded-full ${
            hasKey ? "bg-green-400" : "bg-gray-500"
          }`}
        />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="mt-1 rounded-lg bg-white/5 border border-white/10 p-3 space-y-3">
          {hasKey ? (
            <>
              <div className="text-xs text-[var(--muted)] space-y-1">
                <p>
                  Active:{" "}
                  <code className="text-green-400">
                    {showKey ? apiKey : maskedKey}
                  </code>
                  <button
                    onClick={() => setShowKey(!showKey)}
                    className="ml-2 underline text-[var(--accent)] hover:text-white"
                  >
                    {showKey ? "hide" : "show"}
                  </button>
                </p>
                <p>
                  Expires in <strong className="text-white">{minutesLeft}m</strong>
                </p>
              </div>
              <button
                onClick={() => {
                  clearApiKey();
                  setDraft("");
                }}
                className="w-full py-1.5 rounded-md text-xs font-medium bg-red-500/20 text-red-300
                           hover:bg-red-500/30 transition-colors"
              >
                Remove Key
              </button>
            </>
          ) : (
            <>
              <p className="text-xs text-[var(--muted)]">
                Bring your own Gemini API key. Stored in your browser only — expires after 1 hour.
              </p>
              <input
                type="password"
                placeholder="AIzaSy..."
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                className="w-full rounded-md border border-white/20 bg-white/5 px-2.5 py-1.5
                           text-sm text-white placeholder:text-gray-500
                           focus:border-[var(--accent)] focus:outline-none"
              />
              <button
                disabled={!draft.trim()}
                onClick={() => {
                  setApiKey(draft);
                  setDraft("");
                }}
                className="w-full py-1.5 rounded-md text-xs font-medium bg-[var(--accent)] text-white
                           hover:opacity-90 transition-opacity disabled:opacity-30"
              >
                Save Key (1 hr session)
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
