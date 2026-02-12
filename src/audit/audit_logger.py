"""Audit logging — SQLite-backed audit trail for every evaluation."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.logger import get_logger
from src.models.report import ComplianceReport

logger = get_logger(__name__)

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id       TEXT PRIMARY KEY,
    evaluation_id  TEXT NOT NULL,
    doc_id         TEXT NOT NULL,
    filename       TEXT,
    dqc_version    TEXT,
    model_version  TEXT,
    embedding_model TEXT,
    prompt_version TEXT,
    total_tokens   INTEGER,
    score          REAL,
    passed         INTEGER,
    failed         INTEGER,
    partial        INTEGER,
    processing_time REAL,
    user_id        TEXT,
    result_json    TEXT,
    timestamp      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_doc ON audit_log(doc_id);
CREATE INDEX IF NOT EXISTS idx_audit_ts  ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
"""


class AuditLogger:
    """SQLite-based audit logger for compliance evaluations."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_CREATE_TABLE)
        logger.debug("Audit DB initialised", path=self._db_path)

    def log_evaluation(
        self,
        report: ComplianceReport,
        doc_id: str,
        user: str,
    ) -> None:
        """Write a full audit record for a completed evaluation."""
        import uuid

        audit_id = uuid.uuid4().hex
        result_json = report.model_dump_json()

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_log (
                    audit_id, evaluation_id, doc_id, filename, dqc_version,
                    model_version, embedding_model, prompt_version,
                    total_tokens, score, passed, failed, partial,
                    processing_time, user_id, result_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    report.report_id,
                    doc_id,
                    report.document.filename,
                    report.dqc_version,
                    report.audit.model_version,
                    report.audit.embedding_model,
                    report.audit.prompt_version,
                    report.audit.total_tokens_used,
                    report.overall_compliance.score,
                    report.overall_compliance.passed,
                    report.overall_compliance.failed,
                    report.overall_compliance.partial,
                    report.audit.processing_time_seconds,
                    user,
                    result_json,
                    datetime.utcnow().isoformat(),
                ),
            )
        logger.info("Audit record saved", audit_id=audit_id, doc_id=doc_id)

    def query_by_doc(self, doc_id: str) -> list[dict[str, Any]]:
        """Retrieve audit records for a specific document."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE doc_id = ? ORDER BY timestamp DESC", (doc_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def query_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve the most recent audit records."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def query_by_user(self, user_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE user_id = ? ORDER BY timestamp DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]
