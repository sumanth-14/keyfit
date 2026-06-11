import Link from "next/link";
import type { ApplicationListItem } from "@/lib/types";

const COLOR_CLASSES = {
  green: "bg-emerald-100 text-emerald-700",
  yellow: "bg-amber-100 text-amber-700",
  red: "bg-red-100 text-red-700",
} as const;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

interface Props {
  application: ApplicationListItem;
}

export default function ApplicationRow({ application }: Props) {
  const { application_id, company, role_title, created_at, score, verdict, color } = application;
  const colorClass = COLOR_CLASSES[color] ?? COLOR_CLASSES.red;

  return (
    <Link
      href={`/applications/${application_id}`}
      className="flex items-center gap-4 rounded-xl border border-line bg-paper-raised px-5 py-4 transition-colors hover:border-ink-faint hover:bg-paper"
    >
      {/* Score badge */}
      <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-lg font-bold ${colorClass}`}>
        {score}
      </div>

      {/* Company / role */}
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold text-ink">{company}</p>
        <p className="truncate text-sm text-ink-soft">{role_title}</p>
      </div>

      {/* Verdict */}
      <span className={`hidden shrink-0 rounded-full px-2.5 py-1 text-xs font-medium sm:block ${colorClass}`}>
        {verdict}
      </span>

      {/* Date */}
      <time
        dateTime={created_at}
        className="shrink-0 text-sm text-ink-faint"
      >
        {formatDate(created_at)}
      </time>
    </Link>
  );
}
