import Link from "next/link";
import Reveal from "./Reveal";

/** Final call to action above the footer. */
export default function ClosingCta() {
  return (
    <section className="border-t border-line bg-ink px-6 py-24">
      <Reveal className="mx-auto max-w-2xl text-center">
        <h2 className="font-serif text-3xl font-semibold tracking-tight text-paper sm:text-4xl">
          Tailored to the job.{" "}
          <span className="italic text-accent">Owned by you.</span>
        </h2>
        <p className="mx-auto mt-4 max-w-md text-ink-faint">
          Connect your Drive and tailor your first résumé in under a minute.
        </p>
        <Link
          href="/connect"
          className="mt-9 inline-block rounded-lg bg-paper px-8 py-3 text-sm font-medium text-ink transition-colors hover:bg-accent hover:text-paper"
        >
          Connect Google Drive
        </Link>
      </Reveal>
    </section>
  );
}
