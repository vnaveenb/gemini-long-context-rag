"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getHealth, listDocuments, listReports } from "@/lib/api";
import type { HealthResponse, DocumentEntry, ReportListEntry } from "@/types/api";
import { StatsCard } from "@/components/StatsCard";

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [docs, setDocs] = useState<DocumentEntry[]>([]);
  const [reports, setReports] = useState<ReportListEntry[]>([]);

  useEffect(() => {
    Promise.allSettled([getHealth(), listDocuments(), listReports()]).then(
      ([h, d, r]) => {
        if (h.status === "fulfilled") setHealth(h.value);
        if (d.status === "fulfilled") setDocs(d.value.documents);
        if (r.status === "fulfilled") setReports(r.value.reports);
      }
    );
  }, []);

  const scoreColor = (s: number) =>
    s >= 80 ? "text-green-600" : s >= 50 ? "text-yellow-600" : "text-red-600";

  return (
    <>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <StatsCard
          icon="📄"
          label="Documents"
          value={docs.length}
          subtext="uploaded"
        />
        <StatsCard
          icon="📊"
          label="Reports"
          value={reports.length}
          subtext="generated"
        />
        <StatsCard
          icon={health?.status === "healthy" ? "🟢" : "🔴"}
          label="API"
          value={health?.status ?? "…"}
          subtext={health ? `v${health.version}` : ""}
        />
      </div>

      {/* Recent reports */}
      <h2 className="text-lg font-semibold mb-3">Recent Reports</h2>
      {reports.length === 0 ? (
        <p className="text-[var(--muted)]">
          No reports yet.{" "}
          <Link href="/upload" className="text-[var(--accent)] underline">
            Upload a document
          </Link>{" "}
          to get started.
        </p>
      ) : (
        <div className="rounded-lg border border-[var(--border)] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-white/5 text-left">
              <tr>
                <th className="px-4 py-2 font-medium">Document</th>
                <th className="px-4 py-2 font-medium">Score</th>
                <th className="px-4 py-2 font-medium">Date</th>
                <th className="px-4 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {reports.slice(0, 10).map((r) => (
                <tr
                  key={r.report_id}
                  className="border-t border-[var(--border)] hover:bg-gray-50 dark:hover:bg-white/5"
                >
                  <td className="px-4 py-2 truncate max-w-[200px]">
                    {r.filename}
                  </td>
                  <td className={`px-4 py-2 font-semibold ${scoreColor(r.score ?? 0)}`}>
                    {r.score ?? 0}%
                  </td>
                  <td className="px-4 py-2 text-[var(--muted)]">
                    {r.generated_at ? new Date(r.generated_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <Link
                      href={`/reports/${r.report_id}`}
                      className="text-[var(--accent)] hover:underline"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
