"use client";

import type { PersonalInfo, VisaStatus } from "@/lib/types";

interface Props {
  personal: PersonalInfo;
  visaStatus: VisaStatus | undefined;
  onChange: (personal: PersonalInfo) => void;
  onVisaChange: (visa: VisaStatus | undefined) => void;
}

function Field({
  label, id, value, onChange, placeholder, required, type = "text",
}: {
  label: string; id: string; value: string; onChange: (v: string) => void;
  placeholder?: string; required?: boolean; type?: string;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-ink-soft">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        id={id} type={type} value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder} required={required}
        className="w-full rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
      />
    </div>
  );
}

export default function PersonalSection({ personal, visaStatus, onChange, onVisaChange }: Props) {
  function set(key: keyof PersonalInfo, value: string) {
    onChange({ ...personal, [key]: value || undefined });
  }

  return (
    <section>
      <h2 className="mb-4 font-serif text-lg font-semibold text-ink">Personal info</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Full name" id="name" value={personal.name ?? ""} onChange={(v) => onChange({ ...personal, name: v })} placeholder="Jane Smith" required />
        <Field label="Email" id="email" type="email" value={personal.email ?? ""} onChange={(v) => onChange({ ...personal, email: v })} placeholder="jane@example.com" required />
        <Field label="Phone" id="phone" value={personal.phone ?? ""} onChange={(v) => set("phone", v)} placeholder="+1 (555) 000-0000" />
        <Field label="Location" id="location" value={personal.location ?? ""} onChange={(v) => set("location", v)} placeholder="San Francisco, CA" />
        <Field label="LinkedIn URL" id="linkedin" value={personal.linkedin ?? ""} onChange={(v) => set("linkedin", v)} placeholder="linkedin.com/in/janesmith" />
        <Field label="GitHub URL" id="github" value={personal.github ?? ""} onChange={(v) => set("github", v)} placeholder="github.com/janesmith" />
        <Field label="Portfolio / Website" id="portfolio" value={personal.portfolio ?? ""} onChange={(v) => set("portfolio", v)} placeholder="janesmith.dev" />
      </div>

      <div className="mt-4 flex items-center gap-3">
        <input
          id="sponsorship" type="checkbox"
          checked={visaStatus?.needs_sponsorship ?? false}
          onChange={(e) =>
            onVisaChange(
              e.target.checked
                ? { needs_sponsorship: true, stem_extension_eligible: visaStatus?.stem_extension_eligible ?? false, type: visaStatus?.type ?? "unknown" }
                : undefined,
            )
          }
          className="h-4 w-4 rounded border-line accent-[var(--color-accent)]"
        />
        <label htmlFor="sponsorship" className="text-sm text-ink-soft">
          I require visa sponsorship
        </label>
        {visaStatus?.needs_sponsorship && (
          <input
            type="text"
            value={visaStatus.type === "unknown" ? "" : visaStatus.type}
            onChange={(e) => onVisaChange({ ...visaStatus, type: e.target.value || "unknown" })}
            placeholder="e.g. h1b, opt, tn"
            className="ml-2 rounded-lg border border-line bg-paper-raised px-3 py-1.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent"
          />
        )}
      </div>
    </section>
  );
}
