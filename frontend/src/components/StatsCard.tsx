interface StatsCardProps {
  icon: string;
  label: string;
  value: string | number;
  subtext?: string;
}

export function StatsCard({ icon, label, value, subtext }: StatsCardProps) {
  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 flex items-start gap-4">
      <span className="text-3xl">{icon}</span>
      <div>
        <p className="text-sm text-[var(--muted)]">{label}</p>
        <p className="text-2xl font-bold mt-0.5">{value}</p>
        {subtext && <p className="text-xs text-[var(--muted)] mt-1">{subtext}</p>}
      </div>
    </div>
  );
}
