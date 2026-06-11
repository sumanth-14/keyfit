import { Lock, FolderOpen, KeyRound } from "lucide-react";
import Reveal from "./Reveal";

const POINTS = [
  {
    Icon: FolderOpen,
    title: "Your Drive is the database",
    body: "Profiles, résumés, and drafts are written to one folder you own. Delete it and Keyfit forgets everything.",
  },
  {
    Icon: KeyRound,
    title: "Your API key, request-scoped",
    body: "Your NVIDIA NIM key is encrypted in your browser and used only for the moment of each request — never stored on our servers.",
  },
  {
    Icon: Lock,
    title: "Nothing else is touched",
    body: "Keyfit only reads and writes inside its own folder. The rest of your Drive is never accessed.",
  },
];

/** Data-ownership section — the differentiator behind the tagline. */
export default function DataOwnership() {
  return (
    <section id="data" className="border-t border-line px-6 py-24">
      <div className="mx-auto max-w-5xl">
        <Reveal className="max-w-2xl">
          <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-ink-faint">
            Owned by you
          </p>
          <h2 className="font-serif text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">
            Your career history shouldn&rsquo;t live on someone else&rsquo;s
            server.
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-ink-soft">
            Most résumé tools keep your data to keep you. Keyfit is built the
            other way around — there is no account to mine, because there is no
            database at all.
          </p>
        </Reveal>

        <Reveal stagger={0.12} className="mt-14 grid gap-10 sm:grid-cols-3">
          {POINTS.map(({ Icon, title, body }) => (
            <div key={title}>
              <Icon size={22} strokeWidth={1.75} className="text-accent" />
              <h3 className="mt-4 text-base font-medium text-ink">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">
                {body}
              </p>
            </div>
          ))}
        </Reveal>
      </div>
    </section>
  );
}
