"use client";

import { useCallback, useState } from "react";

interface FileDropzoneProps {
  accept?: string;
  onFile: (file: File) => void;
  disabled?: boolean;
}

export function FileDropzone({
  accept = ".pdf,.docx,.pptx,.xlsx",
  onFile,
  disabled = false,
}: FileDropzoneProps) {
  const [dragging, setDragging] = useState(false);
  const [filename, setFilename] = useState<string | null>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (disabled) return;
      const file = e.dataTransfer.files?.[0];
      if (file) {
        setFilename(file.name);
        onFile(file);
      }
    },
    [onFile, disabled]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setFilename(file.name);
        onFile(file);
      }
    },
    [onFile]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
        dragging
          ? "border-[var(--accent)] bg-blue-50/50"
          : "border-[var(--border)] hover:border-[var(--accent)]"
      } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
    >
      <input
        type="file"
        accept={accept}
        onChange={handleChange}
        disabled={disabled}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
      />
      <div className="text-4xl mb-3">📄</div>
      {filename ? (
        <p className="font-medium">{filename}</p>
      ) : (
        <>
          <p className="font-medium">Drop a document here or click to browse</p>
          <p className="text-sm text-[var(--muted)] mt-1">
            PDF, DOCX, PPTX, XLSX — max 50 MB
          </p>
        </>
      )}
    </div>
  );
}
