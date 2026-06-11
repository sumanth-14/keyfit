"use client";

import { useEffect, useState } from "react";
import { getAuthUrl } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/store/auth";

export default function ConnectPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const signOut = useAuthStore((s) => s.signOut);

  // Clear any stale auth on mount — must be in useEffect, not useState initializer
  useEffect(() => {
    signOut();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleConnect() {
    setLoading(true);
    setError(null);
    try {
      const { auth_url, state, code_verifier } = await getAuthUrl();
      sessionStorage.setItem("oauth_state", state);
      sessionStorage.setItem("oauth_code_verifier", code_verifier);
      window.location.href = auth_url;
    } catch {
      setError("Could not reach the server. Make sure the backend is running.");
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-md">
      <div className="rounded-2xl border border-line bg-paper-raised p-10 shadow-sm">
        {/* Wordmark */}
        <div className="mb-8 text-center">
          <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink">
            Tailored to the job.
            <br />
            <span className="italic text-accent">Owned by you.</span>
          </h1>
          <p className="mt-3 text-sm text-ink-soft">
            Connect your Google Drive to get started — it&rsquo;s where
            everything you make will live.
          </p>
        </div>

        {/* Value props */}
        <ul className="mb-8 space-y-2.5 text-sm text-ink-soft">
          {[
            "Tailors your résumé to each job description",
            "Scores your match and shows what to fix",
            "Generates outreach messages",
            "Everything saves to your own Google Drive",
          ].map((item) => (
            <li key={item} className="flex items-start gap-2.5">
              <span className="mt-0.5 text-accent">✓</span>
              {item}
            </li>
          ))}
        </ul>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          onClick={handleConnect}
          disabled={loading}
          className="flex w-full items-center justify-center gap-3 rounded-xl bg-ink px-4 py-3 text-sm font-medium text-paper transition-colors hover:bg-accent disabled:opacity-60"
        >
          {loading ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-paper border-t-transparent" />
          ) : (
            <GoogleIcon />
          )}
          {loading ? "Redirecting…" : "Connect Google Drive"}
        </button>

        <p className="mt-5 text-center text-xs text-ink-faint">
          We only read and write inside a{" "}
          <span className="font-medium text-ink-soft">Resume_Tailor/</span>{" "}
          folder we create for you. Your other Drive files are never accessed.
        </p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
      <path
        d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908C16.658 14.013 17.64 11.799 17.64 9.2z"
        fill="#4285F4"
      />
      <path
        d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"
        fill="#34A853"
      />
      <path
        d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"
        fill="#FBBC05"
      />
      <path
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"
        fill="#EA4335"
      />
    </svg>
  );
}
