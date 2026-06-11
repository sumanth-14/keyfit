import { apiFetch } from "./client";

export interface AuthUrlResponse {
  auth_url: string;
  state: string;
  code_verifier: string;
}

export interface OAuthCallbackResponse {
  access_token: string;
  refresh_token?: string;
  user_email: string;
  tailor_folder_exists: boolean;
}

export async function getAuthUrl(): Promise<AuthUrlResponse> {
  return apiFetch<AuthUrlResponse>("/api/auth/google/url");
}

export async function exchangeCode(
  code: string,
  state: string,
  codeVerifier: string,
): Promise<OAuthCallbackResponse> {
  return apiFetch<OAuthCallbackResponse>("/api/auth/google/callback", {
    method: "POST",
    body: { code, state, code_verifier: codeVerifier },
  });
}
