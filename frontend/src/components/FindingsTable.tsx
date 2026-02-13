import type { DQCEvaluationResult } from "@/types/api";

interface FindingsTableProps {
  findings: DQCEvaluationResult[];
}

const STATUS_BADGE: Record<string, string> = {
  Pass: "bg-green-100 text-green-800",
  Fail: "bg-red-100 text-red-800",
  Partial: "bg-yellow-100 text-yellow-800",
};

const RISK_BADGE: Record<string, string> = {
  Critical: "bg-red-600 text-white",
  High: "bg-orange-500 text-white",
  Medium: "bg-yellow-400 text-black",
  Low: "bg-green-200 text-green-900",
};

export function FindingsTable({ findings }: FindingsTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
            <th className="py-3 px-3 font-medium">ID</th>
            <th className="py-3 px-3 font-medium">Status</th>
            <th className="py-3 px-3 font-medium">Risk</th>
            <th className="py-3 px-3 font-medium">Confidence</th>
            <th className="py-3 px-3 font-medium">Justification</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((f) => (
            <tr
              key={f.dqc_item_id}
              className="border-b border-[var(--border)] hover:bg-[var(--border)]/40 transition-colors"
            >
              <td className="py-3 px-3 font-mono text-xs">{f.dqc_item_id}</td>
              <td className="py-3 px-3">
                <span
                  className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                    STATUS_BADGE[f.status] ?? ""
                  }`}
                >
                  {f.status}
                </span>
              </td>
              <td className="py-3 px-3">
                <span
                  className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                    RISK_BADGE[f.risk_level] ?? ""
                  }`}
                >
                  {f.risk_level}
                </span>
              </td>
              <td className="py-3 px-3">{(f.confidence_score * 100).toFixed(0)}%</td>
              <td className="py-3 px-3 max-w-md">
                <p className="line-clamp-2">{f.justification}</p>
                {f.evidence_quotes.length > 0 && (
                  <details className="mt-1">
                    <summary className="text-xs text-[var(--accent)] cursor-pointer">
                      Evidence ({f.evidence_quotes.length})
                    </summary>
                    <ul className="mt-1 space-y-1 text-xs text-[var(--muted)]">
                      {f.evidence_quotes.map((q, i) => (
                        <li key={i} className="italic border-l-2 border-[var(--accent)] pl-2">
                          &ldquo;{q}&rdquo;
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
