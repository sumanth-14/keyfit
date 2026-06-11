export interface OutreachOptions {
  enabled: boolean;
  tone?: "professional" | "casual" | "enthusiastic";
  contact_name?: string;
  contact_type?: string;
}

export interface PipelineRequest {
  job_url?: string;
  job_description?: string;
  company_name: string;
  role_title: string;
  role_config_id: string;
  outreach: OutreachOptions;
}

export interface PipelineRunResponse {
  job_id: string;
  stream_url: string;
  new: boolean;
}

export type PipelineStage =
  | "scrape"
  | "jd_analyzer"
  | "tailor"
  | "compile"
  | "critique"
  | "outreach"
  | "persist";

export type PipelineStatus = "running" | "complete" | "failed";

export interface PipelineResultResponse {
  job_id: string;
  status: PipelineStatus;
  application_id?: string;
  pdf_url?: string;
  error?: {
    code: string;
    stage: string;
    user_message: string;
    retry_possible: boolean;
    trace_id: string;
  };
}

export interface RetailorRequest {
  application_id: string;
  job_description?: string;
  notes?: string;
}

// SSE event payloads
export interface StageStartedEvent {
  stage: PipelineStage;
  job_id: string;
}

export interface StageCompletedEvent {
  stage: PipelineStage;
  job_id: string;
}

export interface StageFailedEvent {
  stage: PipelineStage;
  job_id: string;
  error: string;
  retry_possible: boolean;
}

export interface PipelineCompleteEvent {
  job_id: string;
  application_id: string;
  pdf_url: string;
}
