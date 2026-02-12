"""ChromaDB vector store — uses LangChain Chroma wrapper for provider-agnostic storage."""

from __future__ import annotations

from langchain_chroma import Chroma
from langchain_core.documents import Document as LCDocument
from langchain_core.embeddings import Embeddings

from src.config import Settings, get_settings
from src.llm.factory import get_embeddings
from src.logger import get_logger
from src.models.chunk import Chunk

logger = get_logger(__name__)


class VectorStore:
    """Wraps LangChain Chroma for chunk storage, embedding, and retrieval."""

    def __init__(
        self,
        settings: Settings | None = None,
        embeddings: Embeddings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._embeddings = embeddings or get_embeddings(self._settings)
        self._store = Chroma(
            collection_name=self._settings.chroma_collection_name,
            embedding_function=self._embeddings,
            persist_directory=self._settings.chroma_persist_dir,
        )
        logger.info(
            "VectorStore initialised",
            collection=self._settings.chroma_collection_name,
            persist_dir=self._settings.chroma_persist_dir,
        )

    # ── Write ────────────────────────────────────────────────────

    def add_chunks(self, chunks: list[Chunk]) -> list[str]:
        """Embed and store a list of Chunk objects. Returns their IDs."""
        if not chunks:
            return []

        documents = [
            LCDocument(
                page_content=chunk.text,
                metadata=chunk.to_vectorstore_metadata(),
            )
            for chunk in chunks
        ]
        ids = [chunk.chunk_id for chunk in chunks]

        logger.info("Adding chunks to vector store", count=len(chunks))
        self._store.add_documents(documents, ids=ids)
        logger.info("Chunks stored", count=len(ids))
        return ids

    # ── Delete ───────────────────────────────────────────────────

    def delete_by_doc_id(self, doc_id: str) -> None:
        """Remove all chunks belonging to a specific document."""
        logger.info("Deleting chunks for doc", doc_id=doc_id)
        self._store._collection.delete(where={"doc_id": doc_id})

    def reset_collection(self) -> None:
        """Drop and recreate the collection (for re-indexing)."""
        logger.warning("Resetting entire vector store collection")
        self._store._client.delete_collection(self._settings.chroma_collection_name)
        self._store = Chroma(
            collection_name=self._settings.chroma_collection_name,
            embedding_function=self._embeddings,
            persist_directory=self._settings.chroma_persist_dir,
        )

    # ── Read ─────────────────────────────────────────────────────

    def similarity_search(
        self,
        query: str,
        k: int | None = None,
        doc_id: str | None = None,
        score_threshold: float | None = None,
    ) -> list[tuple[LCDocument, float]]:
        """Search for similar documents, optionally filtered by doc_id."""
        k = k or self._settings.retrieval_top_k
        filter_dict = {"doc_id": doc_id} if doc_id else None

        results = self._store.similarity_search_with_relevance_scores(
            query,
            k=k,
            filter=filter_dict,
            score_threshold=score_threshold or self._settings.retrieval_score_threshold,
        )
        return results

    def as_retriever(self, doc_id: str | None = None, k: int | None = None):
        """Return a LangChain VectorStoreRetriever."""
        search_kwargs: dict = {"k": k or self._settings.retrieval_top_k}
        if doc_id:
            search_kwargs["filter"] = {"doc_id": doc_id}
        return self._store.as_retriever(search_kwargs=search_kwargs)

    @property
    def collection_count(self) -> int:
        return self._store._collection.count()
