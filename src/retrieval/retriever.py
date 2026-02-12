"""Retrieval engine — semantic search + section reconstruction + context assembly."""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.documents import Document as LCDocument

from src.config import get_settings
from src.logger import get_logger
from src.vectorstore.chroma_store import VectorStore

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """Structured result from a retrieval query."""

    query: str
    chunks: list[LCDocument] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    total_tokens: int = 0

    @property
    def context_text(self) -> str:
        """Assemble retrieved chunks into a single context string."""
        parts: list[str] = []
        for doc in self.chunks:
            section = doc.metadata.get("section_name", "Unknown Section")
            page = doc.metadata.get("page_number", "?")
            parts.append(f"[Section: {section} | Page: {page}]\n{doc.page_content}")
        return "\n\n---\n\n".join(parts)


class RetrievalEngine:
    """Retrieve and assemble relevant context for DQC evaluation."""

    def __init__(self, vector_store: VectorStore | None = None) -> None:
        self._settings = get_settings()
        self._store = vector_store or VectorStore()

    def retrieve(
        self,
        query: str,
        doc_id: str | None = None,
        k: int | None = None,
    ) -> RetrievalResult:
        """Run semantic search + reconstruction for a single query.

        Args:
            query: The DQC requirement or search text.
            doc_id: Scope results to a specific document.
            k: Override top-k setting.
        """
        k = k or self._settings.retrieval_top_k

        results = self._store.similarity_search(
            query=query,
            k=k,
            doc_id=doc_id,
        )

        chunks = [doc for doc, _ in results]
        scores = [score for _, score in results]

        # Group by section and sort for reading order
        chunks = self._group_by_section(chunks)

        # Estimate tokens
        total_tokens = sum(
            doc.metadata.get("token_count", len(doc.page_content.split())) for doc in chunks
        )

        result = RetrievalResult(
            query=query,
            chunks=chunks,
            scores=scores,
            total_tokens=total_tokens,
        )

        logger.info(
            "Retrieval complete",
            query=query[:80],
            chunks_found=len(chunks),
            total_tokens=total_tokens,
        )
        return result

    def _group_by_section(self, chunks: list[LCDocument]) -> list[LCDocument]:
        """Group chunks by section, then sort by page/chunk_index within each."""
        section_map: dict[str, list[LCDocument]] = {}
        for doc in chunks:
            section = doc.metadata.get("section_name", "")
            section_map.setdefault(section, []).append(doc)

        ordered: list[LCDocument] = []
        for _section, docs in section_map.items():
            docs.sort(
                key=lambda d: (
                    d.metadata.get("page_number", 0),
                    d.metadata.get("chunk_index", 0),
                )
            )
            ordered.extend(docs)
        return ordered

    def retrieve_for_dqc_item(
        self,
        requirement_text: str,
        doc_id: str,
    ) -> RetrievalResult:
        """Convenience method: retrieve context for a single DQC checklist item."""
        return self.retrieve(
            query=requirement_text,
            doc_id=doc_id,
        )
