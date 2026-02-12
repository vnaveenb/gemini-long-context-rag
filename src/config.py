"""Central configuration — loads from .env and environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Environment ──────────────────────────────────────────────
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # ── LLM ──────────────────────────────────────────────────────
    llm_provider: str = "google_genai"
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    # ── Embeddings ───────────────────────────────────────────────
    embedding_provider: str = "google_genai"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768

    # ── API Keys (provider-specific) ─────────────────────────────
    google_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # ── Vector DB ────────────────────────────────────────────────
    chroma_persist_dir: str = str(_BASE_DIR / "data" / "vectordb")
    chroma_collection_name: str = "lra_documents"

    # ── Retrieval ────────────────────────────────────────────────
    retrieval_top_k: int = 10
    retrieval_score_threshold: float = 0.5

    # ── Chunking ─────────────────────────────────────────────────
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # ── Paths ────────────────────────────────────────────────────
    upload_dir: str = str(_BASE_DIR / "data" / "uploads")
    report_dir: str = str(_BASE_DIR / "data" / "reports")
    dqc_dir: str = str(_BASE_DIR / "data" / "dqc")
    audit_db_path: str = str(_BASE_DIR / "data" / "audit.db")

    # ── API ──────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = ""

    # ── Helpers ──────────────────────────────────────────────────
    def ensure_dirs(self) -> None:
        """Create all required data directories."""
        for d in (
            self.chroma_persist_dir,
            self.upload_dir,
            self.report_dir,
            self.dqc_dir,
        ):
            Path(d).mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


if __name__ == "__main__":
    s = get_settings()
    s.ensure_dirs()
    print(f"Environment : {s.environment}")
    print(f"LLM         : {s.llm_provider} / {s.llm_model}")
    print(f"Embedding   : {s.embedding_provider} / {s.embedding_model} (dim={s.embedding_dimensions})")
    print(f"Vector DB   : {s.chroma_persist_dir}")
    print("✓ Config loaded successfully")
