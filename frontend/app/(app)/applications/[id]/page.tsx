"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { getApplication } from "@/lib/api/applications";
import { useAccessToken } from "@/lib/store/auth";
import CritiquePanel from "@/components/critique/CritiquePanel";
import OutreachPanel from "@/components/outreach/OutreachPanel";
import PdfViewer from "@/components/editor/PdfViewer";

type Tab = "resume" | "critique" | "outreach";

export default function ApplicationDetailPage() {
  const params = useParams<{ id: string }>();
  const accessToken = useAccessToken();
  const [activeTab, setActiveTab] = useState<Tab>("resume");

  const { data, isLoading, error } = useQuery({
    queryKey: ["application", params.id, accessToken],
    queryFn: () => getApplication(accessToken!, params.id),
    enabled: !!accessToken && !!params.id,
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 size={20} className="animate-spin text-ink-faint" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-5">
          <p className="text-sm text-red-700">
            {error instanceof Error ? error.message : "Application not found."}
          </p>
        </div>
      </div>
    );
  }

  const { manifest, current_version_data: cvd, outreach } = data;

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      {/* Header */}
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-ink-faint">
          Application
        </p>
        <h1 className="mt-1 font-serif text-3xl font-semibold tracking-tight text-ink">
          {manifest.company}
        </h1>
        <p className="mt-0.5 text-sm text-ink-soft">
          {manifest.role_title}
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex border-b border-line">
        {(["resume", "critique", "outreach"] as Tab[]).map((tab) => {
          const disabled = tab === "outreach" && !outreach;
          return (
            <button
              key={tab}
              type="button"
              onClick={() => !disabled && setActiveTab(tab)}
              disabled={disabled}
              className={`mr-4 pb-2.5 text-sm font-medium capitalize transition-colors ${
                activeTab === tab
                  ? "border-b-2 border-accent text-ink"
                  : disabled
                    ? "cursor-not-allowed text-ink-faint/50"
                    : "text-ink-faint hover:text-ink"
              }`}
            >
              {tab}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "resume" && (
          <PdfViewer pdfPath={cvd.pdf_url} accessToken={accessToken!} />
        )}

        {activeTab === "critique" &&
          (cvd.critique ? (
            <CritiquePanel critique={cvd.critique} />
          ) : (
            <p className="text-sm text-ink-faint">
              No critique available for this version.
            </p>
          ))}

        {activeTab === "outreach" && outreach && (
          <OutreachPanel outreach={outreach} />
        )}
      </div>
    </div>
  );
}
