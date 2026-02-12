"""PDF report generator using ReportLab."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.logger import get_logger
from src.models.dqc import DQCStatus, RiskLevel
from src.models.report import ComplianceReport

logger = get_logger(__name__)

_RISK_COLORS = {
    RiskLevel.CRITICAL: colors.HexColor("#D32F2F"),
    RiskLevel.HIGH: colors.HexColor("#F57C00"),
    RiskLevel.MEDIUM: colors.HexColor("#FBC02D"),
    RiskLevel.LOW: colors.HexColor("#388E3C"),
}

_STATUS_COLORS = {
    DQCStatus.PASS: colors.HexColor("#388E3C"),
    DQCStatus.FAIL: colors.HexColor("#D32F2F"),
    DQCStatus.PARTIAL: colors.HexColor("#F57C00"),
}


def generate_pdf_report(report: ComplianceReport, output_dir: str | Path) -> Path:
    """Generate a styled PDF compliance report.

    Returns the path to the saved file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"report_{report.report_id}.pdf"
    path = output_dir / filename

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]
    small_style = ParagraphStyle("Small", parent=body_style, fontSize=8, textColor=colors.grey)

    elements: list = []

    # ── Cover / Title ────────────────────────────────────────────
    elements.append(Paragraph("Compliance Report", title_style))
    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph(f"Document: {report.document.filename}", body_style))
    elements.append(
        Paragraph(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M')}", body_style)
    )
    elements.append(Paragraph(f"DQC Version: {report.dqc_version}", body_style))
    elements.append(Spacer(1, 10 * mm))

    # ── Executive Summary ────────────────────────────────────────
    elements.append(Paragraph("Executive Summary", heading_style))
    elements.append(Paragraph(report.executive_summary or "N/A", body_style))
    elements.append(Spacer(1, 8 * mm))

    # ── Score Card ───────────────────────────────────────────────
    elements.append(Paragraph("Overall Compliance", heading_style))
    c = report.overall_compliance
    score_data = [
        ["Score", "Passed", "Failed", "Partial", "Total Items"],
        [f"{c.score}%", str(c.passed), str(c.failed), str(c.partial), str(c.total_items)],
    ]
    score_table = Table(score_data, colWidths=[3 * cm] * 5)
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#E3F2FD")),
            ]
        )
    )
    elements.append(score_table)
    elements.append(Spacer(1, 5 * mm))

    # ── Risk Distribution ────────────────────────────────────────
    elements.append(Paragraph("Risk Distribution", heading_style))
    rd = c.risk_distribution
    risk_data = [
        ["Critical", "High", "Medium", "Low"],
        [str(rd.critical), str(rd.high), str(rd.medium), str(rd.low)],
    ]
    risk_table = Table(risk_data, colWidths=[3.5 * cm] * 4)
    risk_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, 0), _RISK_COLORS[RiskLevel.CRITICAL]),
                ("BACKGROUND", (1, 0), (1, 0), _RISK_COLORS[RiskLevel.HIGH]),
                ("BACKGROUND", (2, 0), (2, 0), _RISK_COLORS[RiskLevel.MEDIUM]),
                ("BACKGROUND", (3, 0), (3, 0), _RISK_COLORS[RiskLevel.LOW]),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
    )
    elements.append(risk_table)
    elements.append(Spacer(1, 10 * mm))

    # ── Detailed Findings ────────────────────────────────────────
    elements.append(Paragraph("Detailed Findings", heading_style))
    for finding in report.findings:
        status_color = _STATUS_COLORS.get(finding.status, colors.black)
        elements.append(
            Paragraph(
                f"<b>{finding.dqc_item_id}</b> — "
                f"<font color='{status_color.hexval()}'>{finding.status.value}</font> "
                f"(Risk: {finding.risk_level.value}, Confidence: {finding.confidence_score:.0%})",
                body_style,
            )
        )
        elements.append(
            Paragraph(f"<i>Justification:</i> {finding.justification}", body_style)
        )
        if finding.recommendation:
            elements.append(
                Paragraph(f"<i>Recommendation:</i> {finding.recommendation}", body_style)
            )
        elements.append(Spacer(1, 4 * mm))

    # ── Recommendations ──────────────────────────────────────────
    if report.recommendations:
        elements.append(Paragraph("Prioritised Recommendations", heading_style))
        for rec in report.recommendations:
            elements.append(
                Paragraph(
                    f"{rec.priority}. [{rec.dqc_item_id}] {rec.action} "
                    f"(Impact: {rec.risk_impact.value})",
                    body_style,
                )
            )
        elements.append(Spacer(1, 8 * mm))

    # ── Audit Metadata ───────────────────────────────────────────
    elements.append(Paragraph("Audit Metadata", heading_style))
    a = report.audit
    elements.append(Paragraph(f"LLM Model: {a.model_version}", small_style))
    elements.append(Paragraph(f"Embedding Model: {a.embedding_model}", small_style))
    elements.append(Paragraph(f"Prompt Version: {a.prompt_version}", small_style))
    elements.append(Paragraph(f"DQC Version: {a.dqc_version}", small_style))
    elements.append(Paragraph(f"Total Tokens: {a.total_tokens_used}", small_style))
    elements.append(Paragraph(f"Processing Time: {a.processing_time_seconds}s", small_style))
    elements.append(Paragraph(f"User: {a.user}", small_style))

    # Build PDF
    doc.build(elements)
    logger.info("PDF report saved", path=str(path))
    return path
