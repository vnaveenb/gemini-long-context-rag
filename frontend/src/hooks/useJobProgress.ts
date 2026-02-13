"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PipelineStage, WSProgressMessage } from "@/types/api";
import { getJobStatus, wsUrl } from "@/lib/api";

export interface JobProgress {
  stage: PipelineStage;
  progress: number;
  errors: string[];
  reportId: string | null;
  filename: string;
  connected: boolean;
}

const INITIAL: JobProgress = {
  stage: "pending",
  progress: 0,
  errors: [],
  reportId: null,
  filename: "",
  connected: false,
};

const POLL_INTERVAL = 2000;

/**
 * React hook that connects to the WebSocket for real-time pipeline progress.
 * Falls back to HTTP polling if WebSocket fails.
 */
export function useJobProgress(jobId: string | null): JobProgress {
  const [state, setState] = useState<JobProgress>(INITIAL);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const doneRef = useRef(false);

  const cleanup = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!jobId) {
      setState(INITIAL);
      return;
    }

    doneRef.current = false;

    // ── Try WebSocket first ───────────────────────────────────────────────
    const url = wsUrl(`/api/v1/analysis/${jobId}/ws`);
    let ws: WebSocket;

    try {
      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setState((s) => ({ ...s, connected: true }));
      };

      ws.onmessage = (event) => {
        const msg: WSProgressMessage = JSON.parse(event.data);
        if (msg.type === "heartbeat") return;
        if (msg.type === "error") {
          setState((s) => ({
            ...s,
            errors: [...s.errors, msg.message ?? "Unknown error"],
          }));
          return;
        }
        setState({
          stage: msg.stage ?? "pending",
          progress: msg.progress ?? 0,
          errors: msg.errors ?? [],
          reportId: msg.report_id ?? null,
          filename: msg.filename ?? "",
          connected: true,
        });
        if (msg.stage === "completed" || msg.stage === "failed") {
          doneRef.current = true;
        }
      };

      ws.onerror = () => {
        // Fall back to polling
        ws.close();
        startPolling();
      };

      ws.onclose = () => {
        setState((s) => ({ ...s, connected: false }));
        // If not done yet, fall back to polling
        if (!doneRef.current) {
          startPolling();
        }
      };
    } catch {
      startPolling();
    }

    function startPolling() {
      if (pollRef.current || doneRef.current) return;
      pollRef.current = setInterval(async () => {
        try {
          const status = await getJobStatus(jobId!);
          setState({
            stage: status.stage,
            progress: status.progress,
            errors: status.errors,
            reportId: status.report_id,
            filename: status.filename,
            connected: false,
          });
          if (status.stage === "completed" || status.stage === "failed") {
            doneRef.current = true;
            if (pollRef.current) {
              clearInterval(pollRef.current);
              pollRef.current = null;
            }
          }
        } catch {
          // Silently retry on next interval
        }
      }, POLL_INTERVAL);
    }

    return cleanup;
  }, [jobId, cleanup]);

  return state;
}
