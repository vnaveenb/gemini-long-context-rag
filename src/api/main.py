"""FastAPI application — main entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.v1 import router as v1_router
from src.api.schemas import HealthResponse
from src.config import get_settings
from src.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)
settings = get_settings()
settings.ensure_dirs()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LRA API starting", environment=settings.environment)
    yield
    logger.info("LRA API shutting down")


app = FastAPI(
    title="Learning Content Compliance Intelligence System",
    description="RAG-based DQC validation API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health (root-level, not behind /api/v1) ──────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", environment=settings.environment)


# ── Mount v1 router ──────────────────────────────────────────────────────────

app.include_router(v1_router)
