import type { CritiqueColor, CritiqueVerdict, Critique } from "./critique";

export interface ApplicationFiles {
  tex: string;
  pdf: string;
  critique: string;
}

export interface ApplicationVersion {
  version: number;
  score: number;
  verdict: CritiqueVerdict;
  color: CritiqueColor;
  files: ApplicationFiles;
}

export interface ApplicationManifest {
  application_id: string;
  company: string;
  role_title: string;
  role_config_used: string;
  created_at: string;
  current_version: number;
  status: string;
  versions: ApplicationVersion[];
  outreach_file?: string;
}

export interface ApplicationListItem {
  application_id: string;
  folder_name: string;
  company: string;
  role_title: string;
  created_at: string;
  current_version: number;
  score: number;
  verdict: CritiqueVerdict;
  color: CritiqueColor;
  status: string;
}

export interface ApplicationListResponse {
  applications: ApplicationListItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface VersionData {
  tex_source: string;
  pdf_url: string;
  critique: Critique | null;
}

export interface OutreachMessages {
  cold_email_subject: string;
  cold_email_body: string;
  linkedin_connection_note: string;
  linkedin_inmail_subject: string;
  linkedin_inmail_body: string;
}

export interface ApplicationDetail {
  manifest: ApplicationManifest;
  current_version_data: VersionData;
  outreach?: OutreachMessages;
}
