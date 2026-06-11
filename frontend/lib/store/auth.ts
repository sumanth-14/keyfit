"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  userEmail: string | null;
  nimKey: string | null; // memory-only, never persisted
  tailorFolderExists: boolean;
}

interface AuthActions {
  setAuth: (params: {
    accessToken: string;
    refreshToken?: string;
    userEmail: string;
    tailorFolderExists: boolean;
  }) => void;
  setNimKey: (key: string) => void;
  clearNimKey: () => void;
  signOut: () => void;
}

const initialState: AuthState = {
  accessToken: null,
  refreshToken: null,
  userEmail: null,
  nimKey: null,
  tailorFolderExists: false,
};

export const useAuthStore = create<AuthState & AuthActions>()(
  persist(
    (set) => ({
      ...initialState,

      setAuth: ({ accessToken, refreshToken, userEmail, tailorFolderExists }) =>
        set({ accessToken, refreshToken: refreshToken ?? null, userEmail, tailorFolderExists }),

      setNimKey: (key) => set({ nimKey: key }),

      clearNimKey: () => set({ nimKey: null }),

      signOut: () => set(initialState),
    }),
    {
      name: "resume-tailor-auth",
      // Never persist nimKey — user re-enters it each session
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        userEmail: state.userEmail,
        tailorFolderExists: state.tailorFolderExists,
      }),
    },
  ),
);

export function useIsAuthenticated(): boolean {
  return useAuthStore((s) => s.accessToken !== null);
}

export function useAccessToken(): string | null {
  return useAuthStore((s) => s.accessToken);
}
