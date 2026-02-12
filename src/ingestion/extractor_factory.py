"""Extractor factory — routes files to the correct format-specific extractor.

Also handles document hashing and version tracking.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from src.logger import get_logger
from src.models.document import DocumentFormat, ExtractedContent
from src.ingestion.pdf_extractor import extract_pdf
from src.ingestion.docx_extractor import extract_docx
from src.ingestion.pptx_extractor import extract_pptx
from src.ingestion.xlsx_extractor import extract_xlsx

logger = get_logger(__name__)

_EXTENSION_MAP: dict[str, DocumentFormat] = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".pptx": DocumentFormat.PPTX,
    ".xlsx": DocumentFormat.XLSX,
}

_EXTRACTOR_MAP = {
    DocumentFormat.PDF: extract_pdf,
    DocumentFormat.DOCX: extract_docx,
    DocumentFormat.PPTX: extract_pptx,
    DocumentFormat.XLSX: extract_xlsx,
}


def _file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            sha.update(block)
    return sha.hexdigest()


def detect_format(file_path: str | Path) -> DocumentFormat:
    """Detect document format from file extension."""
    ext = Path(file_path).suffix.lower()
    fmt = _EXTENSION_MAP.get(ext)
    if fmt is None:
        raise ValueError(f"Unsupported file format: {ext}")
    return fmt


def extract_document(file_path: str | Path) -> ExtractedContent:
    """Extract content from a document file. Auto-detects format.

    Returns an ExtractedContent with errors populated if extraction fails.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.stat().st_size == 0:
        return ExtractedContent(
            filename=file_path.name,
            format=detect_format(file_path),
            extraction_errors=["File is empty (0 bytes)"],
        )

    fmt = detect_format(file_path)
    extractor = _EXTRACTOR_MAP[fmt]

    logger.info("Starting extraction", file=file_path.name, format=fmt.value)
    content = extractor(file_path)

    # Attach file hash for versioning / dedup
    content.file_hash = _file_hash(file_path)

    if not content.is_valid:
        logger.warning(
            "Extraction yielded no text",
            file=file_path.name,
            errors=content.extraction_errors,
        )

    return content
