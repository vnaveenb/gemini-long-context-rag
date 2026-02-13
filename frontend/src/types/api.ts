/* ── API type definitions — mirrors src/api/schemas.py ─────────────────────── */

// ── Health ──────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
}

// ── Documents ───────────────────────────────────────────────────────────────

export interface UploadResponse {
  doc_id: string;
  filename: string;
  path: string;
  size_bytes: number;
}

export interface DocumentEntry {
  doc_id: string;
  filename: string;
  size_bytes: number;
  path: string;
  uploaded_at: string;
}

export interface DocumentListResponse {
  documents: DocumentEntry[];
}

// ── Analysis ────────────────────────────────────────────────────────────────

export interface AnalysisStartRequest {
  file_path: string;
  dqc_path?: string | null;
  user?: string;
}

export interface AnalysisStartResponse {
  job_id: string;
  status: string;
}

export type PipelineStage =
  | "pending"
  | "ingestion"
  | "preprocessing"
  | "embedding"
  | "evaluation"
  | "aggregation"
  | "reporting"
  | "completed"
  | "failed";

export interface JobStatusResponse {
  job_id: string;
  stage: PipelineStage;
  progress: number;
  errors: string[];
  report_id: string | null;
  filename: string;
  stage_times: Record<string, number>;
}

// ── Reports ─────────────────────────────────────────────────────────────────

export interface RiskDistribution {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface ComplianceSummary {
  score: number;
  total_items: number;
  passed: number;
  failed: number;
  partial: number;
  risk_distribution: RiskDistribution;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  pages: number;
  version: number;
}

export interface DQCEvaluationResult {
  dqc_item_id: string;
  status: "Pass" | "Fail" | "Partial";
  justification: string;
  evidence_quotes: string[];
  risk_level: "Critical" | "High" | "Medium" | "Low";
  recommendation: string | null;
  confidence_score: number;
  sections_reviewed: string[];
}

export interface Recommendation {
  priority: number;
  dqc_item_id: string;
  action: string;
  risk_impact: "Critical" | "High" | "Medium" | "Low";
}

export interface AuditInfo {
  model_version: string;
  embedding_model: string;
  prompt_version: string;
  dqc_version: string;
  total_tokens_used: number;
  processing_time_seconds: number;
  user: string;
}

export interface ReportListEntry {
  report_id: string;
  filename: string;
  generated_at: string | null;
  score: number | null;
}

export interface ReportListResponse {
  reports: ReportListEntry[];
}

export interface ReportDetail {
  report_id: string;
  generated_at: string;
  document: DocumentInfo;
  dqc_version: string;
  overall_compliance: ComplianceSummary;
  executive_summary: string;
  findings: DQCEvaluationResult[];
  recommendations: Recommendation[];
  audit: AuditInfo;
}

// ── Audit ───────────────────────────────────────────────────────────────────

export interface AuditRecord {
  audit_id: string;
  evaluation_id: string;
  doc_id: string;
  filename: string | null;
  dqc_version: string | null;
  model_version: string | null;
  embedding_model: string | null;
  prompt_version: string | null;
  total_tokens: number | null;
  score: number | null;
  passed: number | null;
  failed: number | null;
  partial: number | null;
  processing_time: number | null;
  user_id: string | null;
  timestamp: string | null;
}

export interface AuditListResponse {
  records: AuditRecord[];
}

// ── WebSocket ───────────────────────────────────────────────────────────────

export interface WSProgressMessage {
  type: "progress" | "heartbeat" | "error";
  job_id?: string;
  stage?: PipelineStage;
  progress?: number;
  errors?: string[];
  report_id?: string | null;
  filename?: string;
  message?: string;
}
