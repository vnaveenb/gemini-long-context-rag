"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getReportDetail, reportJsonUrl, reportPdfUrl } from "@/lib/api";
import { ComplianceGauge } from "@/components/ComplianceGauge";
import { FindingsTable } from "@/components/FindingsTable";
import { RiskChart } from "@/components/RiskChart";
import type { ReportDetail } from "@/types/api";

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getReportDetail(id)
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="text-[var(--muted)]">Loading report…</p>;
  if (error)
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
        {error}
      </div>
    );
  if (!report) return null;

  const { overall_compliance: comp } = report;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            href="/reports"
            className="text-sm text-[var(--accent)] hover:underline"
          >
            ← Back to Reports
          </Link>
          <h1 className="text-2xl font-bold mt-1">
            Report: {report.report_id}
          </h1>
          <p className="text-sm text-[var(--muted)]">
            {report.document.filename} · {report.document.pages} pages ·{" "}
            {new Date(report.generated_at).toLocaleString()}
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={reportJsonUrl(report.report_id)}
            download
            className="px-4 py-2 text-sm font-medium border border-[var(--border)] rounded-lg hover:bg-[var(--border)]/40"
          >
            📥 JSON
          </a>
          <a
            href={reportPdfUrl(report.report_id)}
            download
            className="px-4 py-2 text-sm font-medium bg-[var(--accent)] text-white rounded-lg hover:bg-[var(--accent-hover)]"
          >
            📥 PDF
          </a>
        </div>
      </div>

      {/* Score + Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Gauge */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-6 flex flex-col items-center justify-center">
          <ComplianceGauge score={comp.score} />
          <p className="text-sm font-medium mt-3">Compliance Score</p>
        </div>

        {/* Summary stats */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-6 space-y-3">
          <h3 className="font-semibold text-sm text-[var(--muted)] uppercase tracking-wide">
            Item Results
          </h3>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <p className="text-2xl font-bold text-[var(--success)]">{comp.passed}</p>
              <p className="text-xs text-[var(--muted)]">Passed</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-[var(--danger)]">{comp.failed}</p>
              <p className="text-xs text-[var(--muted)]">Failed</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-[var(--warning)]">{comp.partial}</p>
              <p className="text-xs text-[var(--muted)]">Partial</p>
            </div>
          </div>
          <p className="text-xs text-[var(--muted)] text-center pt-1">
            {comp.total_items} total items evaluated
          </p>
        </div>

        {/* Risk Distribution */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-6">
          <h3 className="font-semibold text-sm text-[var(--muted)] uppercase tracking-wide mb-3">
            Risk Distribution
          </h3>
          <RiskChart distribution={comp.risk_distribution} />
        </div>
      </div>

      {/* Executive Summary */}
      {report.executive_summary && (
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-6">
          <h2 className="font-semibold mb-2">Executive Summary</h2>
          <p className="text-sm leading-relaxed whitespace-pre-line">
            {report.executive_summary}
          </p>
        </div>
      )}

      {/* Findings Table */}
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-6">
        <h2 className="font-semibold mb-4">Detailed Findings</h2>
        <FindingsTable findings={report.findings} />
      </div>

      {/* Recommendations */}
      {report.recommendations.length > 0 && (
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-6">
          <h2 className="font-semibold mb-4">Prioritised Recommendations</h2>
          <div className="space-y-3">
            {report.recommendations.map((rec, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 rounded-lg bg-[var(--background)]"
              >
                <span className="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-full bg-[var(--accent)] text-white text-xs font-bold">
                  {rec.priority}
                </span>
                <div>
                  <p className="text-sm font-medium">
                    <span className="font-mono text-xs text-[var(--muted)] mr-2">
                      {rec.dqc_item_id}
                    </span>
                    {rec.action}
                  </p>
                  <span
                    className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                      rec.risk_impact === "Critical"
                        ? "bg-red-600 text-white"
                        : rec.risk_impact === "High"
                        ? "bg-orange-500 text-white"
                        : rec.risk_impact === "Medium"
                        ? "bg-yellow-400 text-black"
                        : "bg-green-200 text-green-900"
                    }`}
                  >
                    {rec.risk_impact}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Audit Metadata */}
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-6">
        <h2 className="font-semibold mb-3">Audit Metadata</h2>
        <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          {[
            ["Model", report.audit.model_version],
            ["Embedding", report.audit.embedding_model],
            ["Prompt", report.audit.prompt_version],
            ["DQC Version", report.audit.dqc_version],
            ["Tokens Used", report.audit.total_tokens_used.toLocaleString()],
            ["Processing", `${report.audit.processing_time_seconds.toFixed(1)}s`],
            ["User", report.audit.user || "—"],
          ].map(([label, val]) => (
            <div key={label}>
              <dt className="text-[var(--muted)]">{label}</dt>
              <dd className="font-medium">{val}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
