"use client";

import { useEffect, useRef } from "react";
import { useAuthStore } from "@/lib/store/auth";
import { loadNimKey } from "@/lib/nimKey";

/**
 * Auto-unlock: once authenticated, if the NIM key isn't in memory, fetch the
 * encrypted blob from Drive and decrypt it so users don't re-enter it each
 * session. Renders nothing.
 */
export default function NimKeyLoader() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const userEmail = useAuthStore((s) => s.userEmail);
  const nimKey = useAuthStore((s) => s.nimKey);
  const setNimKey = useAuthStore((s) => s.setNimKey);
  const attempted = useRef(false);

  useEffect(() => {
    if (nimKey || !accessToken || !userEmail || attempted.current) return;
    attempted.current = true;
    loadNimKey(accessToken, userEmail)
      .then((key) => {
        if (key) setNimKey(key);
      })
      .catch(() => {
        /* no stored key yet — user will enter one */
      });
  }, [accessToken, userEmail, nimKey, setNimKey]);

  return null;
}
