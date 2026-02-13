/* ── Typed API client — all calls to the FastAPI backend ──────────────────── */

import type {
  AnalysisStartRequest,
  AnalysisStartResponse,
  AuditListResponse,
  DocumentListResponse,
  HealthResponse,
  ReportDetail,
  ReportListResponse,
  UploadResponse,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Construct the WebSocket URL from the HTTP base. */
export function wsUrl(path: string): string {
  const base = API_URL.replace(/^http/, "ws");
  return `${base}${path}`;
}

/** Construct the full HTTP URL for a given API path. */
export function apiUrl(path: string): string {
  return `${API_URL}${path}`;
}

// ── BYOK helper ──────────────────────────────────────────────────────────────

/** Read the BYOK Gemini key from localStorage (if set + not expired). */
function getByokHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const key = localStorage.getItem("lra_gemini_api_key");
  const expiry = localStorage.getItem("lra_gemini_api_key_expiry");
  if (key && expiry && Number(expiry) > Date.now()) {
    return { "X-Gemini-API-Key": key };
  }
  return {};
}

// ── Generic helpers ─────────────────────────────────────────────────────────

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_URL}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString(), {
    headers: { ...getByokHeaders() },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const baseHeaders: Record<string, string> = {
    ...getByokHeaders(),
  };
  if (!(body instanceof FormData)) {
    baseHeaders["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: baseHeaders,
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Health ──────────────────────────────────────────────────────────────────

export const getHealth = () => get<HealthResponse>("/health");

// ── Documents ───────────────────────────────────────────────────────────────

export const listDocuments = () => get<DocumentListResponse>("/api/v1/documents");

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return post<UploadResponse>("/api/v1/documents/upload", form);
}

// ── Analysis ────────────────────────────────────────────────────────────────

export const startAnalysis = (req: AnalysisStartRequest) =>
  post<AnalysisStartResponse>("/api/v1/analysis/start", req);

export const getJobStatus = (jobId: string) =>
  get<import("@/types/api").JobStatusResponse>(`/api/v1/analysis/${jobId}/status`);

// ── Reports ─────────────────────────────────────────────────────────────────

export const listReports = () => get<ReportListResponse>("/api/v1/reports");

export const getReportDetail = (reportId: string) =>
  get<ReportDetail>(`/api/v1/reports/${reportId}`);

export const reportJsonUrl = (reportId: string) =>
  `${API_URL}/api/v1/reports/${reportId}/json`;

export const reportPdfUrl = (reportId: string) =>
  `${API_URL}/api/v1/reports/${reportId}/pdf`;

// ── Audit ───────────────────────────────────────────────────────────────────

export const getRecentAudit = (limit = 20) =>
  get<AuditListResponse>("/api/v1/audit/recent", { limit: String(limit) });

export const getAuditByDocument = (docId: string) =>
  get<AuditListResponse>(`/api/v1/audit/document/${docId}`);

export const getAuditByUser = (userId: string) =>
  get<AuditListResponse>(`/api/v1/audit/user/${userId}`);
