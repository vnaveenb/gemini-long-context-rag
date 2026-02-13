import type { RiskDistribution } from "@/types/api";

interface RiskChartProps {
  distribution: RiskDistribution;
}

const COLORS: { key: keyof RiskDistribution; label: string; bg: string }[] = [
  { key: "critical", label: "Critical", bg: "bg-red-600" },
  { key: "high", label: "High", bg: "bg-orange-500" },
  { key: "medium", label: "Medium", bg: "bg-yellow-400" },
  { key: "low", label: "Low", bg: "bg-green-400" },
];

export function RiskChart({ distribution }: RiskChartProps) {
  const total =
    distribution.critical +
    distribution.high +
    distribution.medium +
    distribution.low;

  if (total === 0) {
    return <p className="text-sm text-[var(--muted)]">No risk data available.</p>;
  }

  return (
    <div className="space-y-3">
      {COLORS.map(({ key, label, bg }) => {
        const count = distribution[key];
        const pct = (count / total) * 100;
        return (
          <div key={key}>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="font-medium">{label}</span>
              <span className="text-[var(--muted)]">
                {count} ({pct.toFixed(0)}%)
              </span>
            </div>
            <div className="h-2 bg-[var(--border)] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${bg} transition-all duration-500`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
