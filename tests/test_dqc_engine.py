"""Tests for the DQC evaluation engine — risk matrix, checklist loading, helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluation.dqc_engine import _risk_level, load_dqc_checklist, PROMPT_VERSION
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
