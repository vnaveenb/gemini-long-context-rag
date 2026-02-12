"""Pydantic models for the Data Quality Checklist (DQC)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DQCStatus(str, Enum):
    PASS = "Pass"
    FAIL = "Fail"
    PARTIAL = "Partial"


class RiskLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class DQCItem(BaseModel):
    """A single DQC checklist item (input)."""

    item_id: str
    category: str
    requirement: str
    criteria: str
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class DQCChecklist(BaseModel):
    """A versioned DQC checklist."""

    version: str
    name: str = "Default DQC"
    description: str = ""
    items: list[DQCItem] = Field(default_factory=list)


class DQCEvaluationResult(BaseModel):
    """Evaluation result for a single DQC item (output from LLM)."""

    dqc_item_id: str
    status: DQCStatus
    justification: str
    evidence_quotes: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
    recommendation: str | None = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    sections_reviewed: list[str] = Field(default_factory=list)
