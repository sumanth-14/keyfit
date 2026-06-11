"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useIsAuthenticated } from "@/lib/store/auth";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const getPersist = () => (useAuthStore as any).persist as {
  hasHydrated: () => boolean;
  onFinishHydration: (fn: () => void) => () => void;
};

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useIsAuthenticated();
  const router = useRouter();

  // SSR always returns false (no localStorage). On client, check if already hydrated.
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const persist = getPersist();
    // Already hydrated (e.g. client-side navigation between pages)
    if (persist.hasHydrated()) {
      setHydrated(true);
      return;
    }
    // Wait for Zustand to finish reading from localStorage
    const unsub = persist.onFinishHydration(() => setHydrated(true));
    return unsub;
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) {
      router.replace("/connect");
    }
  }, [hydrated, isAuthenticated, router]);

  if (!hydrated) return null;
  if (!isAuthenticated) return null;
  return <>{children}</>;
}
