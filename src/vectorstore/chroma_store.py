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

    def add_chunks(self, chunks: list[Chunk], batch_size: int = 100) -> list[str]:
        """Embed and store a list of Chunk objects in batches."""
        if not chunks:
            return []

        import time

        documents = [
            LCDocument(
                page_content=chunk.text,
                metadata=chunk.to_vectorstore_metadata(),
            )
            for chunk in chunks
        ]
        ids = [chunk.chunk_id for chunk in chunks]

        logger.info("Adding chunks to vector store", count=len(chunks))

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]

            try:
                self._store.add_documents(batch_docs, ids=batch_ids)
                logger.debug(f"Added batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")
            except Exception as e:
                logger.error(f"Error adding batch starting at index {i}: {e}")
                # Wait and retry once on failure
                time.sleep(5)
                try:
                    self._store.add_documents(batch_docs, ids=batch_ids)
                except Exception as retry_e:
                    logger.error(f"Retry failed for batch starting at index {i}: {retry_e}")
                    raise retry_e

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
