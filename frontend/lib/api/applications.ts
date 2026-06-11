import type { ApplicationDetail, ApplicationListResponse, VersionData } from "@/lib/types";
import { apiFetch } from "./client";

export async function listApplications(
  accessToken: string,
  limit = 50,
  offset = 0,
): Promise<ApplicationListResponse> {
  return apiFetch<ApplicationListResponse>(
    `/api/applications?limit=${limit}&offset=${offset}`,
    { accessToken },
  );
}

export async function getApplication(
  accessToken: string,
  applicationId: string,
): Promise<ApplicationDetail> {
  return apiFetch<ApplicationDetail>(`/api/applications/${applicationId}`, {
    accessToken,
  });
}

export async function getApplicationVersion(
  accessToken: string,
  applicationId: string,
  version: number,
): Promise<VersionData> {
  return apiFetch<VersionData>(
    `/api/applications/${applicationId}/version/${version}`,
    { accessToken },
  );
}

export async function setCurrentVersion(
  accessToken: string,
  applicationId: string,
  version: number,
): Promise<{ current_version: number }> {
  return apiFetch<{ current_version: number }>(
    `/api/applications/${applicationId}/set-current`,
    { accessToken, method: "POST", body: { version } },
  );
}

export async function deleteApplication(
  accessToken: string,
  applicationId: string,
): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(
    `/api/applications/${applicationId}`,
    { accessToken, method: "DELETE" },
  );
}
