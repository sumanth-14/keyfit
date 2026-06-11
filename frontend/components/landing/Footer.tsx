import Link from "next/link";

/** Quiet footer — wordmark, tagline, year. */
export default function Footer() {
  return (
    <footer className="border-t border-line px-6 py-10">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 sm:flex-row">
        <div>
          <Link
            href="/"
            className="font-serif text-lg font-semibold tracking-tight text-ink"
          >
            Keyfit
          </Link>
          <span className="ml-3 text-sm text-ink-faint">
            Tailored to the job. Owned by you.
          </span>
        </div>
        <p className="text-xs text-ink-faint">
          © {new Date().getFullYear()} Keyfit
        </p>
      </div>
    </footer>
  );
}
