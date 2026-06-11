"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Plus, KeyRound } from "lucide-react";
import { listApplications } from "@/lib/api/applications";
import { useAccessToken, useAuthStore } from "@/lib/store/auth";
import ApplicationsList from "@/components/dashboard/ApplicationsList";
import EmptyState from "@/components/dashboard/EmptyState";

export default function DashboardPage() {
  const accessToken = useAccessToken();
  const nimKey = useAuthStore((s) => s.nimKey);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["applications", accessToken],
    queryFn: () => listApplications(accessToken!),
    enabled: accessToken !== null,
  });

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      {/* NIM key missing banner */}
      {!nimKey && (
        <Link
          href="/onboarding/api-key"
          className="mb-6 flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm hover:bg-amber-100"
        >
          <KeyRound size={16} className="shrink-0 text-amber-600" />
          <span className="flex-1 text-amber-800">
            <span className="font-medium">NIM API key not set.</span> You need it to tailor résumés.
          </span>
          <span className="font-medium text-amber-700 underline">Add key →</span>
        </Link>
      )}

      {/* Page header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-serif text-2xl font-semibold tracking-tight text-ink">Applications</h1>
          {data && (
            <p className="mt-0.5 text-sm text-ink-soft">
              {data.total} {data.total === 1 ? "application" : "applications"}
            </p>
          )}
        </div>
        <Link
          href="/tailor"
          className="flex items-center gap-2 rounded-xl bg-ink px-4 py-2 text-sm font-medium text-paper transition-colors hover:bg-accent"
        >
          <Plus size={16} strokeWidth={2} />
          New application
        </Link>
      </div>

      {/* Content */}
      {isLoading && <LoadingSkeleton />}

      {isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error instanceof Error ? error.message : "Failed to load applications."}
        </div>
      )}

      {data && data.applications.length === 0 && <EmptyState />}

      {data && data.applications.length > 0 && (
        <ApplicationsList applications={data.applications} />
      )}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="flex items-center gap-4 rounded-xl border border-line bg-paper-raised px-5 py-4"
        >
          <div className="h-12 w-12 animate-pulse rounded-xl bg-paper" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-40 animate-pulse rounded bg-paper" />
            <div className="h-3 w-24 animate-pulse rounded bg-paper" />
          </div>
          <div className="h-3 w-20 animate-pulse rounded bg-paper" />
        </div>
      ))}
    </div>
  );
}
