"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, CheckCircle2 } from "lucide-react";
import { getProfile } from "@/lib/api/profile";
import { initialize } from "@/lib/api/setup";
import { ApiRequestError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/store/auth";
import ProfileForm from "@/components/onboarding/ProfileForm";
import type { Profile } from "@/lib/types";

type PageState = "loading" | "ready" | "error";

export default function ProfilePage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const nimKey = useAuthStore((s) => s.nimKey);
  const [state, setState] = useState<PageState>("loading");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const didInit = useRef(false);

  useEffect(() => {
    if (didInit.current || !accessToken) return;
    didInit.current = true;
    initialize(accessToken)
      .then(() =>
        getProfile(accessToken).catch((err: unknown) => {
          if (err instanceof ApiRequestError && err.detail.code === "PROFILE_NOT_FOUND") {
            return null;
          }
          throw err;
        }),
      )
      .then((p) => {
        setProfile(p);
        setState("ready");
      })
      .catch((err: unknown) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load profile.");
        setState("error");
      });
  }, [accessToken]);

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
          <p className="text-sm font-medium text-red-700">
            Couldn&rsquo;t load your profile
          </p>
          <p className="mt-1 text-sm text-red-600">{errorMsg}</p>
          <button
            onClick={() => {
              didInit.current = false;
              setState("loading");
            }}
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
      <div className="mb-8">
        <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink">
          Your profile
        </h1>
        <p className="mt-2 text-sm text-ink-soft">
          This is your achievement library. The AI tailors every résumé from these
          bullets — it never invents new ones, so keep them sharp and specific.
        </p>
      </div>

      {savedAt && (
        <div className="mb-6 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          <CheckCircle2 size={16} />
          Profile saved.
        </div>
      )}

      {!nimKey && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          No NIM key loaded — you can still edit fields manually, but importing from a
          résumé needs a key.{" "}
          <a href="/settings" className="font-medium underline">
            Add one in Settings
          </a>
          .
        </div>
      )}

      <ProfileForm
        initial={profile ?? undefined}
        accessToken={accessToken!}
        nimKey={nimKey ?? ""}
        onSaved={() => setSavedAt(Date.now())}
      />
    </div>
  );
}
