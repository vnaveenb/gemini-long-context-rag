"""Tests for the extractor factory (format detection, hashing, routing)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ingestion.extractor_factory import detect_format, extract_document, _file_hash
from src.models.document import DocumentFormat


class TestDetectFormat:
    def test_pdf(self):
        assert detect_format("file.pdf") == DocumentFormat.PDF

    def test_docx(self):
        assert detect_format("file.docx") == DocumentFormat.DOCX

    def test_pptx(self):
        assert detect_format("file.pptx") == DocumentFormat.PPTX

    def test_xlsx(self):
        assert detect_format("file.xlsx") == DocumentFormat.XLSX

    def test_case_insensitive(self):
        assert detect_format("file.PDF") == DocumentFormat.PDF

    def test_unsupported_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            detect_format("file.txt")

    def test_no_extension_raises(self):
        with pytest.raises(ValueError):
            detect_format("noext")


class TestFileHash:
    def test_hash_deterministic(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h1 = _file_hash(f)
        h2 = _file_hash(f)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f1.write_text("aaa")
        f2 = tmp_path / "b.txt"
        f2.write_text("bbb")
        assert _file_hash(f1) != _file_hash(f2)


class TestExtractDocument:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_document("nonexistent_file.pdf")

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.pdf"
        f.write_bytes(b"")
        content = extract_document(f)
        assert not content.is_valid
        assert "empty" in content.extraction_errors[0].lower()

    def test_unsupported_format(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported"):
            extract_document(f)
