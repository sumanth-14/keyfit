"use client";

import { Plus, Trash2 } from "lucide-react";
import type { Project } from "@/lib/types";

interface Props {
  projects: Project[];
  onChange: (projects: Project[]) => void;
}

function emptyProject(): Project {
  return { id: `proj_${crypto.randomUUID()}`, name: "", text: "", stack: [], themes: [], metrics: [], url: undefined };
}

export default function ProjectsSection({ projects, onChange }: Props) {
  function update(index: number, patch: Partial<Project>) {
    onChange(projects.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  }
  function remove(index: number) { onChange(projects.filter((_, i) => i !== index)); }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-serif text-lg font-semibold text-ink">Projects</h2>
        <button type="button" onClick={() => onChange([...projects, emptyProject()])}
          className="flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink-soft transition-colors hover:bg-paper hover:text-ink">
          <Plus size={13} /> Add project
        </button>
      </div>

      {projects.length === 0 && (
        <p className="text-sm text-ink-faint">No projects added yet.</p>
      )}

      <div className="space-y-4">
        {projects.map((proj, pi) => (
          <div key={proj.id} className="rounded-xl border border-line bg-paper-raised p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-medium text-ink-soft">Project {pi + 1}</span>
              <button type="button" onClick={() => remove(pi)} className="text-ink-faint hover:text-red-500" aria-label="Remove project">
                <Trash2 size={14} />
              </button>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <input type="text" value={proj.name} onChange={(e) => update(pi, { name: e.target.value })} placeholder="Project name *"
                className="rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
              <input type="text" value={proj.subtitle ?? ""} onChange={(e) => update(pi, { subtitle: e.target.value || undefined })} placeholder="Subtitle / tagline (optional)"
                className="rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
              <input type="url" value={proj.url ?? ""} onChange={(e) => update(pi, { url: e.target.value || undefined })} placeholder="URL (optional)"
                className="rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
              <input type="text" value={(proj.stack ?? []).join(", ")}
                onChange={(e) => update(pi, { stack: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
                placeholder="Tech stack (comma-separated)"
                className="rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
              <div className="sm:col-span-2">
                <textarea rows={3} value={proj.text}
                  onChange={(e) => update(pi, { text: e.target.value })}
                  placeholder="Describe the project — what it does, what you built, key results"
                  className="w-full rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
