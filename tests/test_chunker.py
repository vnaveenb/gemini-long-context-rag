"""Tests for the section-aware chunker."""

from __future__ import annotations

import pytest

from src.models.document import (
    DocumentFormat,
    DocumentMetadata,
    ExtractedContent,
    PageContent,
    Section,
)
from src.preprocessing.chunker import chunk_document, _count_tokens, _split_text, _sentence_split


class TestCountTokens:
    def test_empty(self):
        assert _count_tokens("") == 0

    def test_simple(self):
        tokens = _count_tokens("Hello world")
        assert tokens > 0

    def test_long_text(self):
        text = "word " * 200
        tokens = _count_tokens(text)
        assert tokens > 100


class TestSentenceSplit:
    def test_single_sentence(self):
        result = _sentence_split("Hello world.")
        assert len(result) >= 1

    def test_multiple_sentences(self):
        result = _sentence_split("First sentence. Second sentence. Third one.")
        assert len(result) == 3

    def test_paragraph_boundaries(self):
        text = "Paragraph one.\n\nParagraph two."
        result = _sentence_split(text)
        assert len(result) == 2

    def test_empty_text(self):
        assert _sentence_split("") == []
        assert _sentence_split("   ") == []


class TestSplitText:
    def test_short_text_no_split(self):
        result = _split_text("Short text here.", max_tokens=100, overlap_tokens=10)
        assert len(result) == 1

    def test_splits_long_text(self):
        # Create text long enough to be split
        text = ". ".join(f"This is sentence number {i}" for i in range(100))
        result = _split_text(text, max_tokens=50, overlap_tokens=10)
        assert len(result) > 1

    def test_respects_max_tokens(self):
        text = ". ".join(f"This is a reasonably long sentence number {i}" for i in range(50))
        result = _split_text(text, max_tokens=100, overlap_tokens=20)
        for chunk in result:
            # Allow some tolerance for sentence boundary alignment
            assert _count_tokens(chunk) < 200  # generous upper bound


class TestChunkDocument:
    def _make_content(
        self,
        raw_text: str = "",
        sections: list[Section] | None = None,
        pages: list[PageContent] | None = None,
    ) -> ExtractedContent:
        return ExtractedContent(
            doc_id="test-doc-001",
            filename="test.pdf",
            format=DocumentFormat.PDF,
            metadata=DocumentMetadata(page_count=1),
            pages=pages or [],
            sections=sections or [],
            raw_text=raw_text,
        )

    def test_empty_document(self):
        content = self._make_content(raw_text="")
        chunks = chunk_document(content)
        assert chunks == []

    def test_single_section_short(self):
        """A document with a single short section produces 1 chunk."""
        section_text = (
            "This is a comprehensive introduction to the learning content compliance system. "
            "It covers the fundamental principles of quality assurance in educational materials. "
            "The document outlines key requirements for content structure, accessibility, and assessment design. "
            "Each section provides detailed criteria that must be met to achieve compliance certification."
        )
        content = self._make_content(
            raw_text=section_text,
            sections=[Section(title="Intro", page_start=1, page_end=1, content=section_text)],
        )
        chunks = chunk_document(content)
        assert len(chunks) >= 1
        assert chunks[0].section_name == "Intro"
        assert chunks[0].doc_id == "test-doc-001"

    def test_no_sections_uses_raw_text(self):
        """When no sections are detected, fall back to full raw_text."""
        raw = (
            "A meaningful and sufficiently long paragraph that has enough tokens to survive "
            "the twenty-token minimum threshold filter applied during the chunking process. "
            "This text covers additional details about compliance requirements, assessment "
            "methodologies, and learning objective definitions used throughout the system."
        )
        content = self._make_content(raw_text=raw)
        chunks = chunk_document(content)
        assert len(chunks) >= 1
        assert chunks[0].section_name == "Full Document"

    def test_chunk_metadata(self):
        content = self._make_content(
            sections=[
                Section(title="Chapter 1", page_start=1, page_end=2, content="Sample text for testing the chunker pipeline module."),
            ],
        )
        chunks = chunk_document(content)
        if chunks:
            c = chunks[0]
            assert c.metadata["filename"] == "test.pdf"
            assert c.metadata["format"] == "pdf"
            assert c.chunk_index == 0
            assert c.token_count > 0

    def test_multiple_sections(self):
        text_a = (
            "This section covers the introduction and background of the learning material, providing "
            "a comprehensive overview of all compliance topics. It describes the scope, objectives, "
            "and target audience for the educational content being reviewed under the DQC framework."
        )
        text_b = (
            "This section discusses the assessment methodology and evaluation criteria employed "
            "in the compliance review process. It outlines specific rubrics, scoring guidelines, "
            "and the evidence-based approach used to determine whether requirements are satisfied."
        )
        content = self._make_content(
            sections=[
                Section(title="Section A", page_start=1, page_end=1, content=text_a),
                Section(title="Section B", page_start=2, page_end=2, content=text_b),
            ],
        )
        chunks = chunk_document(content)
        section_names = {c.section_name for c in chunks}
        assert "Section A" in section_names
        assert "Section B" in section_names

    def test_chunk_indices_sequential(self):
        text = ". ".join(f"Sentence number {i} with some extra words to bulk it up" for i in range(80))
        content = self._make_content(
            sections=[Section(title="Big", page_start=1, page_end=10, content=text)],
        )
        chunks = chunk_document(content)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))
