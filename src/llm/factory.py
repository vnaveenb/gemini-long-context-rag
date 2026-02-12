"""LLM + Embedding provider factory — hot-swap via config, zero code changes.

Supported LLM providers:  google_genai | openai | anthropic | ollama
Supported Embedding providers:  google_genai | openai | huggingface | ollama
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from src.config import Settings, get_settings
from src.logger import get_logger

logger = get_logger(__name__)


# ── LLM Factory ─────────────────────────────────────────────────────────────


def get_llm(settings: Settings | None = None) -> BaseChatModel:
    """Return a LangChain ChatModel based on config. Provider-agnostic."""
    settings = settings or get_settings()
    provider = settings.llm_provider

    logger.info(
        "Initialising LLM",
        provider=provider,
        model=settings.llm_model,
    )

    match provider:
        case "google_genai":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.llm_model,
                google_api_key=settings.google_api_key,
                temperature=settings.llm_temperature,
                max_output_tokens=settings.llm_max_tokens,
                convert_system_message_to_human=False,
            )

        case "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.openai_api_key,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )

        case "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=settings.llm_model,
                api_key=settings.anthropic_api_key,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )

        case "ollama":
            from langchain_community.chat_models import ChatOllama

            return ChatOllama(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
            )

        case _:
            raise ValueError(f"Unsupported LLM provider: {provider}")


# ── Embedding Factory ────────────────────────────────────────────────────────


def get_embeddings(settings: Settings | None = None) -> Embeddings:
    """Return a LangChain Embeddings model based on config. Provider-agnostic."""
    settings = settings or get_settings()
    provider = settings.embedding_provider

    logger.info(
        "Initialising Embeddings",
        provider=provider,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )

    match provider:
        case "google_genai":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            return GoogleGenerativeAIEmbeddings(
                model=f"models/{settings.embedding_model}",
                google_api_key=settings.google_api_key,
                task_type="RETRIEVAL_DOCUMENT",
            )

        case "openai":
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(
                model=settings.embedding_model,
                api_key=settings.openai_api_key,
                dimensions=settings.embedding_dimensions,
            )

        case "huggingface":
            from langchain_community.embeddings import HuggingFaceEmbeddings

            return HuggingFaceEmbeddings(
                model_name=settings.embedding_model,
            )

        case "ollama":
            from langchain_community.embeddings import OllamaEmbeddings

            return OllamaEmbeddings(
                model=settings.embedding_model,
            )

        case _:
            raise ValueError(f"Unsupported embedding provider: {provider}")
