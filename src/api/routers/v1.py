"""API v1 router — all /api/v1/* endpoints including WebSocket progress."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from src.api.schemas import (
    AnalysisStartRequest,
    AnalysisStartResponse,
    AuditListResponse,
    AuditRecord,
    DocumentEntry,
    DocumentListResponse,
    HealthResponse,
    JobStatusResponse,
    ReportDetailResponse,
    ReportListEntry,
    ReportListResponse,
    UploadResponse,
    WSProgressMessage,
)
from src.config import get_settings
from src.logger import get_logger
from src.orchestration.orchestrator import Pipeline, PipelineState

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1", tags=["v1"])

# ── In-memory state (MVP — swap to Redis/DB for production) ──────────────────

_jobs: dict[str, PipelineState] = {}
_reports: dict[str, dict] = {}  # report_id → {json_path, pdf_path, report}
_job_queues: dict[str, asyncio.Queue] = {}  # job_id → queue for WS subscribers


# ── Document Upload ──────────────────────────────────────────────────────────


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document for analysis."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".docx", ".pptx", ".xlsx"}:
        raise HTTPException(400, f"Unsupported format: {ext}")

    doc_id = uuid.uuid4().hex[:12]
    save_path = Path(settings.upload_dir) / f"{doc_id}_{file.filename}"
    content = await file.read()
    save_path.write_bytes(content)

    logger.info("Document uploaded", doc_id=doc_id, filename=file.filename, size=len(content))

    return UploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        path=str(save_path),
        size_bytes=len(content),
    )


# ── List Documents ───────────────────────────────────────────────────────────


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """List uploaded documents."""
    upload_dir = Path(settings.upload_dir)
    files: list[DocumentEntry] = []
    if upload_dir.exists():
        for f in sorted(upload_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file() and f.suffix.lower() in {".pdf", ".docx", ".pptx", ".xlsx"}:
                # Extract doc_id from filename pattern: {doc_id}_{original_name}
                name_parts = f.name.split("_", 1)
                doc_id = name_parts[0] if len(name_parts) > 1 else f.stem
                stat = f.stat()
                files.append(
                    DocumentEntry(
                        doc_id=doc_id,
                        filename=f.name,
                        size_bytes=stat.st_size,
                        path=str(f),
                        uploaded_at=datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ).isoformat(),
                    )
                )
    return DocumentListResponse(documents=files)


# ── Start Analysis ───────────────────────────────────────────────────────────


def _run_pipeline(job_id: str, file_path: str, dqc_path: str | None, user: str, google_api_key: str | None = None) -> None:
    """Background task that runs the full pipeline."""
    try:

        def on_progress(state: PipelineState) -> None:
            _jobs[job_id] = state
            # Push to WebSocket queue if anyone is listening
            queue = _job_queues.get(job_id)
            if queue is not None:
                msg = WSProgressMessage(
                    job_id=job_id,
                    stage=state.stage.value,
                    progress=state.progress,
                    errors=state.errors,
                    report_id=state.report_id,
                    filename=state.filename,
                )
                try:
                    queue.put_nowait(msg)
                except asyncio.QueueFull:
                    pass  # Drop oldest if queue is full

        pipeline = Pipeline(on_progress=on_progress, google_api_key_override=google_api_key)
        report = pipeline.run(file_path=file_path, dqc_path=dqc_path, user=user)

        _reports[report.report_id] = {
            "json_path": str(Path(settings.report_dir) / f"report_{report.report_id}.json"),
            "pdf_path": str(Path(settings.report_dir) / f"report_{report.report_id}.pdf"),
            "report": report.model_dump(mode="json"),
        }
        if job_id in _jobs:
            _jobs[job_id].report_id = report.report_id

    except Exception as exc:
        logger.error("Pipeline background job failed", job_id=job_id, error=str(exc))
        if job_id in _jobs:
            _jobs[job_id].errors.append(str(exc))


@router.post("/analysis/start", response_model=AnalysisStartResponse)
async def start_analysis(
    body: AnalysisStartRequest,
    background_tasks: BackgroundTasks,
    x_gemini_api_key: str | None = Header(None),
):
    """Start a DQC analysis pipeline in the background."""
    if not Path(body.file_path).exists():
        raise HTTPException(404, f"File not found: {body.file_path}")

    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = PipelineState(filename=Path(body.file_path).name)

    # Create WS queue for this job
    _job_queues[job_id] = asyncio.Queue(maxsize=100)

    background_tasks.add_task(
        _run_pipeline, job_id, body.file_path, body.dqc_path, body.user, x_gemini_api_key
    )

    return AnalysisStartResponse(job_id=job_id, status="started")


# ── Analysis Status (HTTP polling fallback) ──────────────────────────────────


@router.get("/analysis/{job_id}/status", response_model=JobStatusResponse)
async def analysis_status(job_id: str):
    """Check pipeline progress (polling)."""
    state = _jobs.get(job_id)
    if not state:
        raise HTTPException(404, "Job not found")
    return JobStatusResponse(
        job_id=job_id,
        stage=state.stage.value,
        progress=state.progress,
        errors=state.errors,
        report_id=state.report_id,
        filename=state.filename,
        stage_times=state.stage_times,
    )


# ── WebSocket for real-time progress ─────────────────────────────────────────


@router.websocket("/analysis/{job_id}/ws")
async def analysis_ws(websocket: WebSocket, job_id: str):
    """WebSocket endpoint that pushes pipeline progress updates in real time."""
    await websocket.accept()

    queue = _job_queues.get(job_id)
    if queue is None:
        await websocket.send_json({"type": "error", "message": "Job not found"})
        await websocket.close()
        return

    try:
        while True:
            try:
                msg: WSProgressMessage = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(msg.model_dump())

                # Close when pipeline is done
                if msg.stage in ("completed", "failed"):
                    await websocket.close()
                    break
            except asyncio.TimeoutError:
                # Send a heartbeat to keep connection alive
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        logger.debug("WS client disconnected", job_id=job_id)
    finally:
        # Clean up queue after connection ends
        _job_queues.pop(job_id, None)


# ── Report Endpoints ─────────────────────────────────────────────────────────


@router.get("/reports", response_model=ReportListResponse)
async def list_reports():
    """List all generated reports with summary info."""
    report_dir = Path(settings.report_dir)
    reports: list[ReportListEntry] = []
    for f in sorted(report_dir.glob("report_*.json"), reverse=True):
        report_id = f.stem.replace("report_", "")
        entry = ReportListEntry(report_id=report_id, filename=f.name)

        # Enrich with score + date from in-memory cache or file
        cached = _reports.get(report_id)
        if cached and cached.get("report"):
            entry.score = cached["report"].get("overall_compliance", {}).get("score")
            entry.generated_at = cached["report"].get("generated_at")
        else:
            try:
                data = json.loads(f.read_text())
                entry.score = data.get("overall_compliance", {}).get("score")
                entry.generated_at = data.get("generated_at")
            except Exception:
                pass

        reports.append(entry)
    return ReportListResponse(reports=reports)


@router.get("/reports/{report_id}", response_model=ReportDetailResponse)
async def get_report_detail(report_id: str):
    """Get full report data as JSON for in-app display."""
    # Try in-memory cache first
    cached = _reports.get(report_id)
    if cached and cached.get("report"):
        return cached["report"]

    # Fall back to disk
    path = Path(settings.report_dir) / f"report_{report_id}.json"
    if not path.exists():
        raise HTTPException(404, "Report not found")
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        raise HTTPException(500, f"Failed to read report: {exc}")


@router.get("/reports/{report_id}/json")
async def download_report_json(report_id: str):
    """Download JSON report file."""
    path = Path(settings.report_dir) / f"report_{report_id}.json"
    if not path.exists():
        raise HTTPException(404, "Report not found")
    return FileResponse(path, media_type="application/json", filename=path.name)


@router.get("/reports/{report_id}/pdf")
async def download_report_pdf(report_id: str):
    """Download PDF report file."""
    path = Path(settings.report_dir) / f"report_{report_id}.pdf"
    if not path.exists():
        raise HTTPException(404, "Report not found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


# ── Audit ────────────────────────────────────────────────────────────────────


def _get_audit_logger():
    from src.audit.audit_logger import AuditLogger
    return AuditLogger(settings.audit_db_path)


@router.get("/audit/recent", response_model=AuditListResponse)
async def audit_recent(limit: int = 20):
    """Get recent audit records."""
    audit = _get_audit_logger()
    records = audit.query_recent(limit)
    return AuditListResponse(
        records=[AuditRecord(**{k: v for k, v in r.items() if k != "result_json"}) for r in records]
    )


@router.get("/audit/document/{doc_id}", response_model=AuditListResponse)
async def audit_by_document(doc_id: str):
    """Get audit records for a specific document."""
    audit = _get_audit_logger()
    records = audit.query_by_doc(doc_id)
    return AuditListResponse(
        records=[AuditRecord(**{k: v for k, v in r.items() if k != "result_json"}) for r in records]
    )


@router.get("/audit/user/{user_id}", response_model=AuditListResponse)
async def audit_by_user(user_id: str):
    """Get audit records for a specific user."""
    audit = _get_audit_logger()
    records = audit.query_by_user(user_id)
    return AuditListResponse(
        records=[AuditRecord(**{k: v for k, v in r.items() if k != "result_json"}) for r in records]
    )
