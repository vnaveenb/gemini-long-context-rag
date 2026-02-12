"""DQC Evaluation Engine — uses LangChain LCEL chains for provider-agnostic evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from src.config import Settings, get_settings
from src.llm.callbacks import TokenTrackingCallback
from src.llm.factory import get_llm
from src.logger import get_logger
from src.models.dqc import (
    DQCChecklist,
    DQCEvaluationResult,
    DQCItem,
    DQCStatus,
    RiskLevel,
)
from src.models.report import (
    AuditInfo,
    ComplianceReport,
    ComplianceSummary,
    DocumentInfo,
    Recommendation,
    RiskDistribution,
)
from src.evaluation.output_parsers import evaluation_parser
from src.evaluation.prompt_templates import EVALUATION_PROMPT, SUMMARY_PROMPT
from src.retrieval.retriever import RetrievalEngine, RetrievalResult

logger = get_logger(__name__)

PROMPT_VERSION = "v1.0"


def _risk_level(status: DQCStatus, confidence: float) -> RiskLevel:
    """Compute risk level from the scoring matrix."""
    if status == DQCStatus.FAIL:
        if confidence >= 0.8:
            return RiskLevel.CRITICAL
        if confidence >= 0.5:
            return RiskLevel.HIGH
        return RiskLevel.MEDIUM
    if status == DQCStatus.PARTIAL:
        if confidence >= 0.8:
            return RiskLevel.HIGH
        if confidence >= 0.5:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
    # Pass
    if confidence < 0.5:
        return RiskLevel.LOW
    return RiskLevel.LOW


class DQCEngine:
    """Evaluates documents against a DQC checklist using LangChain chains."""

    def __init__(
        self,
        retrieval_engine: RetrievalEngine,
        settings: Settings | None = None,
        llm: BaseChatModel | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or get_llm(self._settings)
        self._retrieval = retrieval_engine
        self._token_tracker = TokenTrackingCallback()

        # LCEL evaluation chain: prompt → LLM → parse
        self._eval_chain = EVALUATION_PROMPT | self._llm | evaluation_parser

        # Summary chain
        self._summary_chain = SUMMARY_PROMPT | self._llm | StrOutputParser()

    # ── Single item evaluation ───────────────────────────────────

    def evaluate_item(
        self,
        item: DQCItem,
        doc_id: str,
    ) -> DQCEvaluationResult:
        """Evaluate a single DQC item against the document."""
        # 1. Retrieve relevant context
        retrieval: RetrievalResult = self._retrieval.retrieve_for_dqc_item(
            requirement_text=f"{item.requirement}. {item.criteria}",
            doc_id=doc_id,
        )

        if not retrieval.chunks:
            logger.warning("No chunks retrieved", item_id=item.item_id)
            return DQCEvaluationResult(
                dqc_item_id=item.item_id,
                status=DQCStatus.FAIL,
                justification="No relevant content found in the document for this requirement.",
                risk_level=RiskLevel.HIGH,
                recommendation=f"Ensure the document addresses: {item.requirement}",
                confidence_score=0.3,
            )

        # 2. Invoke the LCEL chain
        try:
            result: DQCEvaluationResult = self._eval_chain.invoke(
                {
                    "dqc_item_id": item.item_id,
                    "category": item.category,
                    "requirement": item.requirement,
                    "criteria": item.criteria,
                    "retrieved_context": retrieval.context_text,
                    "format_instructions": evaluation_parser.get_format_instructions(),
                },
                config={"callbacks": [self._token_tracker]},
            )
        except Exception as exc:
            logger.error("Evaluation chain failed", item_id=item.item_id, error=str(exc))
            # Retry once with a simpler prompt (graceful degradation)
            try:
                result = self._eval_chain.invoke(
                    {
                        "dqc_item_id": item.item_id,
                        "category": item.category,
                        "requirement": item.requirement,
                        "criteria": item.criteria,
                        "retrieved_context": retrieval.context_text[:5000],
                        "format_instructions": evaluation_parser.get_format_instructions(),
                    },
                    config={"callbacks": [self._token_tracker]},
                )
            except Exception as retry_exc:
                logger.error("Retry also failed", item_id=item.item_id, error=str(retry_exc))
                return DQCEvaluationResult(
                    dqc_item_id=item.item_id,
                    status=DQCStatus.PARTIAL,
                    justification=f"Evaluation failed: {retry_exc}",
                    risk_level=RiskLevel.MEDIUM,
                    recommendation="Manual review required for this item.",
                    confidence_score=0.0,
                )

        # 3. Override risk level using our matrix
        result.risk_level = _risk_level(result.status, result.confidence_score)

        logger.info(
            "Item evaluated",
            item_id=item.item_id,
            status=result.status.value,
            risk=result.risk_level.value,
            confidence=result.confidence_score,
        )
        return result

    # ── Full checklist evaluation ────────────────────────────────

    def evaluate_checklist(
        self,
        checklist: DQCChecklist,
        doc_id: str,
        doc_info: DocumentInfo,
    ) -> ComplianceReport:
        """Evaluate all DQC items and produce a ComplianceReport."""
        logger.info(
            "Starting full DQC evaluation",
            doc_id=doc_id,
            dqc_version=checklist.version,
            items=len(checklist.items),
        )
        self._token_tracker.reset()

        findings: list[DQCEvaluationResult] = []
        for item in checklist.items:
            result = self.evaluate_item(item, doc_id)
            findings.append(result)

        # Aggregate
        passed = sum(1 for f in findings if f.status == DQCStatus.PASS)
        failed = sum(1 for f in findings if f.status == DQCStatus.FAIL)
        partial = sum(1 for f in findings if f.status == DQCStatus.PARTIAL)
        total = len(findings)

        score = round((passed / total) * 100, 1) if total else 0.0

        risk_dist = RiskDistribution(
            critical=sum(1 for f in findings if f.risk_level == RiskLevel.CRITICAL),
            high=sum(1 for f in findings if f.risk_level == RiskLevel.HIGH),
            medium=sum(1 for f in findings if f.risk_level == RiskLevel.MEDIUM),
            low=sum(1 for f in findings if f.risk_level == RiskLevel.LOW),
        )

        compliance = ComplianceSummary(
            score=score,
            total_items=total,
            passed=passed,
            failed=failed,
            partial=partial,
            risk_distribution=risk_dist,
        )

        # Generate recommendations from non-pass items, sorted by risk
        recommendations = self._build_recommendations(findings)

        # Generate executive summary
        executive_summary = self._generate_summary(
            doc_info.filename, score, passed, failed, partial, findings
        )

        report = ComplianceReport(
            document=doc_info,
            dqc_version=checklist.version,
            overall_compliance=compliance,
            executive_summary=executive_summary,
            findings=findings,
            recommendations=recommendations,
            audit=AuditInfo(
                model_version=self._settings.llm_model,
                embedding_model=self._settings.embedding_model,
                prompt_version=PROMPT_VERSION,
                dqc_version=checklist.version,
                total_tokens_used=self._token_tracker.total_tokens,
            ),
        )

        logger.info(
            "Evaluation complete",
            score=score,
            passed=passed,
            failed=failed,
            partial=partial,
            tokens=self._token_tracker.total_tokens,
        )
        return report

    # ── Helpers ──────────────────────────────────────────────────

    def _build_recommendations(
        self, findings: list[DQCEvaluationResult]
    ) -> list[Recommendation]:
        risk_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3}
        non_pass = [f for f in findings if f.status != DQCStatus.PASS and f.recommendation]
        non_pass.sort(key=lambda f: risk_order.get(f.risk_level, 99))

        return [
            Recommendation(
                priority=idx + 1,
                dqc_item_id=f.dqc_item_id,
                action=f.recommendation or "",
                risk_impact=f.risk_level,
            )
            for idx, f in enumerate(non_pass)
        ]

    def _generate_summary(
        self,
        filename: str,
        score: float,
        passed: int,
        failed: int,
        partial: int,
        findings: list[DQCEvaluationResult],
    ) -> str:
        findings_text = "\n".join(
            f"- {f.dqc_item_id}: {f.status.value} ({f.risk_level.value}) — {f.justification[:120]}"
            for f in findings
        )
        try:
            summary = self._summary_chain.invoke(
                {
                    "filename": filename,
                    "score": score,
                    "passed": passed,
                    "failed": failed,
                    "partial": partial,
                    "findings_text": findings_text,
                },
                config={"callbacks": [self._token_tracker]},
            )
            return summary.strip()
        except Exception as exc:
            logger.error("Summary generation failed", error=str(exc))
            return f"Compliance score: {score}%. {passed} passed, {failed} failed, {partial} partial."

    @property
    def token_usage(self) -> dict:
        return self._token_tracker.summary()


def load_dqc_checklist(path: str | Path) -> DQCChecklist:
    """Load a DQC checklist from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    return DQCChecklist(**data)
