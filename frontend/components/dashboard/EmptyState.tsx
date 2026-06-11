import Link from "next/link";
import { FileText } from "lucide-react";

export default function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-soft">
        <FileText size={28} className="text-accent" strokeWidth={1.5} />
      </div>
      <h2 className="mb-2 font-serif text-xl font-semibold text-ink">
        No applications yet
      </h2>
      <p className="mb-6 max-w-xs text-sm text-ink-soft">
        Paste a job description and let the AI tailor your résumé in seconds.
      </p>
      <Link
        href="/tailor"
        className="rounded-xl bg-ink px-5 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-accent"
      >
        Tailor my first résumé
      </Link>
    </div>
  );
}
