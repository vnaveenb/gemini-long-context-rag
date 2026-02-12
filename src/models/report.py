"""Pydantic models for compliance reports."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.models.dqc import DQCEvaluationResult, RiskLevel


class RiskDistribution(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class ComplianceSummary(BaseModel):
    score: float = 0.0
    total_items: int = 0
    passed: int = 0
    failed: int = 0
    partial: int = 0
    risk_distribution: RiskDistribution = Field(default_factory=RiskDistribution)


class DocumentInfo(BaseModel):
    id: str
    filename: str
    pages: int = 0
    version: int = 1


class Recommendation(BaseModel):
    priority: int
    dqc_item_id: str
    action: str
    risk_impact: RiskLevel


class AuditInfo(BaseModel):
    model_version: str = ""
    embedding_model: str = ""
    prompt_version: str = ""
    dqc_version: str = ""
    total_tokens_used: int = 0
    processing_time_seconds: float = 0.0
    user: str = ""


class ComplianceReport(BaseModel):
    """Full structured compliance report."""

    report_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    document: DocumentInfo
    dqc_version: str
    overall_compliance: ComplianceSummary = Field(default_factory=ComplianceSummary)
    executive_summary: str = ""
    findings: list[DQCEvaluationResult] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    audit: AuditInfo = Field(default_factory=AuditInfo)
