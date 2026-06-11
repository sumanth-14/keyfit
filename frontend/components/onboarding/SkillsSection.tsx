"use client";

import { Plus, Trash2 } from "lucide-react";

interface Props {
  skills: Record<string, string[]>;
  onChange: (skills: Record<string, string[]>) => void;
}

const DEFAULT_CATEGORIES = [
  "Programming Languages",
  "Frameworks & Libraries",
  "Databases & Storage",
  "Cloud & DevOps",
  "AI & ML",
  "Core Competencies",
];

export default function SkillsSection({ skills, onChange }: Props) {
  const entries = Object.entries(skills);

  function updateCategory(oldKey: string, newKey: string) {
    const updated: Record<string, string[]> = {};
    for (const [k, v] of Object.entries(skills)) {
      updated[k === oldKey ? newKey : k] = v;
    }
    onChange(updated);
  }

  function updateValues(key: string, raw: string) {
    onChange({
      ...skills,
      [key]: raw.split(",").map((s) => s.trim()).filter(Boolean),
    });
  }

  function removeCategory(key: string) {
    const updated = { ...skills };
    delete updated[key];
    onChange(updated);
  }

  function addCategory() {
    const name = `Category ${entries.length + 1}`;
    onChange({ ...skills, [name]: [] });
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="font-serif text-lg font-semibold text-ink">Skills</h2>
          <p className="mt-0.5 text-xs text-ink-faint">
            Suggested categories: {DEFAULT_CATEGORIES.join(", ")}
          </p>
        </div>
        <button
          type="button"
          onClick={addCategory}
          className="flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink-soft transition-colors hover:bg-paper hover:text-ink"
        >
          <Plus size={13} /> Add category
        </button>
      </div>

      {entries.length === 0 && (
        <p className="text-sm text-ink-faint">No skill categories yet.</p>
      )}

      <div className="space-y-3">
        {entries.map(([key, values]) => (
          <div key={key} className="flex items-start gap-3">
            <input
              type="text"
              value={key}
              onChange={(e) => updateCategory(key, e.target.value)}
              placeholder="Category name"
              className="w-44 shrink-0 rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm font-medium text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <input
              type="text"
              value={values.join(", ")}
              onChange={(e) => updateValues(key, e.target.value)}
              placeholder="Python, TypeScript, Go, …"
              className="flex-1 rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <button
              type="button"
              onClick={() => removeCategory(key)}
              className="mt-2.5 text-ink-faint hover:text-red-500"
              aria-label="Remove category"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
