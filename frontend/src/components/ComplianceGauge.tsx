interface ComplianceGaugeProps {
  score: number;
  size?: "sm" | "lg";
}

export function ComplianceGauge({ score, size = "lg" }: ComplianceGaugeProps) {
  const color =
    score >= 80
      ? "text-[var(--success)]"
      : score >= 50
      ? "text-[var(--warning)]"
      : "text-[var(--danger)]";

  const dim = size === "lg" ? "w-32 h-32" : "w-20 h-20";
  const textSize = size === "lg" ? "text-3xl" : "text-lg";

  // SVG circle parameters
  const r = size === "lg" ? 56 : 34;
  const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;

  return (
    <div className={`relative ${dim} flex items-center justify-center`}>
      <svg className="absolute inset-0 -rotate-90" viewBox="0 0 128 128">
        <circle
          cx="64"
          cy="64"
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth="8"
        />
        <circle
          cx="64"
          cy="64"
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          strokeDasharray={c}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={`${color} transition-all duration-700`}
        />
      </svg>
      <span className={`${textSize} font-bold ${color}`}>
        {score.toFixed(0)}%
      </span>
    </div>
  );
}
