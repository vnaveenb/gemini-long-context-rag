"""Custom LangChain callback handlers for logging, token tracking, and audit."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from src.logger import get_logger

logger = get_logger(__name__)


class TokenTrackingCallback(BaseCallbackHandler):
    """Track token usage across all LLM calls in a pipeline run."""

    def __init__(self) -> None:
        super().__init__()
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_calls: int = 0
        self._call_start_times: dict[UUID, float] = {}
        self.total_latency_ms: float = 0.0

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._call_start_times[run_id] = time.time()
        self.total_calls += 1
        logger.debug(
            "LLM call started",
            run_id=str(run_id),
            model=serialized.get("kwargs", {}).get("model", "unknown"),
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        # Track latency
        start = self._call_start_times.pop(run_id, None)
        if start:
            self.total_latency_ms += (time.time() - start) * 1000

        # Track tokens from response metadata
        if response.llm_output:
            usage = response.llm_output.get("usage_metadata") or response.llm_output.get(
                "token_usage", {}
            )
            if usage:
                self.total_input_tokens += usage.get("prompt_tokens", 0) or usage.get(
                    "input_tokens", 0
                )
                self.total_output_tokens += usage.get("completion_tokens", 0) or usage.get(
                    "output_tokens", 0
                )

        logger.debug(
            "LLM call completed",
            run_id=str(run_id),
            cumulative_input_tokens=self.total_input_tokens,
            cumulative_output_tokens=self.total_output_tokens,
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._call_start_times.pop(run_id, None)
        logger.error("LLM call failed", run_id=str(run_id), error=str(error))

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def summary(self) -> dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 2),
        }

    def reset(self) -> None:
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_calls = 0
        self.total_latency_ms = 0.0
        self._call_start_times.clear()
