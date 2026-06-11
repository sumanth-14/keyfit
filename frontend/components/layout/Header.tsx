"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { useAuthStore } from "@/lib/store/auth";

export default function Header() {
  const router = useRouter();
  const userEmail = useAuthStore((s) => s.userEmail);
  const signOut = useAuthStore((s) => s.signOut);

  function handleSignOut() {
    signOut();
    router.push("/connect");
  }

  return (
    <header className="flex h-14 items-center justify-end gap-4 border-b border-line bg-paper-raised px-6">
      {userEmail && (
        <span className="text-sm text-ink-soft">{userEmail}</span>
      )}
      <button
        onClick={handleSignOut}
        title="Sign out"
        className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm text-ink-soft transition-colors hover:bg-paper hover:text-ink"
      >
        <LogOut size={14} strokeWidth={1.75} />
        Sign out
      </button>
    </header>
  );
}
