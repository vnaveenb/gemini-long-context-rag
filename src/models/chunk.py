"""Pydantic models for text chunks."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A single chunk of text with metadata, ready for embedding."""

    chunk_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    doc_id: str
    text: str
    section_name: str = ""
    page_number: int | None = None
    page_end: int | None = None
    chunk_index: int = 0
    token_count: int = 0
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_vectorstore_metadata(self) -> dict[str, Any]:
        """Flatten metadata for ChromaDB storage."""
        return {
            "doc_id": self.doc_id,
            "section_name": self.section_name,
            "page_number": self.page_number or 0,
            "page_end": self.page_end or self.page_number or 0,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            "upload_timestamp": self.upload_timestamp.isoformat(),
            **self.metadata,
        }
