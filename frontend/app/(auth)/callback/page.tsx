"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { exchangeCode } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/store/auth";

type CallbackStatus = "loading" | "error";

function CallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [status, setStatus] = useState<CallbackStatus>("loading");
  const [errorMsg, setErrorMsg] = useState<string>("");
  const didRun = useRef(false);

  useEffect(() => {
    // Strict Mode mounts twice in dev — guard with a ref so we only run once
    if (didRun.current) return;
    didRun.current = true;

    const code = searchParams.get("code");
    const returnedState = searchParams.get("state");
    const oauthError = searchParams.get("error");

    if (oauthError) {
      setErrorMsg(`Google returned an error: ${oauthError}`);
      setStatus("error");
      return;
    }

    if (!code || !returnedState) {
      setErrorMsg("Missing authorization code or state. Please try again.");
      setStatus("error");
      return;
    }

    // CSRF: compare returned state to what we stored before redirecting
    const savedState = sessionStorage.getItem("oauth_state");
    if (savedState !== returnedState) {
      setErrorMsg("State mismatch — possible CSRF. Please try again.");
      setStatus("error");
      return;
    }
    const codeVerifier = sessionStorage.getItem("oauth_code_verifier") ?? "";
    sessionStorage.removeItem("oauth_state");
    sessionStorage.removeItem("oauth_code_verifier");

    exchangeCode(code, returnedState, codeVerifier)
      .then(({ access_token, refresh_token, user_email, tailor_folder_exists }) => {
        setAuth({
          accessToken: access_token,
          refreshToken: refresh_token,
          userEmail: user_email,
          tailorFolderExists: tailor_folder_exists,
        });
        router.replace(tailor_folder_exists ? "/dashboard" : "/onboarding/api-key");
      })
      .catch((err: unknown) => {
        const msg =
          err instanceof Error ? err.message : "Authentication failed. Please try again.";
        setErrorMsg(msg);
        setStatus("error");
      });
  }, [searchParams, setAuth, router]);

  if (status === "loading") {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <span className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-accent" />
        <p className="text-sm text-ink-soft">Completing sign-in…</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md rounded-2xl border border-red-200 bg-paper-raised p-10 shadow-sm">
      <h2 className="mb-2 font-serif text-xl font-semibold text-red-700">
        Sign-in failed
      </h2>
      <p className="mb-6 text-sm text-ink-soft">{errorMsg}</p>
      <a
        href="/connect"
        className="inline-block rounded-xl bg-ink px-5 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-accent"
      >
        Try again
      </a>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center gap-4 text-center">
          <span className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-accent" />
          <p className="text-sm text-ink-soft">Loading…</p>
        </div>
      }
    >
      <CallbackInner />
    </Suspense>
  );
}
