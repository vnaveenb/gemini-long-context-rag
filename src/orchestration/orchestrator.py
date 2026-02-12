"""End-to-end orchestration pipeline: Upload → Extract → Chunk → Embed → Evaluate → Report."""

from __future__ import annotations

import json
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.evaluation.dqc_engine import DQCEngine, load_dqc_checklist
from src.ingestion.extractor_factory import extract_document
from src.logger import get_logger
from src.models.dqc import DQCChecklist
from src.models.document import ExtractedContent
from src.models.report import ComplianceReport, DocumentInfo
from src.preprocessing.chunker import chunk_document
from src.reporting.json_reporter import save_json_report
from src.reporting.pdf_reporter import generate_pdf_report
from src.retrieval.retriever import RetrievalEngine
from src.vectorstore.chroma_store import VectorStore
from src.audit.audit_logger import AuditLogger

logger = get_logger(__name__)


class PipelineStage(str, Enum):
    PENDING = "pending"
    INGESTION = "ingestion"
    PREPROCESSING = "preprocessing"
    EMBEDDING = "embedding"
    EVALUATION = "evaluation"
    AGGREGATION = "aggregation"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineState(BaseModel):
    """Tracks pipeline execution state."""

    doc_id: str = ""
    filename: str = ""
    stage: PipelineStage = PipelineStage.PENDING
    progress: float = 0.0  # 0–100
    errors: list[str] = Field(default_factory=list)
    stage_times: dict[str, float] = Field(default_factory=dict)
    report_id: str | None = None


class Pipeline:
    """Full orchestration pipeline — wires all components together."""

    def __init__(
        self,
        settings: Settings | None = None,
        on_progress: Callable[[PipelineState], None] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._on_progress = on_progress
        self.state = PipelineState()

        # Lazy-init heavy components
        self._vector_store: VectorStore | None = None
        self._retrieval_engine: RetrievalEngine | None = None
        self._dqc_engine: DQCEngine | None = None
        self._audit = AuditLogger(self._settings.audit_db_path)

    def _emit(self, stage: PipelineStage, progress: float) -> None:
        self.state.stage = stage
        self.state.progress = progress
        if self._on_progress:
            self._on_progress(self.state)

    def _init_components(self) -> None:
        if self._vector_store is None:
            self._vector_store = VectorStore(self._settings)
            self._retrieval_engine = RetrievalEngine(self._vector_store)
            self._dqc_engine = DQCEngine(self._retrieval_engine, self._settings)

    # ── Main pipeline ────────────────────────────────────────────

    def run(
        self,
        file_path: str | Path,
        dqc_path: str | Path | None = None,
        user: str = "system",
    ) -> ComplianceReport:
        """Execute the full pipeline end-to-end.

        Args:
            file_path: Path to the document to analyse.
            dqc_path: Path to the DQC checklist JSON. Defaults to sample_dqc.json.
            user: Identifier of the user triggering the analysis.

        Returns:
            ComplianceReport with all findings and metadata.
        """
        pipeline_start = time.time()
        self._init_components()

        assert self._vector_store is not None
        assert self._retrieval_engine is not None
        assert self._dqc_engine is not None

        file_path = Path(file_path)
        if dqc_path is None:
            dqc_path = Path(self._settings.dqc_dir) / "sample_dqc.json"
        dqc_path = Path(dqc_path)

        self.state.filename = file_path.name

        try:
            # ── Stage 1: Ingestion ───────────────────────────────
            self._emit(PipelineStage.INGESTION, 5)
            t0 = time.time()
            content: ExtractedContent = extract_document(file_path)
            self.state.doc_id = content.doc_id
            self.state.stage_times["ingestion"] = time.time() - t0

            if not content.is_valid:
                raise ValueError(
                    f"Extraction failed: {content.extraction_errors or 'no text extracted'}"
                )
            self._emit(PipelineStage.INGESTION, 15)

            # ── Stage 2: Preprocessing ───────────────────────────
            self._emit(PipelineStage.PREPROCESSING, 18)
            t0 = time.time()
            chunks = chunk_document(content)
            self.state.stage_times["preprocessing"] = time.time() - t0
            self._emit(PipelineStage.PREPROCESSING, 25)

            if not chunks:
                raise ValueError("Chunking produced no chunks")

            # ── Stage 3: Embedding ───────────────────────────────
            self._emit(PipelineStage.EMBEDDING, 28)
            t0 = time.time()
            # Remove old chunks for this doc if re-processing
            self._vector_store.delete_by_doc_id(content.doc_id)
            self._vector_store.add_chunks(chunks)
            self.state.stage_times["embedding"] = time.time() - t0
            self._emit(PipelineStage.EMBEDDING, 40)

            # ── Stage 4: Evaluation ──────────────────────────────
            self._emit(PipelineStage.EVALUATION, 42)
            t0 = time.time()
            checklist: DQCChecklist = load_dqc_checklist(dqc_path)
            doc_info = DocumentInfo(
                id=content.doc_id,
                filename=content.filename,
                pages=content.metadata.page_count,
                version=content.version,
            )
            report: ComplianceReport = self._dqc_engine.evaluate_checklist(
                checklist=checklist,
                doc_id=content.doc_id,
                doc_info=doc_info,
            )
            self.state.stage_times["evaluation"] = time.time() - t0
            self._emit(PipelineStage.EVALUATION, 85)

            # ── Stage 5: Reporting ───────────────────────────────
            self._emit(PipelineStage.REPORTING, 90)
            t0 = time.time()

            report.audit.processing_time_seconds = round(time.time() - pipeline_start, 2)
            report.audit.user = user

            # Save JSON report
            json_path = save_json_report(report, self._settings.report_dir)

            # Save PDF report
            pdf_path = generate_pdf_report(report, self._settings.report_dir)

            self.state.stage_times["reporting"] = time.time() - t0
            self.state.report_id = report.report_id

            # ── Audit log ────────────────────────────────────────
            self._audit.log_evaluation(report, content.doc_id, user)

            self._emit(PipelineStage.COMPLETED, 100)
            logger.info(
                "Pipeline complete",
                report_id=report.report_id,
                score=report.overall_compliance.score,
                total_time=report.audit.processing_time_seconds,
                tokens=report.audit.total_tokens_used,
            )
            return report

        except Exception as exc:
            self.state.errors.append(str(exc))
            self._emit(PipelineStage.FAILED, self.state.progress)
            logger.error("Pipeline failed", error=str(exc), stage=self.state.stage.value)
            raise
