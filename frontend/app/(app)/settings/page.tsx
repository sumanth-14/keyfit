"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  KeyRound,
  LogOut,
  ArrowRight,
} from "lucide-react";
import { useAuthStore } from "@/lib/store/auth";
import { saveNimKey } from "@/lib/nimKey";

export default function SettingsPage() {
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const userEmail = useAuthStore((s) => s.userEmail);
  const nimKey = useAuthStore((s) => s.nimKey);
  const setNimKey = useAuthStore((s) => s.setNimKey);
  const signOut = useAuthStore((s) => s.signOut);

  const [key, setKey] = useState("");
  const [visible, setVisible] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = key.trim();
    if (!trimmed.startsWith("nvapi-")) {
      setError('NVIDIA NIM keys start with "nvapi-". Check your key and try again.');
      return;
    }
    if (!accessToken || !userEmail) {
      setError("You must be signed in to save a key.");
      return;
    }
    setError(null);
    setSaved(false);
    setSaving(true);
    try {
      await saveNimKey(accessToken, userEmail, trimmed);
      setNimKey(trimmed);
      setKey("");
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save your key.");
    } finally {
      setSaving(false);
    }
  }

  function handleSignOut() {
    signOut();
    router.replace("/connect");
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="mb-8 font-serif text-3xl font-semibold tracking-tight text-ink">
        Settings
      </h1>

      {/* NIM key */}
      <section className="mb-6 rounded-2xl border border-line bg-paper-raised p-6">
        <div className="mb-4 flex items-center gap-2">
          <KeyRound size={18} className="text-ink-soft" />
          <h2 className="font-serif text-lg font-semibold text-ink">
            NVIDIA NIM API key
          </h2>
        </div>

        <div className="mb-4 rounded-lg bg-paper px-4 py-3 text-sm">
          {nimKey ? (
            <p className="flex items-center gap-2 text-ink-soft">
              <CheckCircle2 size={15} className="text-accent" />
              A key is active this session{" "}
              <span className="font-mono text-xs text-ink-faint">
                (nvapi-…{nimKey.slice(-4)})
              </span>
            </p>
          ) : (
            <p className="text-ink-soft">
              No key loaded. Enter one below to tailor résumés.
            </p>
          )}
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label
              htmlFor="nim-key"
              className="mb-1.5 block text-sm font-medium text-ink-soft"
            >
              {nimKey ? "Replace key" : "Add key"}
            </label>
            <div className="relative">
              <input
                id="nim-key"
                type={visible ? "text" : "password"}
                value={key}
                onChange={(e) => {
                  setKey(e.target.value);
                  setError(null);
                  setSaved(false);
                }}
                placeholder="nvapi-…"
                autoComplete="off"
                spellCheck={false}
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
            <p className="mt-1.5 text-xs text-ink-faint">
              Encrypted in your browser and stored in your own Google Drive. Sent
              directly to NVIDIA on each request; never stored on our servers.
            </p>
            {error && (
              <p className="mt-1.5 text-xs text-red-600">{error}</p>
            )}
            {saved && (
              <p className="mt-1.5 flex items-center gap-1.5 text-xs text-accent">
                <CheckCircle2 size={13} /> Saved to your Drive.
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={!key.trim() || saving}
            className="flex items-center justify-center gap-2 rounded-xl bg-ink px-5 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-accent disabled:opacity-50"
          >
            {saving && <Loader2 size={14} className="animate-spin" />}
            {saving ? "Saving…" : "Save key"}
          </button>
        </form>
      </section>

      {/* Account */}
      <section className="rounded-2xl border border-line bg-paper-raised p-6">
        <h2 className="mb-4 font-serif text-lg font-semibold text-ink">
          Account
        </h2>
        {userEmail && (
          <p className="mb-4 text-sm text-ink-soft">
            Signed in as{" "}
            <span className="font-medium text-ink">
              {userEmail}
            </span>
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => router.push("/profile")}
            className="flex items-center gap-2 rounded-xl border border-line px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-paper hover:text-ink"
          >
            Edit profile <ArrowRight size={14} />
          </button>
          <button
            onClick={handleSignOut}
            className="flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </section>
    </div>
  );
}
