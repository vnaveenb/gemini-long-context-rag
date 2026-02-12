"""Tests for the LLM factory and token tracking callback."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.config import Settings
from src.llm.callbacks import TokenTrackingCallback


class TestTokenTrackingCallback:
    def test_initial_state(self):
        cb = TokenTrackingCallback()
        assert cb.total_tokens == 0
        assert cb.total_input_tokens == 0
        assert cb.total_output_tokens == 0
        assert cb.total_calls == 0

    def test_summary(self):
        cb = TokenTrackingCallback()
        s = cb.summary()
        assert s["total_tokens"] == 0
        assert s["total_calls"] == 0
        assert "total_latency_ms" in s

    def test_reset(self):
        cb = TokenTrackingCallback()
        cb.total_input_tokens = 100
        cb.total_output_tokens = 50
        cb.total_calls = 3
        cb.reset()
        assert cb.total_tokens == 0
        assert cb.total_calls == 0


class TestLLMFactory:
    """Test that the factory raises for unknown providers (without needing real API keys)."""

    def test_unsupported_llm_provider(self):
        from src.llm.factory import get_llm

        settings = Settings(llm_provider="unsupported_provider")
        with pytest.raises(ValueError, match="Unsupported"):
            get_llm(settings)

    def test_unsupported_embedding_provider(self):
        from src.llm.factory import get_embeddings

        settings = Settings(embedding_provider="unsupported_provider")
        with pytest.raises(ValueError, match="Unsupported"):
            get_embeddings(settings)
