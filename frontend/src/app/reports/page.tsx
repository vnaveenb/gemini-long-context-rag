"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listReports, reportJsonUrl, reportPdfUrl } from "@/lib/api";
import type { ReportListEntry } from "@/types/api";

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportListEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listReports()
      .then((r) => setReports(r.reports))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-[var(--muted)]">Loading reports…</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Compliance Reports</h1>

      {reports.length === 0 ? (
        <p className="text-[var(--muted)]">
          No reports available yet. Upload a document to generate one.
        </p>
      ) : (
        <div className="grid gap-4">
          {reports.map((r) => (
            <div
              key={r.report_id}
              className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 flex items-center justify-between"
            >
              <div className="space-y-1">
                <Link
                  href={`/reports/${r.report_id}`}
                  className="font-medium hover:text-[var(--accent)] transition-colors"
                >
                  {r.report_id}
                </Link>
                <p className="text-sm text-[var(--muted)]">{r.filename}</p>
                {r.generated_at && (
                  <p className="text-xs text-[var(--muted)]">
                    {new Date(r.generated_at).toLocaleString()}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-4">
                {r.score != null && (
                  <span
                    className={`text-lg font-bold ${
                      r.score >= 80
                        ? "text-[var(--success)]"
                        : r.score >= 50
                        ? "text-[var(--warning)]"
                        : "text-[var(--danger)]"
                    }`}
                  >
                    {r.score.toFixed(1)}%
                  </span>
                )}
                <div className="flex gap-2">
                  <a
                    href={reportJsonUrl(r.report_id)}
                    download
                    className="px-3 py-1.5 text-xs font-medium border border-[var(--border)] rounded-lg hover:bg-[var(--border)]/40 transition-colors"
                  >
                    JSON
                  </a>
                  <a
                    href={reportPdfUrl(r.report_id)}
                    download
                    className="px-3 py-1.5 text-xs font-medium border border-[var(--border)] rounded-lg hover:bg-[var(--border)]/40 transition-colors"
                  >
                    PDF
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
