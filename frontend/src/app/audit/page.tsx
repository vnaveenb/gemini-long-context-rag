"use client";

import { useEffect, useState } from "react";
import { getRecentAudit } from "@/lib/api";
import type { AuditRecord } from "@/types/api";

export default function AuditPage() {
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRecentAudit(50)
      .then((r) => setRecords(r.records))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-[var(--muted)]">Loading audit log…</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Audit Trail</h1>

      {records.length === 0 ? (
        <p className="text-[var(--muted)]">No audit records found.</p>
      ) : (
        <div className="overflow-x-auto bg-[var(--card)] border border-[var(--border)] rounded-xl">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="py-3 px-4 font-medium">Timestamp</th>
                <th className="py-3 px-4 font-medium">File</th>
                <th className="py-3 px-4 font-medium">Score</th>
                <th className="py-3 px-4 font-medium">P / F / Pr</th>
                <th className="py-3 px-4 font-medium">Tokens</th>
                <th className="py-3 px-4 font-medium">Time</th>
                <th className="py-3 px-4 font-medium">Model</th>
                <th className="py-3 px-4 font-medium">User</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr
                  key={r.audit_id}
                  className="border-b border-[var(--border)] hover:bg-[var(--border)]/40 transition-colors"
                >
                  <td className="py-3 px-4 text-xs">
                    {r.timestamp
                      ? new Date(r.timestamp).toLocaleString()
                      : "—"}
                  </td>
                  <td className="py-3 px-4">{r.filename ?? "—"}</td>
                  <td className="py-3 px-4 font-bold">
                    {r.score != null ? (
                      <span
                        className={
                          r.score >= 80
                            ? "text-[var(--success)]"
                            : r.score >= 50
                            ? "text-[var(--warning)]"
                            : "text-[var(--danger)]"
                        }
                      >
                        {r.score.toFixed(1)}%
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="py-3 px-4 font-mono text-xs">
                    <span className="text-[var(--success)]">{r.passed ?? 0}</span>
                    {" / "}
                    <span className="text-[var(--danger)]">{r.failed ?? 0}</span>
                    {" / "}
                    <span className="text-[var(--warning)]">{r.partial ?? 0}</span>
                  </td>
                  <td className="py-3 px-4 text-xs">
                    {r.total_tokens?.toLocaleString() ?? "—"}
                  </td>
                  <td className="py-3 px-4 text-xs">
                    {r.processing_time != null
                      ? `${r.processing_time.toFixed(1)}s`
                      : "—"}
                  </td>
                  <td className="py-3 px-4 text-xs font-mono">
                    {r.model_version ?? "—"}
                  </td>
                  <td className="py-3 px-4 text-xs">{r.user_id ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
