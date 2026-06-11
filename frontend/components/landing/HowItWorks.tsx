import Reveal from "./Reveal";

const STEPS = [
  {
    n: "01",
    title: "Connect your Drive",
    body: "Sign in with Google and add your profile once. Keyfit creates a single Resume_Tailor folder — and never touches anything else.",
  },
  {
    n: "02",
    title: "Paste a job posting",
    body: "Drop in any job description. Keyfit reads what the role actually wants and matches it against your achievement library.",
  },
  {
    n: "03",
    title: "Get a tailored résumé",
    body: "A one-page résumé, a match critique, and ready-to-send outreach messages — saved straight to your Drive.",
  },
];

/** Three-step explainer. Scroll-revealed as a staggered group. */
export default function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-line px-6 py-24">
      <div className="mx-auto max-w-5xl">
        <Reveal>
          <h2 className="font-serif text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            From posting to polished, in three steps
          </h2>
          <p className="mt-3 max-w-xl text-ink-soft">
            No templates to wrestle with. No copy-pasting between tools.
          </p>
        </Reveal>

        <Reveal stagger={0.15} className="mt-14 grid gap-10 sm:grid-cols-3">
          {STEPS.map((step) => (
            <div key={step.n}>
              <span className="font-serif text-2xl text-accent">{step.n}</span>
              <h3 className="mt-4 text-lg font-medium text-ink">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">
                {step.body}
              </p>
            </div>
          ))}
        </Reveal>
      </div>
    </section>
  );
}
