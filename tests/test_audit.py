"""Tests for the audit logger (SQLite-backed)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.audit.audit_logger import AuditLogger
from src.models.dqc import DQCEvaluationResult, DQCStatus, RiskLevel
from src.models.report import (
    AuditInfo,
    ComplianceReport,
    ComplianceSummary,
    DocumentInfo,
    RiskDistribution,
)


@pytest.fixture
def audit_logger(tmp_path) -> AuditLogger:
    db_path = tmp_path / "audit" / "test_audit.db"
    return AuditLogger(db_path)


@pytest.fixture
def sample_report() -> ComplianceReport:
    return ComplianceReport(
        document=DocumentInfo(id="doc-123", filename="test.pdf", pages=10),
        dqc_version="1.0",
        overall_compliance=ComplianceSummary(
            score=80.0,
            total_items=5,
            passed=4,
            failed=1,
            partial=0,
            risk_distribution=RiskDistribution(critical=0, high=1, medium=0, low=4),
        ),
        executive_summary="Overall good compliance with one high-risk finding.",
        findings=[
            DQCEvaluationResult(
                dqc_item_id="DQC-001",
                status=DQCStatus.PASS,
                justification="Met criteria",
                risk_level=RiskLevel.LOW,
                confidence_score=0.9,
            ),
        ],
        audit=AuditInfo(
            model_version="gemini-2.5-flash",
            embedding_model="gemini-embedding-001",
            prompt_version="v1.0",
            dqc_version="1.0",
            total_tokens_used=5000,
            processing_time_seconds=12.5,
        ),
    )


class TestAuditLogger:
    def test_init_creates_db(self, tmp_path):
        db_path = tmp_path / "new_audit.db"
        AuditLogger(db_path)
        assert db_path.exists()

    def test_init_creates_parent_dirs(self, tmp_path):
        db_path = tmp_path / "nested" / "deep" / "audit.db"
        AuditLogger(db_path)
        assert db_path.exists()

    def test_log_evaluation(self, audit_logger: AuditLogger, sample_report: ComplianceReport):
        audit_logger.log_evaluation(sample_report, doc_id="doc-123", user="tester")
        records = audit_logger.query_by_doc("doc-123")
        assert len(records) == 1

        record = records[0]
        assert record["doc_id"] == "doc-123"
        assert record["filename"] == "test.pdf"
        assert record["score"] == 80.0
        assert record["user_id"] == "tester"
        assert record["model_version"] == "gemini-2.5-flash"

    def test_query_recent(self, audit_logger: AuditLogger, sample_report: ComplianceReport):
        for i in range(5):
            report = sample_report.model_copy(update={"report_id": f"report-{i}"})
            audit_logger.log_evaluation(report, doc_id=f"doc-{i}", user="user")

        recent = audit_logger.query_recent(limit=3)
        assert len(recent) == 3

    def test_query_by_user(self, audit_logger: AuditLogger, sample_report: ComplianceReport):
        audit_logger.log_evaluation(sample_report, doc_id="d1", user="alice")
        audit_logger.log_evaluation(sample_report, doc_id="d2", user="bob")
        audit_logger.log_evaluation(sample_report, doc_id="d3", user="alice")

        alice_records = audit_logger.query_by_user("alice")
        assert len(alice_records) == 2

        bob_records = audit_logger.query_by_user("bob")
        assert len(bob_records) == 1

    def test_empty_query(self, audit_logger: AuditLogger):
        records = audit_logger.query_by_doc("nonexistent")
        assert records == []

    def test_result_json_roundtrip(self, audit_logger: AuditLogger, sample_report: ComplianceReport):
        audit_logger.log_evaluation(sample_report, doc_id="doc-rt", user="test")
        records = audit_logger.query_by_doc("doc-rt")
        assert len(records) == 1

        result_json = records[0]["result_json"]
        parsed = json.loads(result_json)
        assert parsed["document"]["filename"] == "test.pdf"
        assert parsed["overall_compliance"]["score"] == 80.0
