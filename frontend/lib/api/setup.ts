import { apiFetch } from "./client";

export interface SetupResponse {
  initialized: boolean;
  root_folder_id: string;
}

export async function initialize(accessToken: string): Promise<SetupResponse> {
  return apiFetch<SetupResponse>("/api/setup/initialize", {
    accessToken,
    method: "POST",
  });
}
