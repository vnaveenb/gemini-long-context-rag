"""PDF text extraction using PyMuPDF (fitz)."""

from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF

from src.logger import get_logger
from src.models.document import (
    DocumentMetadata,
    ExtractedContent,
    DocumentFormat,
    PageContent,
    Section,
)

logger = get_logger(__name__)

# Heuristic heading patterns
_HEADING_RE = re.compile(
    r"^(?:chapter|module|section|part|unit|lesson)\s+\d",
    re.IGNORECASE,
)


def _is_heading(block_text: str, font_size: float, avg_font_size: float) -> bool:
    """Heuristic: a line is a heading if it's significantly larger or matches patterns."""
    if font_size > avg_font_size * 1.25 and len(block_text.strip()) < 200:
        return True
    if _HEADING_RE.match(block_text.strip()):
        return True
    return False


def _heading_level(font_size: float, avg_font_size: float) -> int:
    ratio = font_size / avg_font_size if avg_font_size else 1
    if ratio > 1.8:
        return 1
    if ratio > 1.4:
        return 2
    return 3


def extract_pdf(file_path: str | Path) -> ExtractedContent:
    """Extract text, sections, and metadata from a PDF file."""
    file_path = Path(file_path)
    logger.info("Extracting PDF", path=str(file_path))

    errors: list[str] = []

    try:
        doc = fitz.open(str(file_path))
    except Exception as exc:
        logger.error("Failed to open PDF", path=str(file_path), error=str(exc))
        return ExtractedContent(
            filename=file_path.name,
            format=DocumentFormat.PDF,
            extraction_errors=[f"Failed to open PDF: {exc}"],
        )

    pages: list[PageContent] = []
    sections: list[Section] = []
    all_text_parts: list[str] = []

    # First pass — collect average font size for heading detection
    font_sizes: list[float] = []
    for page in doc:
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get("blocks", [])
        for b in blocks:
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("text", "").strip():
                        font_sizes.append(span["size"])
    avg_font = sum(font_sizes) / len(font_sizes) if font_sizes else 12.0

    # Second pass — extract content
    for page_num, page in enumerate(doc, start=1):
        try:
            page_text = page.get_text("text") or ""
            pages.append(PageContent(page_number=page_num, text=page_text))
            all_text_parts.append(page_text)

            # Detect headings
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get("blocks", [])
            for b in blocks:
                for line in b.get("lines", []):
                    line_text = "".join(s.get("text", "") for s in line.get("spans", []))
                    if not line_text.strip():
                        continue
                    max_size = max((s["size"] for s in line.get("spans", []) if s.get("text", "").strip()), default=avg_font)
                    if _is_heading(line_text, max_size, avg_font):
                        sections.append(
                            Section(
                                title=line_text.strip(),
                                level=_heading_level(max_size, avg_font),
                                page_start=page_num,
                            )
                        )
        except Exception as exc:
            errors.append(f"Page {page_num}: {exc}")
            logger.warning("Error extracting page", page=page_num, error=str(exc))

    # Fill section page_end
    for i, sec in enumerate(sections):
        sec.page_end = sections[i + 1].page_start if i + 1 < len(sections) else len(pages)

    # Metadata
    meta_raw = doc.metadata or {}
    raw_text = "\n".join(all_text_parts)

    metadata = DocumentMetadata(
        author=meta_raw.get("author"),
        title=meta_raw.get("title"),
        subject=meta_raw.get("subject"),
        page_count=len(doc),
        word_count=len(raw_text.split()),
    )

    doc.close()

    content = ExtractedContent(
        filename=file_path.name,
        format=DocumentFormat.PDF,
        metadata=metadata,
        pages=pages,
        sections=sections,
        raw_text=raw_text,
        extraction_errors=errors,
    )
    logger.info(
        "PDF extraction complete",
        pages=len(pages),
        sections=len(sections),
        words=metadata.word_count,
    )
    return content
