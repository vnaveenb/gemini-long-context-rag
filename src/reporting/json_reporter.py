"""JSON report generator — saves structured compliance report to disk."""

from __future__ import annotations

import json
from pathlib import Path

from src.logger import get_logger
from src.models.report import ComplianceReport

logger = get_logger(__name__)


def save_json_report(report: ComplianceReport, output_dir: str | Path) -> Path:
    """Serialize and save the compliance report as JSON.

    Returns the path to the saved file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"report_{report.report_id}.json"
    path = output_dir / filename

    data = report.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    logger.info("JSON report saved", path=str(path))
    return path
