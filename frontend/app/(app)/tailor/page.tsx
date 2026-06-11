"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "@/lib/store/auth";
import { runPipeline } from "@/lib/api/pipeline";
import { usePipelineStream } from "@/hooks/usePipelineStream";
import JobInputForm, { type InputMode } from "@/components/pipeline/JobInputForm";
import RoleSelector from "@/components/pipeline/RoleSelector";
import PipelineProgress from "@/components/pipeline/PipelineProgress";
import type { PipelineRequest } from "@/lib/types";

type PageView = "form" | "running";

export default function TailorPage() {
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const nimKey = useAuthStore((s) => s.nimKey);

  // Form state
  const [company, setCompany] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [roleConfigId, setRoleConfigId] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [inputMode, setInputMode] = useState<InputMode>("url");
  const [outreachEnabled, setOutreachEnabled] = useState(true);
  const [contactName, setContactName] = useState("");

  const [view, setView] = useState<PageView>("form");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { stages, streamStatus, applicationId, error, start } =
    usePipelineStream();

  // Redirect when pipeline completes
  useEffect(() => {
    if (streamStatus === "complete" && applicationId) {
      router.push(`/applications/${applicationId}`);
    }
  }, [streamStatus, applicationId, router]);

  // Return to the form after a failure, preserving the user's inputs. If the
  // scrape stage was the one that failed, drop them into paste-JD mode so the
  // recovery path matches the error message ("paste the description directly").
  function handleReset() {
    const scrapeFailed = stages.some(
      (s) => s.stage === "scrape" && s.status === "failed",
    );
    if (scrapeFailed) setInputMode("paste");
    setView("form");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken || !nimKey) return;

    if (!jobUrl.trim() && !jobDescription.trim()) {
      setSubmitError("Provide a job URL or paste the job description.");
      return;
    }
    if (!company.trim() || !roleTitle.trim() || !roleConfigId || roleConfigId === "other") {
      setSubmitError("Company, role title, and role type are all required.");
      return;
    }

    setSubmitError(null);
    setSubmitting(true);

    const request: PipelineRequest = {
      company_name: company.trim(),
      role_title: roleTitle.trim(),
      role_config_id: roleConfigId,
      outreach: {
        enabled: outreachEnabled,
        ...(outreachEnabled && contactName.trim()
          ? { contact_name: contactName.trim() }
          : {}),
      },
      ...(jobDescription.trim()
        ? { job_description: jobDescription.trim() }
        : { job_url: jobUrl.trim() }),
    };

    try {
      const result = await runPipeline(accessToken, nimKey, request);
      setView("running");
      start(result.job_id, accessToken);
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Failed to start pipeline.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (view === "running") {
    return (
      <div className="mx-auto max-w-lg px-6 py-10">
        <div className="mb-6">
          <h1 className="font-serif text-2xl font-semibold tracking-tight text-ink">
            Tailoring résumé
          </h1>
          <p className="mt-1 text-sm text-ink-soft">
            {company} — {roleTitle}
          </p>
        </div>
        <PipelineProgress
          stages={stages}
          streamStatus={streamStatus}
          error={error}
          onReset={handleReset}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg px-6 py-10">
      <div className="mb-8">
        <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink">
          Tailor résumé
        </h1>
        <p className="mt-2 text-sm text-ink-soft">
          Paste a job description or URL and the AI will tailor your profile to
          it.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Job input */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink-soft">
            Job posting
          </label>
          <JobInputForm
            jobUrl={jobUrl}
            jobDescription={jobDescription}
            onJobUrlChange={setJobUrl}
            onJobDescriptionChange={setJobDescription}
            mode={inputMode}
            onModeChange={setInputMode}
          />
        </div>

        {/* Company + role title */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-soft">
              Company
            </label>
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Stripe"
              className="w-full rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-soft">
              Role title
            </label>
            <input
              type="text"
              value={roleTitle}
              onChange={(e) => setRoleTitle(e.target.value)}
              placeholder="Software Engineer"
              className="w-full rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>
        </div>

        {/* Role type */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink-soft">
            Role type
          </label>
          <RoleSelector value={roleConfigId} onChange={setRoleConfigId} />
        </div>

        {/* Outreach toggle */}
        <div className="rounded-xl border border-line p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-ink-soft">
                Generate outreach
              </p>
              <p className="mt-0.5 text-xs text-ink-faint">
                Cold email + LinkedIn message
              </p>
            </div>
            <button
              type="button"
              onClick={() => setOutreachEnabled((v) => !v)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none ${
                outreachEnabled ? "bg-accent" : "bg-line"
              }`}
              aria-pressed={outreachEnabled}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-paper-raised shadow transition duration-200 ${
                  outreachEnabled ? "translate-x-4" : "translate-x-0"
                }`}
              />
            </button>
          </div>
          {outreachEnabled && (
            <div className="mt-3">
              <input
                type="text"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                placeholder="Recruiter / hiring manager name (optional)"
                className="w-full rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
          )}
        </div>

        {submitError && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {submitError}
          </div>
        )}

        <div className="flex items-center justify-between">
          {!nimKey && (
            <p className="text-xs text-ink-faint">
              No NIM key.{" "}
              <a
                href="/onboarding/api-key"
                className="underline hover:text-ink"
              >
                Add one
              </a>
            </p>
          )}
          <div className="ml-auto">
            <button
              type="submit"
              disabled={submitting || !nimKey}
              className="flex items-center gap-2 rounded-xl bg-ink px-6 py-3 text-sm font-medium text-paper transition-colors hover:bg-accent disabled:opacity-50"
            >
              {submitting && <Loader2 size={14} className="animate-spin" />}
              {submitting ? "Starting…" : "Tailor résumé"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
