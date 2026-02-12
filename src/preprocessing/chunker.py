"""Section-aware chunking with semantic boundary detection and metadata tagging."""

from __future__ import annotations

import tiktoken

from src.config import get_settings
from src.logger import get_logger
from src.models.chunk import Chunk
from src.models.document import ExtractedContent, Section

logger = get_logger(__name__)

# Use cl100k_base tokenizer (close to Gemini tokenizer for counting purposes)
_ENCODER = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_ENCODER.encode(text))


def _split_text(
    text: str,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """Split text into chunks respecting sentence boundaries."""
    sentences = _sentence_split(text)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sent_tokens = _count_tokens(sentence)

        # If a single sentence exceeds max, force-split by words
        if sent_tokens > max_tokens:
            if current:
                chunks.append(" ".join(current))
                current, current_tokens = _overlap_carry(current, overlap_tokens)

            words = sentence.split()
            word_buf: list[str] = []
            word_tok = 0
            for w in words:
                wt = _count_tokens(w)
                if word_tok + wt > max_tokens and word_buf:
                    chunks.append(" ".join(word_buf))
                    word_buf, word_tok = [], 0
                word_buf.append(w)
                word_tok += wt
            if word_buf:
                current = word_buf
                current_tokens = word_tok
            continue

        if current_tokens + sent_tokens > max_tokens and current:
            chunks.append(" ".join(current))
            current, current_tokens = _overlap_carry(current, overlap_tokens)

        current.append(sentence)
        current_tokens += sent_tokens

    if current:
        chunks.append(" ".join(current))

    return chunks


def _sentence_split(text: str) -> list[str]:
    """Naive but effective sentence splitter (paragraph + period-based)."""
    import re

    # Split on paragraph boundaries first
    paragraphs = re.split(r"\n\s*\n", text)
    sentences: list[str] = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # Split on sentence-ending punctuation
        parts = re.split(r"(?<=[.!?])\s+", para)
        sentences.extend(p.strip() for p in parts if p.strip())
    return sentences


def _overlap_carry(
    current: list[str], overlap_tokens: int
) -> tuple[list[str], int]:
    """Return the tail of `current` that fits within `overlap_tokens`."""
    carry: list[str] = []
    carry_tok = 0
    for sent in reversed(current):
        st = _count_tokens(sent)
        if carry_tok + st > overlap_tokens:
            break
        carry.insert(0, sent)
        carry_tok += st
    return carry, carry_tok


def _build_section_map(content: ExtractedContent) -> dict[int, str]:
    """Map page numbers to the most recent section title."""
    page_section: dict[int, str] = {}
    current_section = "Untitled"
    section_pages: list[tuple[int, str]] = []

    for sec in content.sections:
        if sec.page_start is not None:
            section_pages.append((sec.page_start, sec.title))

    section_pages.sort(key=lambda x: x[0])

    sec_idx = 0
    for page in content.pages:
        while sec_idx < len(section_pages) and section_pages[sec_idx][0] <= page.page_number:
            current_section = section_pages[sec_idx][1]
            sec_idx += 1
        page_section[page.page_number] = current_section

    return page_section


def chunk_document(content: ExtractedContent) -> list[Chunk]:
    """Chunk an extracted document into metadata-tagged pieces.

    Strategy:
    1. Group text by section boundaries.
    2. Split each section into chunks of ~chunk_size tokens with overlap.
    3. Tag each chunk with section name, page range, doc_id.
    """
    settings = get_settings()
    max_tokens = settings.chunk_size
    overlap_tokens = settings.chunk_overlap

    logger.info(
        "Chunking document",
        doc_id=content.doc_id,
        max_tokens=max_tokens,
        overlap=overlap_tokens,
    )

    # Build section text groups
    section_groups: list[tuple[str, str, int | None]] = []  # (section_name, text, page_start)

    if content.sections:
        # Use detected sections
        for sec in content.sections:
            sec_text = sec.content
            if not sec_text:
                # Gather text from pages in this section's range
                page_texts = []
                for page in content.pages:
                    if sec.page_start and sec.page_end:
                        if sec.page_start <= page.page_number <= sec.page_end:
                            page_texts.append(page.text)
                sec_text = "\n".join(page_texts)
            if sec_text.strip():
                section_groups.append((sec.title, sec_text, sec.page_start))
    else:
        # No sections detected — treat entire doc as one section
        section_groups.append(("Full Document", content.raw_text, 1))

    # Chunk each section
    chunks: list[Chunk] = []
    chunk_index = 0

    for section_name, section_text, page_start in section_groups:
        if not section_text.strip():
            continue

        text_chunks = _split_text(section_text, max_tokens, overlap_tokens)
        for chunk_text in text_chunks:
            token_count = _count_tokens(chunk_text)

            # Skip trivially small chunks
            if token_count < 20:
                continue

            chunks.append(
                Chunk(
                    doc_id=content.doc_id,
                    text=chunk_text,
                    section_name=section_name,
                    page_number=page_start,
                    chunk_index=chunk_index,
                    token_count=token_count,
                    upload_timestamp=content.upload_timestamp,
                    metadata={
                        "filename": content.filename,
                        "format": content.format.value,
                    },
                )
            )
            chunk_index += 1

    logger.info(
        "Chunking complete",
        doc_id=content.doc_id,
        total_chunks=len(chunks),
        total_tokens=sum(c.token_count for c in chunks),
    )
    return chunks
