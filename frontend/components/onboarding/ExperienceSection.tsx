"use client";

import { Plus, Trash2, GripVertical } from "lucide-react";
import type { Bullet, Experience } from "@/lib/types";

interface Props {
  experience: Experience[];
  onChange: (experience: Experience[]) => void;
}

function newBullet(text = ""): Bullet {
  return { id: `bullet_${crypto.randomUUID()}`, text, themes: [], metrics: [], tech_stack: [] };
}

function emptyExperience(): Experience {
  return { id: `exp_${crypto.randomUUID()}`, company: "", title: "", dates: "", level: "L3", bullets: [newBullet()] };
}

const LEVELS = ["L1", "L2", "L3", "L4"] as const;
const LEVEL_LABELS: Record<string, string> = {
  L1: "L1 — Intern / Junior",
  L2: "L2 — Mid-level",
  L3: "L3 — Senior",
  L4: "L4 — Staff / Principal",
};

interface ExpCardProps {
  exp: Experience;
  index: number;
  onUpdate: (patch: Partial<Experience>) => void;
  onRemove: () => void;
}

function ExperienceCard({ exp, index, onUpdate, onRemove }: ExpCardProps) {
  function updateBullet(bi: number, text: string) {
    onUpdate({ bullets: exp.bullets.map((b, i) => (i === bi ? { ...b, text } : b)) });
  }
  function addBullet() { onUpdate({ bullets: [...exp.bullets, newBullet()] }); }
  function removeBullet(bi: number) { onUpdate({ bullets: exp.bullets.filter((_, i) => i !== bi) }); }

  return (
    <div className="rounded-xl border border-line bg-paper-raised p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium text-ink-soft">
          <GripVertical size={14} className="text-ink-faint" />
          Experience {index + 1}
        </div>
        <button type="button" onClick={onRemove} className="text-ink-faint hover:text-red-500" aria-label="Remove experience">
          <Trash2 size={14} />
        </button>
      </div>

      <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <input type="text" value={exp.company} onChange={(e) => onUpdate({ company: e.target.value })} placeholder="Company *"
          className="rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
        <input type="text" value={exp.title} onChange={(e) => onUpdate({ title: e.target.value })} placeholder="Job title *"
          className="rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
        <input type="text" value={exp.dates ?? ""} onChange={(e) => onUpdate({ dates: e.target.value || undefined })} placeholder="Dates (e.g. Jan 2022 – Present) *"
          className="rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
        <input type="text" value={exp.location ?? ""} onChange={(e) => onUpdate({ location: e.target.value || undefined })} placeholder="Location (optional)"
          className="rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
        <div className="sm:col-span-2">
          <select value={exp.level ?? "L3"} onChange={(e) => onUpdate({ level: e.target.value })}
            className="w-full rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink-soft focus:outline-none focus:ring-2 focus:ring-accent">
            {LEVELS.map((l) => <option key={l} value={l}>{LEVEL_LABELS[l]}</option>)}
          </select>
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-ink-soft">Bullets</p>
        {exp.bullets.map((b, bi) => (
          <div key={b.id} className="flex items-start gap-2">
            <textarea rows={2} value={b.text} onChange={(e) => updateBullet(bi, e.target.value)}
              placeholder={`Bullet ${bi + 1} — start with an action verb`}
              className="flex-1 rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
            {exp.bullets.length > 1 && (
              <button type="button" onClick={() => removeBullet(bi)} className="mt-1.5 text-ink-faint hover:text-red-500" aria-label="Remove bullet">
                <Trash2 size={13} />
              </button>
            )}
          </div>
        ))}
        <button type="button" onClick={addBullet} className="flex items-center gap-1 text-xs text-ink-faint transition-colors hover:text-ink">
          <Plus size={12} /> Add bullet
        </button>
      </div>
    </div>
  );
}

export default function ExperienceSection({ experience, onChange }: Props) {
  function update(index: number, patch: Partial<Experience>) {
    onChange(experience.map((e, i) => (i === index ? { ...e, ...patch } : e)));
  }
  function remove(index: number) { onChange(experience.filter((_, i) => i !== index)); }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-serif text-lg font-semibold text-ink">Experience</h2>
        <button type="button" onClick={() => onChange([...experience, emptyExperience()])}
          className="flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink-soft transition-colors hover:bg-paper hover:text-ink">
          <Plus size={13} /> Add role
        </button>
      </div>

      {experience.length === 0 && (
        <p className="text-sm text-ink-faint">No experience added yet.</p>
      )}

      <div className="space-y-4">
        {experience.map((exp, i) => (
          <ExperienceCard key={exp.id} exp={exp} index={i} onUpdate={(patch) => update(i, patch)} onRemove={() => remove(i)} />
        ))}
      </div>
    </section>
  );
}
