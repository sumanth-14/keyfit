import {
  FileText,
  Gauge,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  HardDrive,
} from "lucide-react";
import Reveal from "./Reveal";

const FEATURES = [
  {
    Icon: FileText,
    title: "One-page, guaranteed",
    body: "Keyfit compiles real LaTeX and trims older roles until it fits on a single page. Every time.",
  },
  {
    Icon: Gauge,
    title: "Match score & critique",
    body: "See how well you fit the role and exactly what to strengthen before you apply.",
  },
  {
    Icon: MessageSquareText,
    title: "Outreach, written for you",
    body: "Recruiter and referral messages drafted from the same context as your résumé.",
  },
  {
    Icon: ShieldCheck,
    title: "Never fabricates",
    body: "It selects and rewords from your own achievements — it never invents experience or metrics.",
  },
  {
    Icon: Sparkles,
    title: "Knows every role",
    body: "Built-in roles plus configs generated on the fly for anything else — you never see the seams.",
  },
  {
    Icon: HardDrive,
    title: "Lives in your Drive",
    body: "No database on our side. Every résumé, profile, and draft persists in your own Google Drive.",
  },
];

/** Feature grid. Cards reveal as a staggered group on scroll. */
export default function Features() {
  return (
    <section className="border-t border-line bg-paper-raised px-6 py-24">
      <div className="mx-auto max-w-5xl">
        <Reveal>
          <h2 className="font-serif text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            Everything a tailored application needs
          </h2>
        </Reveal>

        <Reveal stagger={0.1} className="mt-14 grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ Icon, title, body }) => (
            <div key={title} className="bg-paper-raised p-7">
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
