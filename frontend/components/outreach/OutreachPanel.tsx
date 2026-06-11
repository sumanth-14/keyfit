"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";
import type { OutreachMessages } from "@/lib/types";

interface Props {
  outreach: OutreachMessages;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-ink-soft transition-colors hover:bg-paper hover:text-ink"
    >
      {copied ? (
        <Check size={12} className="text-accent" />
      ) : (
        <Copy size={12} />
      )}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

interface MessageCardProps {
  label: string;
  subject?: string;
  body: string;
}

function MessageCard({ label, subject, body }: MessageCardProps) {
  const fullText = subject ? `Subject: ${subject}\n\n${body}` : body;

  return (
    <div className="rounded-xl border border-line bg-paper-raised p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-widest text-ink-faint">
          {label}
        </p>
        <CopyButton text={fullText} />
      </div>
      {subject && (
        <p className="mb-2 text-sm font-medium text-ink">
          Subject: {subject}
        </p>
      )}
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-soft">
        {body}
      </p>
    </div>
  );
}

export default function OutreachPanel({ outreach }: Props) {
  return (
    <div className="space-y-4">
      <MessageCard
        label="Cold Email"
        subject={outreach.cold_email_subject}
        body={outreach.cold_email_body}
      />
      <MessageCard
        label="LinkedIn Connection Note"
        body={outreach.linkedin_connection_note}
      />
      <MessageCard
        label="LinkedIn InMail"
        subject={outreach.linkedin_inmail_subject}
        body={outreach.linkedin_inmail_body}
      />
    </div>
  );
}
