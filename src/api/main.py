"""FastAPI application — main entry point."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from src.config import get_settings
from src.logger import get_logger, setup_logging
from src.orchestration.orchestrator import Pipeline, PipelineState

setup_logging()
logger = get_logger(__name__)
settings = get_settings()
settings.ensure_dirs()

# In-memory job tracking (MVP — swap to Redis/DB for production)
_jobs: dict[str, PipelineState] = {}
_reports: dict[str, dict] = {}  # report_id → {json_path, pdf_path, report}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LRA API starting", environment=settings.environment)
    yield
    logger.info("LRA API shutting down")


app = FastAPI(
    title="Learning Content Compliance Intelligence System",
    description="RAG-based DQC validation API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth dependency (API key) ────────────────────────────────────────────────


def _verify_api_key(api_key: str = "") -> None:
    """Simple API key check for MVP."""
    if settings.api_key and api_key != settings.api_key:
        # For MVP, skip strict enforcement if no key configured
        if settings.api_key != "":
            pass  # Accept all for now; tighten in production


# ── Health ───────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment}


# ── Document Upload ──────────────────────────────────────────────────────────


@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document for analysis."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".docx", ".pptx", ".xlsx"}:
        raise HTTPException(400, f"Unsupported format: {ext}")

    # Save to uploads dir
    doc_id = uuid.uuid4().hex[:12]
    save_path = Path(settings.upload_dir) / f"{doc_id}_{file.filename}"
    content = await file.read()
    save_path.write_bytes(content)

    logger.info("Document uploaded", doc_id=doc_id, filename=file.filename, size=len(content))

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "path": str(save_path),
        "size_bytes": len(content),
    }


# ── List Documents ───────────────────────────────────────────────────────────


@app.get("/api/v1/documents")
async def list_documents():
    """List uploaded documents."""
    upload_dir = Path(settings.upload_dir)
    files = []
    for f in upload_dir.iterdir():
        if f.is_file() and f.suffix.lower() in {".pdf", ".docx", ".pptx", ".xlsx"}:
            files.append({"filename": f.name, "size_bytes": f.stat().st_size, "path": str(f)})
    return {"documents": files}


# ── Start Analysis ───────────────────────────────────────────────────────────


def _run_pipeline(job_id: str, file_path: str, dqc_path: str | None, user: str) -> None:
    """Background task that runs the full pipeline."""
    try:
        def on_progress(state: PipelineState):
            _jobs[job_id] = state

        pipeline = Pipeline(on_progress=on_progress)
        report = pipeline.run(file_path=file_path, dqc_path=dqc_path, user=user)

        _reports[report.report_id] = {
            "json_path": str(Path(settings.report_dir) / f"report_{report.report_id}.json"),
            "pdf_path": str(Path(settings.report_dir) / f"report_{report.report_id}.pdf"),
            "report": report.model_dump(mode="json"),
        }
        # Update job with report_id
        if job_id in _jobs:
            _jobs[job_id].report_id = report.report_id

    except Exception as exc:
        logger.error("Pipeline background job failed", job_id=job_id, error=str(exc))
        if job_id in _jobs:
            _jobs[job_id].errors.append(str(exc))


@app.post("/api/v1/analysis/start")
async def start_analysis(
    background_tasks: BackgroundTasks,
    file_path: str,
    dqc_path: str | None = None,
    user: str = "api_user",
):
    """Start a DQC analysis pipeline in the background."""
    if not Path(file_path).exists():
        raise HTTPException(404, f"File not found: {file_path}")

    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = PipelineState(filename=Path(file_path).name)

    background_tasks.add_task(_run_pipeline, job_id, file_path, dqc_path, user)

    return {"job_id": job_id, "status": "started"}


# ── Analysis Status ──────────────────────────────────────────────────────────


@app.get("/api/v1/analysis/{job_id}/status")
async def analysis_status(job_id: str):
    """Check pipeline progress."""
    state = _jobs.get(job_id)
    if not state:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": job_id,
        "stage": state.stage.value,
        "progress": state.progress,
        "errors": state.errors,
        "report_id": state.report_id,
    }


# ── Report Endpoints ─────────────────────────────────────────────────────────


@app.get("/api/v1/reports/{report_id}/json")
async def get_report_json(report_id: str):
    """Download JSON report."""
    path = Path(settings.report_dir) / f"report_{report_id}.json"
    if not path.exists():
        raise HTTPException(404, "Report not found")
    return FileResponse(path, media_type="application/json", filename=path.name)


@app.get("/api/v1/reports/{report_id}/pdf")
async def get_report_pdf(report_id: str):
    """Download PDF report."""
    path = Path(settings.report_dir) / f"report_{report_id}.pdf"
    if not path.exists():
        raise HTTPException(404, "Report not found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@app.get("/api/v1/reports")
async def list_reports():
    """List all generated reports."""
    report_dir = Path(settings.report_dir)
    reports = []
    for f in sorted(report_dir.glob("report_*.json"), reverse=True):
        reports.append({"report_id": f.stem.replace("report_", ""), "filename": f.name})
    return {"reports": reports}


# ── Audit ────────────────────────────────────────────────────────────────────


@app.get("/api/v1/audit/recent")
async def audit_recent(limit: int = 20):
    """Get recent audit records."""
    from src.audit.audit_logger import AuditLogger

    audit = AuditLogger(settings.audit_db_path)
    return {"records": audit.query_recent(limit)}
