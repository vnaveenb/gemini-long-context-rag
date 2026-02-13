"""Pydantic response/request models for the API — provides typed contracts + OpenAPI docs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.models.dqc import DQCEvaluationResult, DQCStatus, RiskLevel
from src.models.report import (
    AuditInfo,
    ComplianceReport,
    ComplianceSummary,
    DocumentInfo,
    Recommendation,
    RiskDistribution,
)


# ── Health ───────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    environment: str


# ── Documents ────────────────────────────────────────────────────────────────


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    path: str
    size_bytes: int


class DocumentEntry(BaseModel):
    doc_id: str
    filename: str
    size_bytes: int
    path: str
    uploaded_at: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentEntry]


# ── Analysis ─────────────────────────────────────────────────────────────────


class AnalysisStartRequest(BaseModel):
    file_path: str
    dqc_path: str | None = None
    user: str = "api_user"


class AnalysisStartResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    stage: str
    progress: float
    errors: list[str] = Field(default_factory=list)
    report_id: str | None = None
    filename: str = ""
    stage_times: dict[str, float] = Field(default_factory=dict)


# ── Reports ──────────────────────────────────────────────────────────────────


class ReportListEntry(BaseModel):
    report_id: str
    filename: str
    generated_at: str | None = None
    score: float | None = None


class ReportListResponse(BaseModel):
    reports: list[ReportListEntry]


class ReportDetailResponse(BaseModel):
    """Full compliance report data for in-app display."""

    report_id: str
    generated_at: str
    document: DocumentInfo
    dqc_version: str
    overall_compliance: ComplianceSummary
    executive_summary: str
    findings: list[DQCEvaluationResult]
    recommendations: list[Recommendation]
    audit: AuditInfo


# ── Audit ────────────────────────────────────────────────────────────────────


class AuditRecord(BaseModel):
    audit_id: str
    evaluation_id: str
    doc_id: str
    filename: str | None = None
    dqc_version: str | None = None
    model_version: str | None = None
    embedding_model: str | None = None
    prompt_version: str | None = None
    total_tokens: int | None = None
    score: float | None = None
    passed: int | None = None
    failed: int | None = None
    partial: int | None = None
    processing_time: float | None = None
    user_id: str | None = None
    timestamp: str | None = None


class AuditListResponse(BaseModel):
    records: list[AuditRecord]


# ── WebSocket ────────────────────────────────────────────────────────────────


class WSProgressMessage(BaseModel):
    """Message pushed over WebSocket on each pipeline progress update."""

    type: str = "progress"
    job_id: str
    stage: str
    progress: float
    errors: list[str] = Field(default_factory=list)
    report_id: str | None = None
    filename: str = ""
