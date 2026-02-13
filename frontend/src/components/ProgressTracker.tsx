import type { PipelineStage } from "@/types/api";

interface ProgressTrackerProps {
  stage: PipelineStage;
  progress: number;
  errors: string[];
}

const STAGE_LABELS: Record<PipelineStage, string> = {
  pending: "Pending",
  ingestion: "Extracting document…",
  preprocessing: "Chunking text…",
  embedding: "Generating embeddings…",
  evaluation: "Evaluating compliance…",
  aggregation: "Aggregating results…",
  reporting: "Generating report…",
  completed: "Complete!",
  failed: "Failed",
};

export function ProgressTracker({ stage, progress, errors }: ProgressTrackerProps) {
  const pct = Math.min(Math.max(progress, 0), 100);
  const done = stage === "completed";
  const failed = stage === "failed";

  return (
    <div className="space-y-3">
      {/* Bar */}
      <div className="h-3 bg-[var(--border)] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            failed
              ? "bg-[var(--danger)]"
              : done
              ? "bg-[var(--success)]"
              : "bg-[var(--accent)]"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Label */}
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">
          {STAGE_LABELS[stage] ?? stage}
        </span>
        <span className="text-[var(--muted)]">{pct.toFixed(0)}%</span>
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {errors.map((e, i) => (
            <p key={i}>{e}</p>
          ))}
        </div>
      )}
    </div>
  );
}
