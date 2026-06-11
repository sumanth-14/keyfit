"use client";

import { useState } from "react";
import { Link, FileText } from "lucide-react";

export type InputMode = "url" | "paste";

interface Props {
  jobUrl: string;
  jobDescription: string;
  onJobUrlChange: (val: string) => void;
  onJobDescriptionChange: (val: string) => void;
  // Optional controlled mode. When provided, the parent owns the toggle
  // (e.g. to force "paste" after a scrape failure). Otherwise it's internal.
  mode?: InputMode;
  onModeChange?: (mode: InputMode) => void;
}

export default function JobInputForm({
  jobUrl,
  jobDescription,
  onJobUrlChange,
  onJobDescriptionChange,
  mode: controlledMode,
  onModeChange,
}: Props) {
  const [internalMode, setInternalMode] = useState<InputMode>("url");
  const mode = controlledMode ?? internalMode;
  const setMode = (next: InputMode) => {
    setInternalMode(next);
    onModeChange?.(next);
  };

  return (
    <div>
      <div className="mb-3 flex w-fit rounded-lg border border-line p-0.5">
        <button
          type="button"
          onClick={() => setMode("url")}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
            mode === "url"
              ? "bg-ink text-paper"
              : "text-ink-soft hover:text-ink"
          }`}
        >
          <Link size={12} /> Job URL
        </button>
        <button
          type="button"
          onClick={() => setMode("paste")}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
            mode === "paste"
              ? "bg-ink text-paper"
              : "text-ink-soft hover:text-ink"
          }`}
        >
          <FileText size={12} /> Paste JD
        </button>
      </div>

      {mode === "url" ? (
        <input
          type="url"
          value={jobUrl}
          onChange={(e) => onJobUrlChange(e.target.value)}
          placeholder="https://stripe.com/jobs/..."
          className="w-full rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
        />
      ) : (
        <textarea
          rows={8}
          value={jobDescription}
          onChange={(e) => onJobDescriptionChange(e.target.value)}
          placeholder="Paste the full job description here…"
          className="w-full rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
        />
      )}
    </div>
  );
}
