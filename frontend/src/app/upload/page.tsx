"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { FileDropzone } from "@/components/FileDropzone";
import { ProgressTracker } from "@/components/ProgressTracker";
import { useJobProgress } from "@/hooks/useJobProgress";
import { uploadDocument, startAnalysis } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const progress = useJobProgress(jobId);

  const handleAnalyse = useCallback(async () => {
    if (!file) return;
    setError(null);
    setUploading(true);

    try {
      // Step 1: Upload
      const upload = await uploadDocument(file);

      // Step 2: Start analysis
      const { job_id } = await startAnalysis({ file_path: upload.path });
      setJobId(job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  }, [file]);

  // Navigate to report when done
  if (progress.stage === "completed" && progress.reportId) {
    setTimeout(() => router.push(`/reports/${progress.reportId}`), 1500);
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold">Upload &amp; Analyse</h1>

      {/* Dropzone */}
      <FileDropzone
        onFile={setFile}
        disabled={!!jobId || uploading}
      />

      {/* File info */}
      {file && !jobId && (
        <div className="flex items-center justify-between bg-[var(--card)] border border-[var(--border)] rounded-xl px-5 py-3">
          <div>
            <p className="font-medium">{file.name}</p>
            <p className="text-sm text-[var(--muted)]">
              {(file.size / 1024).toFixed(1)} KB
            </p>
          </div>
          <button
            onClick={handleAnalyse}
            disabled={uploading}
            className="px-5 py-2 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {uploading ? "Uploading…" : "🚀 Start Analysis"}
          </button>
        </div>
      )}

      {/* Progress */}
      {jobId && (
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Pipeline Progress</h2>
            <span className="text-xs font-mono text-[var(--muted)]">
              Job: {jobId}
            </span>
          </div>
          <ProgressTracker
            stage={progress.stage}
            progress={progress.progress}
            errors={progress.errors}
          />
          {progress.stage === "completed" && (
            <p className="text-[var(--success)] font-medium">
              ✅ Analysis complete! Redirecting to report…
            </p>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  );
}
