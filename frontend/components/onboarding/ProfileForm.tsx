"use client";

import { useRef, useState } from "react";
import { Upload, Loader2 } from "lucide-react";
import type { Profile } from "@/lib/types";
import { parseFromResume, updateProfile } from "@/lib/api/profile";
import PersonalSection from "./PersonalSection";
import EducationSection from "./EducationSection";
import ExperienceSection from "./ExperienceSection";
import ProjectsSection from "./ProjectsSection";
import SkillsSection from "./SkillsSection";

const EMPTY_PROFILE: Profile = {
  version: 1,
  personal: { name: "", email: "" },
  visa_status: undefined,
  education: [],
  experience: [],
  projects: [],
  skills: {},
};

interface Props {
  initial?: Profile;
  accessToken: string;
  nimKey: string;
  onSaved: () => void;
}

export default function ProfileForm({ initial, accessToken, nimKey, onSaved }: Props) {
  const [profile, setProfile] = useState<Profile>(initial ?? EMPTY_PROFILE);
  const [saving, setSaving] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [parseWarnings, setParseWarnings] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setParsing(true);
    setElapsed(0);
    setError(null);
    setParseWarnings([]);
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    try {
      const result = await parseFromResume(accessToken, nimKey, file);
      setProfile(result.profile);
      setParseWarnings((result.flagged_fields ?? []).map((f) => f.reason));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to parse resume.");
    } finally {
      setParsing(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      // Reset input so same file can be re-uploaded
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await updateProfile(accessToken, profile);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save profile.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-10">
      {/* Parse from resume upload */}
      <div className="rounded-xl border border-dashed border-line p-5">
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <p className="text-sm font-medium text-ink">
              Import from existing résumé
            </p>
            <p className="mt-0.5 text-xs text-ink-faint">
              Upload your <span className="font-mono">.tex</span> file and the AI will pre-fill
              the form. You can edit afterwards.
            </p>
          </div>
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-paper hover:text-ink">
            {parsing ? (
              <><Loader2 size={14} className="animate-spin" /> Parsing… {elapsed}s</>
            ) : (
              <><Upload size={14} /> Upload .tex</>
            )}
            <input
              ref={fileRef}
              type="file"
              accept=".tex"
              onChange={handleFileChange}
              disabled={parsing}
              className="hidden"
            />
          </label>
        </div>

        {parsing && (
          <p className="mt-3 text-xs text-ink-faint">
            Reading your résumé and extracting your experience. The first upload can take up
            to a minute while the server wakes up — later ones are faster.
          </p>
        )}

        {parseWarnings.length > 0 && (
          <ul className="mt-3 space-y-1">
            {parseWarnings.map((w, i) => (
              <li key={i} className="text-xs text-amber-600">
                ⚠ {w}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Sections */}
      <PersonalSection
        personal={profile.personal}
        visaStatus={profile.visa_status}
        onChange={(personal) => setProfile((p) => ({ ...p, personal }))}
        onVisaChange={(visa_status) => setProfile((p) => ({ ...p, visa_status }))}
      />

      <hr className="border-line" />

      <EducationSection
        education={profile.education}
        onChange={(education) => setProfile((p) => ({ ...p, education }))}
      />

      <hr className="border-line" />

      <ExperienceSection
        experience={profile.experience}
        onChange={(experience) => setProfile((p) => ({ ...p, experience }))}
      />

      <hr className="border-line" />

      <ProjectsSection
        projects={profile.projects}
        onChange={(projects) => setProfile((p) => ({ ...p, projects }))}
      />

      <hr className="border-line" />

      <SkillsSection
        skills={profile.skills}
        onChange={(skills) => setProfile((p) => ({ ...p, skills }))}
      />

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Submit */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={saving || parsing}
          className="flex items-center gap-2 rounded-xl bg-ink px-6 py-3 text-sm font-medium text-paper transition-colors hover:bg-accent disabled:opacity-50"
        >
          {saving && <Loader2 size={14} className="animate-spin" />}
          {saving ? "Saving…" : "Save profile and continue"}
        </button>
      </div>
    </form>
  );
}
