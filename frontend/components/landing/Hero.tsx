"use client";

import { useRef } from "react";
import Link from "next/link";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP);

/** Above-the-fold hero. Tagline is the H1; staggered entrance on load. */
export default function Hero() {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

      gsap.from(".hero-reveal", {
        opacity: 0,
        y: 20,
        duration: 0.9,
        ease: "power3.out",
        stagger: 0.12,
        delay: 0.1,
      });
    },
    { scope: ref },
  );

  return (
    <section ref={ref} className="px-6 pt-20 pb-24 sm:pt-28 sm:pb-32">
      <div className="mx-auto max-w-3xl text-center">
        <p className="hero-reveal mb-6 text-sm font-medium uppercase tracking-[0.2em] text-ink-faint">
          AI résumé tailoring
        </p>

        <h1 className="hero-reveal font-serif text-5xl font-semibold leading-[1.05] tracking-tight text-ink sm:text-6xl">
          Tailored to the job.
          <br />
          <span className="italic text-accent">Owned by you.</span>
        </h1>

        <p className="hero-reveal mx-auto mt-7 max-w-xl text-lg leading-relaxed text-ink-soft">
          Keyfit reshapes your résumé to fit any job posting in seconds — then
          stores everything in your own Google Drive. No database, no lock-in.
        </p>

        <div className="hero-reveal mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/connect"
            className="w-full rounded-lg bg-ink px-7 py-3 text-center text-sm font-medium text-paper transition-colors hover:bg-accent sm:w-auto"
          >
            Connect Google Drive
          </Link>
          <a
            href="#how-it-works"
            className="w-full rounded-lg border border-line px-7 py-3 text-center text-sm font-medium text-ink transition-colors hover:border-ink sm:w-auto"
          >
            See how it works
          </a>
        </div>

        <p className="hero-reveal mt-6 text-xs text-ink-faint">
          Free to use · Powered by NVIDIA NIM · Your data never leaves your Drive
        </p>
      </div>
    </section>
  );
}
