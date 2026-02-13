"""Tests for the DQC evaluation engine — risk matrix, checklist loading, helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluation.dqc_engine import _risk_level, load_dqc_checklist, PROMPT_VERSION, DQCEngine
from src.models.dqc import DQCChecklist, DQCStatus, RiskLevel


# ────────────────────────────── Risk Matrix ──────────────────────────────────


class TestRiskLevel:
    """Test the risk scoring matrix: status × confidence → risk level."""

    # FAIL cases
    def test_fail_high_confidence(self):
        assert _risk_level(DQCStatus.FAIL, 0.9) == RiskLevel.CRITICAL

    def test_fail_medium_confidence(self):
        assert _risk_level(DQCStatus.FAIL, 0.6) == RiskLevel.HIGH

    def test_fail_low_confidence(self):
        assert _risk_level(DQCStatus.FAIL, 0.3) == RiskLevel.MEDIUM

    # PARTIAL cases
    def test_partial_high_confidence(self):
        assert _risk_level(DQCStatus.PARTIAL, 0.85) == RiskLevel.HIGH

    def test_partial_medium_confidence(self):
        assert _risk_level(DQCStatus.PARTIAL, 0.6) == RiskLevel.MEDIUM

    def test_partial_low_confidence(self):
        assert _risk_level(DQCStatus.PARTIAL, 0.3) == RiskLevel.LOW

    # PASS cases
    def test_pass_high_confidence(self):
        assert _risk_level(DQCStatus.PASS, 0.95) == RiskLevel.LOW

    def test_pass_low_confidence(self):
        assert _risk_level(DQCStatus.PASS, 0.3) == RiskLevel.LOW

    # Edge cases
    def test_fail_exactly_080(self):
        assert _risk_level(DQCStatus.FAIL, 0.8) == RiskLevel.CRITICAL

    def test_fail_exactly_050(self):
        assert _risk_level(DQCStatus.FAIL, 0.5) == RiskLevel.HIGH

    def test_partial_exactly_080(self):
        assert _risk_level(DQCStatus.PARTIAL, 0.8) == RiskLevel.HIGH

    def test_partial_exactly_050(self):
        assert _risk_level(DQCStatus.PARTIAL, 0.5) == RiskLevel.MEDIUM


# ────────────────────────────── DQC Loading ──────────────────────────────────


class TestLoadDQCChecklist:
    def test_load_valid_json(self, tmp_path):
        data = {
            "version": "1.0",
            "name": "Test Checklist",
            "description": "For testing",
            "items": [
                {
                    "item_id": "DQC-001",
                    "category": "Structure",
                    "requirement": "Has a title",
                    "criteria": "Document must have a title page",
                    "weight": 1.0,
                },
                {
                    "item_id": "DQC-002",
                    "category": "Content",
                    "requirement": "Learning objectives",
                    "criteria": "Clearly stated learning objectives",
                    "weight": 1.5,
                },
            ],
        }
        path = tmp_path / "dqc.json"
        path.write_text(json.dumps(data))

        checklist = load_dqc_checklist(path)
        assert isinstance(checklist, DQCChecklist)
        assert checklist.version == "1.0"
        assert checklist.name == "Test Checklist"
        assert len(checklist.items) == 2
        assert checklist.items[0].item_id == "DQC-001"
        assert checklist.items[1].weight == 1.5

    def test_load_sample_dqc(self):
        """Verify the sample DQC file in the project can be loaded."""
        sample_path = Path(__file__).resolve().parent.parent / "data" / "dqc" / "sample_dqc.json"
        if sample_path.exists():
            checklist = load_dqc_checklist(sample_path)
            assert isinstance(checklist, DQCChecklist)
            assert len(checklist.items) > 0

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_dqc_checklist("/path/does/not/exist.json")


class TestPromptVersion:
    def test_version_set(self):
        assert PROMPT_VERSION == "v1.0"


# ────────────────────────── JSON Repair / Parser ─────────────────────────────

VALID_JSON = json.dumps({
    "evaluations": [
        {
            "dqc_item_id": "DQC-001",
            "status": "Pass",
            "justification": "Objectives are clearly stated.",
            "evidence_quotes": ["The course aims to..."],
            "risk_level": "Low",
            "recommendation": None,
            "confidence_score": 0.95,
            "sections_reviewed": ["Introduction"],
        }
    ],
    "executive_summary": "The document is well-structured.",
})

MINI_CHECKLIST = DQCChecklist(
    version="1.0",
    name="Test",
    description="Test checklist",
    items=[
        {
            "item_id": "DQC-001",
            "category": "Structure",
            "requirement": "Has objectives",
            "criteria": "Must have objectives",
            "weight": 1.0,
        }
    ],
)


class TestStripMarkdownFences:
    def test_no_fences(self):
        assert DQCEngine._strip_markdown_fences(VALID_JSON) == VALID_JSON

    def test_json_fences(self):
        wrapped = f"```json\n{VALID_JSON}\n```"
        assert json.loads(DQCEngine._strip_markdown_fences(wrapped))

    def test_plain_fences(self):
        wrapped = f"```\n{VALID_JSON}\n```"
        assert json.loads(DQCEngine._strip_markdown_fences(wrapped))


class TestExtractJsonBlock:
    def test_clean_json(self):
        result = DQCEngine._extract_json_block(VALID_JSON)
        assert result is not None
        assert json.loads(result)

    def test_text_before_json(self):
        text = f"Here is the result:\n\n{VALID_JSON}\n\nDone."
        result = DQCEngine._extract_json_block(text)
        assert result is not None
        data = json.loads(result)
        assert "evaluations" in data

    def test_no_json(self):
        assert DQCEngine._extract_json_block("No JSON here") is None


class TestRepairJson:
    def test_trailing_comma_object(self):
        bad = '{"evaluations": [], "executive_summary": "ok",}'
        fixed = DQCEngine._repair_json(bad)
        data = json.loads(fixed)
        assert data["executive_summary"] == "ok"

    def test_trailing_comma_array(self):
        bad = '{"evaluations": [{"dqc_item_id": "DQC-001"},], "executive_summary": ""}'
        fixed = DQCEngine._repair_json(bad)
        data = json.loads(fixed)
        assert len(data["evaluations"]) == 1


class TestParseBatchResponse:
    """Test the full multi-layer parser via _try_parse_json."""

    def test_clean_json(self):
        engine = DQCEngine.__new__(DQCEngine)
        data = engine._try_parse_json(VALID_JSON)
        assert data is not None
        assert data["evaluations"][0]["dqc_item_id"] == "DQC-001"

    def test_markdown_wrapped(self):
        engine = DQCEngine.__new__(DQCEngine)
        wrapped = f"```json\n{VALID_JSON}\n```"
        data = engine._try_parse_json(wrapped)
        assert data is not None
        assert "evaluations" in data

    def test_trailing_comma_recovery(self):
        engine = DQCEngine.__new__(DQCEngine)
        bad = VALID_JSON[:-1] + ",}"  # add trailing comma before closing brace
        data = engine._try_parse_json(bad)
        assert data is not None

    def test_garbage_returns_none(self):
        engine = DQCEngine.__new__(DQCEngine)
        assert engine._try_parse_json("This is not JSON at all.") is None

    def test_full_parse_with_fallback(self):
        """When parsing fails completely, _parse_batch_response returns fallback results."""
        engine = DQCEngine.__new__(DQCEngine)
        findings, summary = engine._parse_batch_response("GARBAGE", MINI_CHECKLIST)
        assert len(findings) == 1
        assert findings[0].status == DQCStatus.PARTIAL
        assert "could not be parsed" in findings[0].justification

    def test_full_parse_success(self):
        """When parsing succeeds, _parse_batch_response returns real results."""
        engine = DQCEngine.__new__(DQCEngine)
        findings, summary = engine._parse_batch_response(VALID_JSON, MINI_CHECKLIST)
        assert len(findings) == 1
        assert findings[0].status == DQCStatus.PASS
        assert findings[0].dqc_item_id == "DQC-001"
        assert summary == "The document is well-structured."
