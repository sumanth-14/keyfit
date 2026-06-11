"use client";

import { Loader2, CheckCircle2, XCircle, Circle } from "lucide-react";
import type { StageState, StreamStatus } from "@/hooks/usePipelineStream";

const STAGE_LABELS: Record<string, string> = {
  scrape: "Fetching job description",
  jd_analyzer: "Analyzing requirements",
  tailor: "Tailoring résumé",
  compile: "Compiling PDF",
  critique: "Scoring resume",
  outreach: "Drafting outreach messages",
  persist: "Saving to Drive",
};

interface Props {
  stages: StageState[];
  streamStatus: StreamStatus;
  error: string | null;
  onReset?: () => void;
}

export default function PipelineProgress({
  stages,
  streamStatus,
  error,
  onReset,
}: Props) {
  return (
    <div className="rounded-xl border border-line bg-paper-raised p-6">
      <p className="mb-5 text-xs font-semibold uppercase tracking-widest text-ink-faint">
        Pipeline
      </p>

      <ol className="space-y-4">
        {stages.map((s) => (
          <li key={s.stage} className="flex items-start gap-3">
            <div className="mt-0.5 shrink-0">
              {s.status === "pending" && (
                <Circle size={16} className="text-ink-faint" />
              )}
              {s.status === "running" && (
                <Loader2 size={16} className="animate-spin text-accent" />
              )}
              {s.status === "complete" && (
                <CheckCircle2 size={16} className="text-emerald-500" />
              )}
              {s.status === "failed" && (
                <XCircle size={16} className="text-red-500" />
              )}
            </div>
            <div className="flex-1">
              <span
                className={`text-sm ${
                  s.status === "pending"
                    ? "text-ink-faint"
                    : s.status === "running"
                      ? "font-medium text-ink"
                      : s.status === "complete"
                        ? "text-ink-soft line-through decoration-line"
                        : "text-red-600"
                }`}
              >
                {STAGE_LABELS[s.stage] ?? s.stage}
              </span>
              {s.status === "failed" && s.error && (
                <p className="mt-0.5 text-xs text-red-500">{s.error}</p>
              )}
            </div>
          </li>
        ))}
      </ol>

      {streamStatus === "complete" && (
        <p className="mt-6 text-sm font-medium text-accent">
          Done! Redirecting to your application…
        </p>
      )}

      {streamStatus === "failed" && error && (
        <div className="mt-6 space-y-3">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
          {onReset && (
            <button
              type="button"
              onClick={onReset}
              className="w-full rounded-xl border border-line px-4 py-2.5 text-sm font-medium text-ink-soft transition-colors hover:bg-paper hover:text-ink"
            >
              Edit and try again
            </button>
          )}
        </div>
      )}
    </div>
  );
}
