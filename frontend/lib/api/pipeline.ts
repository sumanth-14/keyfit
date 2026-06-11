import type {
  PipelineRequest,
  PipelineRunResponse,
  PipelineResultResponse,
  RetailorRequest,
} from "@/lib/types";
import { apiFetch } from "./client";

export async function runPipeline(
  accessToken: string,
  nimKey: string,
  request: PipelineRequest,
): Promise<PipelineRunResponse> {
  return apiFetch<PipelineRunResponse>("/api/pipeline/run", {
    method: "POST",
    accessToken,
    nimKey,
    body: request,
  });
}

export async function getPipelineResult(
  accessToken: string,
  jobId: string,
): Promise<PipelineResultResponse> {
  return apiFetch<PipelineResultResponse>(`/api/pipeline/${jobId}/result`, {
    accessToken,
  });
}

export async function retailorPipeline(
  accessToken: string,
  nimKey: string,
  request: RetailorRequest,
): Promise<PipelineRunResponse> {
  return apiFetch<PipelineRunResponse>("/api/pipeline/retailor", {
    method: "POST",
    accessToken,
    nimKey,
    body: request,
  });
}
