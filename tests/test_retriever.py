"""Tests for the retrieval engine (with mocked vector store)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document as LCDocument

from src.retrieval.retriever import RetrievalEngine, RetrievalResult


class TestRetrievalResult:
    def test_empty_context(self):
        r = RetrievalResult(query="test")
        assert r.context_text == ""
        assert r.chunks == []
        assert r.total_tokens == 0

    def test_context_text_assembly(self):
        docs = [
            LCDocument(
                page_content="First chunk content",
                metadata={"section_name": "Intro", "page_number": 1},
            ),
            LCDocument(
                page_content="Second chunk content",
                metadata={"section_name": "Chapter 1", "page_number": 3},
            ),
        ]
        r = RetrievalResult(query="test", chunks=docs, scores=[0.9, 0.8])

        ctx = r.context_text
        assert "[Section: Intro | Page: 1]" in ctx
        assert "First chunk content" in ctx
        assert "[Section: Chapter 1 | Page: 3]" in ctx
        assert "Second chunk content" in ctx
        assert "---" in ctx  # separator

    def test_context_text_missing_metadata(self):
        docs = [LCDocument(page_content="text", metadata={})]
        r = RetrievalResult(query="q", chunks=docs)
        ctx = r.context_text
        assert "Unknown Section" in ctx


class TestRetrievalEngine:
    def test_group_by_section_orders_within_section(self):
        engine = RetrievalEngine.__new__(RetrievalEngine)
        docs = [
            LCDocument(page_content="c", metadata={"section_name": "A", "page_number": 3, "chunk_index": 1}),
            LCDocument(page_content="a", metadata={"section_name": "A", "page_number": 1, "chunk_index": 0}),
            LCDocument(page_content="b", metadata={"section_name": "A", "page_number": 2, "chunk_index": 0}),
        ]
        ordered = engine._group_by_section(docs)
        pages = [d.metadata["page_number"] for d in ordered]
        assert pages == [1, 2, 3]

    def test_group_by_section_separates_sections(self):
        engine = RetrievalEngine.__new__(RetrievalEngine)
        docs = [
            LCDocument(page_content="b1", metadata={"section_name": "B", "page_number": 5, "chunk_index": 0}),
            LCDocument(page_content="a1", metadata={"section_name": "A", "page_number": 1, "chunk_index": 0}),
        ]
        ordered = engine._group_by_section(docs)
        sections = [d.metadata["section_name"] for d in ordered]
        # Both sections present
        assert "A" in sections
        assert "B" in sections
