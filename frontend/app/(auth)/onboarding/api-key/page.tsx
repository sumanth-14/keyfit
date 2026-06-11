"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { useAuthStore } from "@/lib/store/auth";
import { saveNimKey } from "@/lib/nimKey";

export default function ApiKeyPage() {
  const router = useRouter();
  const setNimKey = useAuthStore((s) => s.setNimKey);
  const accessToken = useAuthStore((s) => s.accessToken);
  const userEmail = useAuthStore((s) => s.userEmail);
  const [key, setKey] = useState("");
  const [visible, setVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = key.trim();
    if (!trimmed.startsWith("nvapi-")) {
      setError('NVIDIA NIM keys start with "nvapi-". Check your key and try again.');
      return;
    }
    setNimKey(trimmed);
    // Encrypt and store in the user's Drive so they never re-enter it.
    // Non-fatal if it fails — the key is still in memory for this session.
    if (accessToken && userEmail) {
      setSaving(true);
      try {
        await saveNimKey(accessToken, userEmail, trimmed);
      } catch {
        /* ignore — Settings page can re-save later */
      } finally {
        setSaving(false);
      }
    }
    router.push("/onboarding/profile");
  }

  return (
    <div className="w-full max-w-md">
      <div className="rounded-2xl border border-line bg-paper-raised p-10 shadow-sm">
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-widest text-ink-faint">
            Step 1 of 2
          </p>
          <h1 className="mt-2 font-serif text-3xl font-semibold tracking-tight text-ink">
            Add your NVIDIA NIM key
          </h1>
          <p className="mt-2 text-sm text-ink-soft">
            Keyfit uses NVIDIA&rsquo;s free LLM API. You need your own key — it stays
            in your browser and is never stored on our servers.
          </p>
        </div>

        <div className="mb-6 rounded-xl bg-paper px-4 py-3 text-sm">
          <p className="font-medium text-ink">
            Get a free key in 2 minutes:
          </p>
          <ol className="mt-2 list-decimal space-y-1 pl-4 text-ink-soft">
            <li>
              Go to{" "}
              <span className="font-mono text-xs text-ink">
                build.nvidia.com
              </span>
            </li>
            <li>Sign in and click &ldquo;Get API Key&rdquo;</li>
            <li>Copy the key that starts with{" "}
              <span className="font-mono text-xs">nvapi-</span>
            </li>
          </ol>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="nim-key"
              className="mb-1.5 block text-sm font-medium text-ink-soft"
            >
              NVIDIA NIM API Key
            </label>
            <div className="relative">
              <input
                id="nim-key"
                type={visible ? "text" : "password"}
                value={key}
                onChange={(e) => { setKey(e.target.value); setError(null); }}
                placeholder="nvapi-…"
                autoComplete="off"
                spellCheck={false}
                required
                className="w-full rounded-xl border border-line bg-paper-raised px-4 py-2.5 pr-10 text-sm font-mono text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <button
                type="button"
                onClick={() => setVisible((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint transition-colors hover:text-ink"
                aria-label={visible ? "Hide key" : "Show key"}
              >
                {visible ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {error && (
              <p className="mt-1.5 text-xs text-red-600">{error}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={!key.trim() || saving}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-ink px-4 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-accent disabled:opacity-50"
          >
            {saving && <Loader2 size={14} className="animate-spin" />}
            {saving ? "Saving…" : "Save and continue"}
          </button>
        </form>

        <p className="mt-5 text-center text-xs text-ink-faint">
          Your key is encrypted in your browser and stored in your own Google Drive,
          so you won&rsquo;t need to re-enter it. It is sent directly to NVIDIA on each
          request and never stored on our infrastructure.
        </p>
      </div>
    </div>
  );
}
