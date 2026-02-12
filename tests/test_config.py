"""Tests for the config module."""

import os
from pathlib import Path

import pytest

from src.config import Settings, get_settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.llm_provider == "google_genai"
        assert s.llm_model == "gemini-2.5-flash"
        assert s.embedding_model == "gemini-embedding-001"
        assert s.embedding_dimensions == 768
        assert s.llm_temperature == 0.0
        assert s.chunk_size == 1000
        assert s.chunk_overlap == 150
        assert s.retrieval_top_k == 10
        assert s.retrieval_score_threshold == 0.5

    def test_environment_default(self):
        s = Settings()
        assert s.environment in ("development", "staging", "production")

    def test_ensure_dirs_creates_folders(self, tmp_path):
        s = Settings(
            chroma_persist_dir=str(tmp_path / "vectordb"),
            upload_dir=str(tmp_path / "uploads"),
            report_dir=str(tmp_path / "reports"),
            dqc_dir=str(tmp_path / "dqc"),
        )
        s.ensure_dirs()
        assert (tmp_path / "vectordb").is_dir()
        assert (tmp_path / "uploads").is_dir()
        assert (tmp_path / "reports").is_dir()
        assert (tmp_path / "dqc").is_dir()

    def test_get_settings_returns_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)
