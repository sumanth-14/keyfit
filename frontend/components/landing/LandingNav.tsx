import Link from "next/link";

/** Minimal top bar: serif wordmark + a single CTA. Solid colors, no gradient. */
export default function LandingNav() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-paper/85 backdrop-blur-sm">
      <nav className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <Link
          href="/"
          className="font-serif text-xl font-semibold tracking-tight text-ink"
        >
          Keyfit
        </Link>

        <div className="flex items-center gap-6">
          <a
            href="#how-it-works"
            className="hidden text-sm text-ink-soft transition-colors hover:text-ink sm:inline"
          >
            How it works
          </a>
          <a
            href="#data"
            className="hidden text-sm text-ink-soft transition-colors hover:text-ink sm:inline"
          >
            Your data
          </a>
          <Link
            href="/connect"
            className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-paper transition-colors hover:bg-accent"
          >
            Get started
          </Link>
        </div>
      </nav>
    </header>
  );
}
