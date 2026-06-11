"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { apiUrl } from "@/lib/api/client";

interface Props {
  pdfPath: string; // e.g. "/api/files/abc123"
  accessToken: string;
}

export default function PdfViewer({ pdfPath, accessToken }: Props) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    setLoading(true);
    setError(null);
    setBlobUrl(null);

    fetch(apiUrl(pdfPath), {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load PDF (${res.status})`);
        return res.blob();
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load PDF.");
      })
      .finally(() => setLoading(false));

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [pdfPath, accessToken]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center rounded-xl border border-line bg-paper-raised">
        <Loader2 size={20} className="animate-spin text-ink-faint" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-96 items-center justify-center rounded-xl border border-red-200 bg-red-50">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <iframe
      src={blobUrl!}
      className="h-[72vh] w-full rounded-xl border border-line"
      title="Résumé PDF"
    />
  );
}
