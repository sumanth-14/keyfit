"use client";

import type { Critique, CritiqueColor } from "@/lib/types";

interface Props {
  critique: Critique;
}

const VERDICT_STYLES: Record<string, string> = {
  "STRONG MATCH": "bg-emerald-100 text-emerald-800",
  "NEEDS WORK": "bg-amber-100 text-amber-800",
  "WEAK MATCH": "bg-red-100 text-red-800",
};

const SCORE_COLOR: Record<CritiqueColor, string> = {
  green: "text-emerald-600",
  yellow: "text-amber-600",
  red: "text-red-600",
};

const PRIORITY_STYLES: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-paper text-ink-soft",
};

const SCORE_LABELS: Record<string, string> = {
  ats_keyword_match: "ATS Keywords",
  impact_metrics: "Impact & Metrics",
  bullet_quality: "Bullet Quality",
  role_alignment: "Role Alignment",
  clarity: "Clarity",
};

function colorForScore(score: number): CritiqueColor {
  if (score >= 80) return "green";
  if (score >= 60) return "yellow";
  return "red";
}

export default function CritiquePanel({ critique }: Props) {
  const color = colorForScore(critique.total);
  const scoreEntries = Object.entries(critique.scores ?? {});

  return (
    <div className="space-y-8">
      {/* Score + verdict */}
      <div className="flex items-center gap-5">
        <span className={`text-6xl font-bold tabular-nums leading-none ${SCORE_COLOR[color]}`}>
          {critique.total}
        </span>
        <div>
          <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${VERDICT_STYLES[critique.verdict] ?? ""}`}>
            {critique.verdict}
          </span>
          <p className="mt-2 text-xs text-ink-faint">out of 100</p>
        </div>
      </div>

      {/* Category breakdown */}
      {scoreEntries.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-widest text-ink-faint">Breakdown</p>
          {scoreEntries.map(([key, s]) => (
            <div key={key} className="flex items-center gap-3">
              <span className="w-40 shrink-0 text-xs text-ink-soft">
                {SCORE_LABELS[key] ?? key}
              </span>
              <div className="flex-1 overflow-hidden rounded-full bg-line">
                <div
                  className="h-1.5 rounded-full bg-accent transition-all"
                  style={{ width: `${Math.round((s.score / s.max) * 100)}%` }}
                />
              </div>
              <span className="w-12 shrink-0 text-right text-xs tabular-nums text-ink-soft">
                {s.score}/{s.max}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Keywords */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        {(critique.keywords_found?.length ?? 0) > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-ink-faint">Matched keywords</p>
            <div className="flex flex-wrap gap-1.5">
              {critique.keywords_found.map((kw) => (
                <span key={kw} className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs text-emerald-800">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}
        {(critique.keywords_missing?.length ?? 0) > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-ink-faint">Missing keywords</p>
            <div className="flex flex-wrap gap-1.5">
              {critique.keywords_missing.map((kw) => (
                <span key={kw} className="rounded-full bg-red-100 px-2.5 py-1 text-xs text-red-700">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Top fixes */}
      {(critique.top_fixes?.length ?? 0) > 0 && (
        <div>
          <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-ink-faint">Top fixes</p>
          <ol className="space-y-3">
            {critique.top_fixes.map((fix, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className={`mt-0.5 rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${PRIORITY_STYLES[fix.priority.toLowerCase()] ?? PRIORITY_STYLES.low}`}>
                  {fix.priority}
                </span>
                <p className="text-sm text-ink-soft">{fix.fix}</p>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
