"""Tests for Pydantic data models."""

from datetime import datetime

import pytest

from src.models.document import (
    DocumentFormat,
    DocumentMetadata,
    ExtractedContent,
    PageContent,
    Section,
)
from src.models.chunk import Chunk
from src.models.dqc import (
    DQCChecklist,
    DQCEvaluationResult,
    DQCItem,
    DQCStatus,
    RiskLevel,
)
from src.models.report import (
    AuditInfo,
    ComplianceReport,
    ComplianceSummary,
    DocumentInfo,
    Recommendation,
    RiskDistribution,
)


# ────────────────────────────── Document Models ──────────────────────────────


class TestDocumentFormat:
    def test_enum_values(self):
        assert DocumentFormat.PDF == "pdf"
        assert DocumentFormat.DOCX == "docx"
        assert DocumentFormat.PPTX == "pptx"
        assert DocumentFormat.XLSX == "xlsx"

    def test_enum_from_string(self):
        assert DocumentFormat("pdf") == DocumentFormat.PDF


class TestSection:
    def test_defaults(self):
        sec = Section(title="Intro")
        assert sec.title == "Intro"
        assert sec.level == 1
        assert sec.page_start is None
        assert sec.content == ""

    def test_full_section(self):
        sec = Section(title="Ch1", level=2, page_start=3, page_end=5, content="hello")
        assert sec.page_end == 5
        assert sec.content == "hello"


class TestPageContent:
    def test_basic(self):
        p = PageContent(page_number=1, text="some text")
        assert p.page_number == 1
        assert p.metadata == {}


class TestDocumentMetadata:
    def test_defaults(self):
        m = DocumentMetadata()
        assert m.page_count == 0
        assert m.word_count == 0
        assert m.author is None


class TestExtractedContent:
    def test_auto_fields(self):
        ec = ExtractedContent(filename="test.pdf", format=DocumentFormat.PDF)
        assert ec.doc_id  # auto-generated
        assert ec.upload_timestamp
        assert ec.file_hash == ""
        assert ec.version == 1

    def test_is_valid_empty(self):
        ec = ExtractedContent(filename="test.pdf", format=DocumentFormat.PDF, raw_text="")
        assert not ec.is_valid

    def test_is_valid_with_text(self):
        ec = ExtractedContent(filename="test.pdf", format=DocumentFormat.PDF, raw_text="content")
        assert ec.is_valid


# ────────────────────────────── Chunk Models ─────────────────────────────────


class TestChunk:
    def test_auto_chunk_id(self):
        c = Chunk(doc_id="abc", text="hello world")
        assert c.chunk_id  # auto-generated
        assert c.doc_id == "abc"

    def test_to_vectorstore_metadata(self):
        c = Chunk(
            doc_id="d1",
            text="sample",
            section_name="Intro",
            page_number=3,
            chunk_index=0,
            token_count=10,
            metadata={"filename": "test.pdf"},
        )
        meta = c.to_vectorstore_metadata()
        assert meta["doc_id"] == "d1"
        assert meta["section_name"] == "Intro"
        assert meta["page_number"] == 3
        assert meta["chunk_index"] == 0
        assert meta["token_count"] == 10
        assert meta["filename"] == "test.pdf"

    def test_vectorstore_metadata_none_pages(self):
        c = Chunk(doc_id="d1", text="hello")
        meta = c.to_vectorstore_metadata()
        assert meta["page_number"] == 0
        assert meta["page_end"] == 0


# ────────────────────────────── DQC Models ───────────────────────────────────


class TestDQCStatus:
    def test_values(self):
        assert DQCStatus.PASS == "Pass"
        assert DQCStatus.FAIL == "Fail"
        assert DQCStatus.PARTIAL == "Partial"


class TestRiskLevel:
    def test_ordering(self):
        levels = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]
        assert len(levels) == 4


class TestDQCItem:
    def test_basic(self):
        item = DQCItem(
            item_id="DQC-001",
            category="Structure",
            requirement="Has ToC",
            criteria="Document must contain table of contents",
        )
        assert item.weight == 1.0
        assert item.metadata == {}


class TestDQCChecklist:
    def test_with_items(self):
        checklist = DQCChecklist(
            version="1.0",
            name="Test DQC",
            items=[
                DQCItem(item_id="1", category="C", requirement="R", criteria="C"),
                DQCItem(item_id="2", category="C", requirement="R", criteria="C"),
            ],
        )
        assert len(checklist.items) == 2
        assert checklist.version == "1.0"


class TestDQCEvaluationResult:
    def test_full_result(self):
        r = DQCEvaluationResult(
            dqc_item_id="DQC-001",
            status=DQCStatus.PASS,
            justification="All criteria met",
            evidence_quotes=["Found in section 1"],
            risk_level=RiskLevel.LOW,
            confidence_score=0.95,
            sections_reviewed=["Intro", "Chapter 1"],
        )
        assert r.confidence_score == 0.95
        assert len(r.evidence_quotes) == 1

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            DQCEvaluationResult(
                dqc_item_id="x",
                status=DQCStatus.PASS,
                justification="j",
                risk_level=RiskLevel.LOW,
                confidence_score=1.5,  # out of bounds
            )


# ────────────────────────────── Report Models ────────────────────────────────


class TestRiskDistribution:
    def test_defaults(self):
        rd = RiskDistribution()
        assert rd.critical == 0
        assert rd.high == 0
        assert rd.medium == 0
        assert rd.low == 0


class TestComplianceSummary:
    def test_with_values(self):
        cs = ComplianceSummary(
            score=85.0,
            total_items=10,
            passed=8,
            failed=1,
            partial=1,
        )
        assert cs.score == 85.0
        assert cs.passed == 8


class TestComplianceReport:
    def test_auto_fields(self):
        report = ComplianceReport(
            document=DocumentInfo(id="d1", filename="test.pdf"),
            dqc_version="1.0",
        )
        assert report.report_id  # auto-generated
        assert report.generated_at
        assert report.findings == []
        assert report.recommendations == []

    def test_with_findings(self):
        finding = DQCEvaluationResult(
            dqc_item_id="DQC-001",
            status=DQCStatus.PASS,
            justification="ok",
            risk_level=RiskLevel.LOW,
            confidence_score=0.9,
        )
        report = ComplianceReport(
            document=DocumentInfo(id="d1", filename="test.pdf"),
            dqc_version="1.0",
            findings=[finding],
        )
        assert len(report.findings) == 1
