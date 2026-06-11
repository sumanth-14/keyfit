"use client";

import { useCallback, useRef, useState } from "react";
import { apiUrl } from "@/lib/api/client";
import type { PipelineStage } from "@/lib/types";

export type StageStatus = "pending" | "running" | "complete" | "failed";

export interface StageState {
  stage: PipelineStage;
  status: StageStatus;
  error?: string;
}

export type StreamStatus = "idle" | "streaming" | "complete" | "failed";

export interface UsePipelineStreamResult {
  stages: StageState[];
  streamStatus: StreamStatus;
  applicationId: string | null;
  error: string | null;
  start: (jobId: string, accessToken: string) => void;
  stop: () => void;
}

const ALL_STAGES: PipelineStage[] = [
  "scrape",
  "jd_analyzer",
  "tailor",
  "compile",
  "critique",
  "outreach",
  "persist",
];

function initialStages(): StageState[] {
  return ALL_STAGES.map((stage) => ({ stage, status: "pending" }));
}

export function usePipelineStream(): UsePipelineStreamResult {
  const [stages, setStages] = useState<StageState[]>(initialStages());
  const [streamStatus, setStreamStatus] = useState<StreamStatus>("idle");
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const start = useCallback((jobId: string, accessToken: string) => {
    setStages(initialStages());
    setStreamStatus("streaming");
    setApplicationId(null);
    setError(null);

    const controller = new AbortController();
    abortRef.current = controller;

    async function consume() {
      // Local variables track terminal state to avoid stale-closure reads
      let terminalStatus: StreamStatus = "complete";
      let terminalError: string | null = null;
      let terminalAppId: string | null = null;

      try {
        const response = await fetch(apiUrl(`/api/pipeline/${jobId}/stream`), {
          headers: { Authorization: `Bearer ${accessToken}` },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Stream failed: ${response.statusText}`);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let keepReading = true;

        while (keepReading) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // SSE events are delimited by \n\n
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            const trimmed = part.trim();
            if (!trimmed || trimmed.startsWith(":")) continue; // keepalive

            let eventType = "message";
            let dataStr = "";

            for (const line of trimmed.split("\n")) {
              if (line.startsWith("event: ")) {
                eventType = line.slice(7).trim();
              } else if (line.startsWith("data: ")) {
                dataStr = line.slice(6).trim();
              }
            }

            if (!dataStr) continue;

            let data: Record<string, unknown>;
            try {
              data = JSON.parse(dataStr) as Record<string, unknown>;
            } catch {
              continue;
            }

            if (eventType === "stage_started") {
              const stage = data.stage as PipelineStage;
              setStages((prev) =>
                prev.map((s) =>
                  s.stage === stage ? { ...s, status: "running" } : s,
                ),
              );
            } else if (eventType === "stage_completed") {
              const stage = data.stage as PipelineStage;
              setStages((prev) =>
                prev.map((s) =>
                  s.stage === stage ? { ...s, status: "complete" } : s,
                ),
              );
            } else if (eventType === "stage_failed") {
              const stage = data.stage as PipelineStage;
              const errData = data.error as Record<string, unknown> | undefined;
              const errMsg =
                (errData?.user_message as string | undefined) ?? "Stage failed";
              setStages((prev) =>
                prev.map((s) =>
                  s.stage === stage
                    ? { ...s, status: "failed", error: errMsg }
                    : s,
                ),
              );
              terminalStatus = "failed";
              terminalError = errMsg;
              keepReading = false;
            } else if (eventType === "pipeline_complete") {
              terminalAppId = data.application_id as string;
              terminalStatus = "complete";
              keepReading = false;
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        terminalStatus = "failed";
        terminalError = err instanceof Error ? err.message : "Stream failed";
      }

      // Apply terminal state all at once (avoids stale-closure status check)
      if (terminalAppId) setApplicationId(terminalAppId);
      if (terminalError) setError(terminalError);
      setStreamStatus(terminalStatus);
    }

    consume();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { stages, streamStatus, applicationId, error, start, stop };
}
