"use client";

import { Plus, Trash2 } from "lucide-react";
import type { Education } from "@/lib/types";

interface Props {
  education: Education[];
  onChange: (education: Education[]) => void;
}

function emptyEducation(): Education {
  return { id: `edu_${crypto.randomUUID()}`, degree: "", school: "", location: undefined, dates: undefined, gpa: undefined };
}

export default function EducationSection({ education, onChange }: Props) {
  function update(index: number, patch: Partial<Education>) {
    onChange(education.map((e, i) => (i === index ? { ...e, ...patch } : e)));
  }

  function remove(index: number) {
    onChange(education.filter((_, i) => i !== index));
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-serif text-lg font-semibold text-ink">Education</h2>
        <button
          type="button"
          onClick={() => onChange([...education, emptyEducation()])}
          className="flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink-soft transition-colors hover:bg-paper hover:text-ink"
        >
          <Plus size={13} /> Add education
        </button>
      </div>

      {education.length === 0 && (
        <p className="text-sm text-ink-faint">No education added yet.</p>
      )}

      <div className="space-y-4">
        {education.map((edu, i) => (
          <div key={edu.id} className="rounded-xl border border-line bg-paper-raised p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-medium text-ink-soft">Education {i + 1}</span>
              <button type="button" onClick={() => remove(i)} className="text-ink-faint hover:text-red-500" aria-label="Remove">
                <Trash2 size={14} />
              </button>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <input type="text" value={edu.school} onChange={(e) => update(i, { school: e.target.value })} placeholder="School / University *"
                className="rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
              <input type="text" value={edu.degree} onChange={(e) => update(i, { degree: e.target.value })} placeholder="Degree *"
                className="rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
              <input type="text" value={edu.location ?? ""} onChange={(e) => update(i, { location: e.target.value || undefined })} placeholder="Location (e.g. Austin, TX)"
                className="rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
              <div className="flex gap-2">
                <input type="text" value={edu.dates ?? ""} onChange={(e) => update(i, { dates: e.target.value || undefined })} placeholder="Dates (e.g. 2018 – 2022)"
                  className="flex-1 rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
                <input type="number" value={edu.gpa ?? ""} onChange={(e) => update(i, { gpa: e.target.value ? Number(e.target.value) : undefined })} placeholder="GPA"
                  step="0.01" min={0} max={4.0}
                  className="w-24 rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
