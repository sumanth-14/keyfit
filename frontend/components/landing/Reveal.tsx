"use client";

import { useRef, type ElementType, type ReactNode } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP, ScrollTrigger);

type RevealProps = {
  children: ReactNode;
  /** Render as a different element (default: div). */
  as?: ElementType;
  className?: string;
  /** Seconds to wait before the reveal starts. */
  delay?: number;
  /** Stagger between direct children, in seconds. 0 = animate as one block. */
  stagger?: number;
};

/**
 * Fades + lifts content into view once, the first time it scrolls near the
 * viewport. Respects prefers-reduced-motion (content shows immediately).
 * Simple and classic — no parallax, no gradients, no bounce.
 */
export default function Reveal({
  children,
  as: Tag = "div",
  className,
  delay = 0,
  stagger = 0,
}: RevealProps) {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const root = ref.current;
      if (!root) return;

      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        return; // leave content in its natural, visible state
      }

      const targets = stagger > 0 ? Array.from(root.children) : root;

      gsap.from(targets, {
        opacity: 0,
        y: 24,
        duration: 0.8,
        ease: "power2.out",
        delay,
        stagger,
        scrollTrigger: {
          trigger: root,
          start: "top 85%",
          toggleActions: "play none none none",
        },
      });
    },
    { scope: ref },
  );

  return (
    <Tag ref={ref} className={className}>
      {children}
    </Tag>
  );
}
