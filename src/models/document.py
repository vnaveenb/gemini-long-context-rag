"""Pydantic models for documents and extracted content."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"


class Section(BaseModel):
    """A logical section detected within a document."""

    title: str
    level: int = 1  # heading level (1 = H1, 2 = H2, …)
    page_start: int | None = None
    page_end: int | None = None
    content: str = ""


class PageContent(BaseModel):
    """Text content for a single page / slide / sheet."""

    page_number: int
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentMetadata(BaseModel):
    """Metadata extracted from a document."""

    author: str | None = None
    creation_date: datetime | None = None
    modification_date: datetime | None = None
    page_count: int = 0
    word_count: int = 0
    title: str | None = None
    subject: str | None = None


class ExtractedContent(BaseModel):
    """Result of the ingestion / extraction pipeline for one document."""

    doc_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    filename: str
    format: DocumentFormat
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    file_hash: str = ""  # SHA-256
    version: int = 1
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    pages: list[PageContent] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    raw_text: str = ""
    extraction_errors: list[str] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.raw_text.strip()) > 0
