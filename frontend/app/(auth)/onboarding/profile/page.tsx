"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { initialize } from "@/lib/api/setup";
import { getProfile } from "@/lib/api/profile";
import { ApiRequestError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/store/auth";
import ProfileForm from "@/components/onboarding/ProfileForm";
import type { Profile } from "@/lib/types";

type PageState = "loading" | "ready" | "error";

export default function ProfileSetupPage() {
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const nimKey = useAuthStore((s) => s.nimKey);
  const [state, setState] = useState<PageState>("loading");
  const [existingProfile, setExistingProfile] = useState<Profile | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const didInit = useRef(false);

  // Redirect if they skipped the NIM key step
  useEffect(() => {
    if (!nimKey) {
      router.replace("/onboarding/api-key");
    }
  }, [nimKey, router]);

  useEffect(() => {
    if (didInit.current || !accessToken || !nimKey) return;
    didInit.current = true;

    // 1. Ensure folder structure exists
    // 2. Check if profile already exists (re-onboarding after lost session)
    initialize(accessToken)
      .then(() =>
        getProfile(accessToken).catch((err: unknown) => {
          // New user: no profile.json yet — show blank form, not an error
          if (err instanceof ApiRequestError && err.detail.code === "PROFILE_NOT_FOUND") {
            return null;
          }
          throw err;
        }),
      )
      .then((profile) => {
        setExistingProfile(profile);
        setState("ready");
      })
      .catch((err: unknown) => {
        setErrorMsg(err instanceof Error ? err.message : "Setup failed. Please try again.");
        setState("error");
      });
  }, [accessToken, nimKey]);

  if (!nimKey) return null; // redirect in flight

  if (state === "loading") {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 size={24} className="animate-spin text-ink-faint" />
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="mx-auto max-w-2xl px-6 py-16">
        <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-5">
          <p className="text-sm font-medium text-red-700">Setup failed</p>
          <p className="mt-1 text-sm text-red-600">{errorMsg}</p>
          <button
            onClick={() => { didInit.current = false; setState("loading"); }}
            className="mt-4 rounded-lg bg-red-700 px-4 py-2 text-sm font-medium text-white hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      {/* Header */}
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-widest text-ink-faint">
          Step 2 of 2
        </p>
        <h1 className="mt-2 font-serif text-3xl font-semibold tracking-tight text-ink">
          {existingProfile ? "Update your profile" : "Build your profile"}
        </h1>
        <p className="mt-2 text-sm text-ink-soft">
          This becomes your achievement library. The AI tailors every résumé from
          these bullets — it never invents new ones.
        </p>
      </div>

      {existingProfile && (
        <div className="mb-6 flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
          <p className="text-sm text-emerald-700">
            Profile already set up. Update below or continue.
          </p>
          <button
            onClick={() => router.push("/dashboard")}
            className="ml-4 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600"
          >
            Go to dashboard →
          </button>
        </div>
      )}
      <ProfileForm
        initial={existingProfile ?? undefined}
        accessToken={accessToken!}
        nimKey={nimKey}
        onSaved={() => router.push("/dashboard")}
      />
    </div>
  );
}
