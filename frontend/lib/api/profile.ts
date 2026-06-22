import type { ParseFromResumeResponse, Profile } from "@/lib/types";
import { apiFetch, apiUrl, ApiRequestError } from "./client";

export async function getProfile(accessToken: string): Promise<Profile | null> {
  try {
    return await apiFetch<Profile>("/api/profile", { accessToken });
  } catch (err) {
    // 404 → profile not created yet, return null
    if (err instanceof ApiRequestError && err.status === 404) return null;
    throw err;
  }
}

export async function updateProfile(
  accessToken: string,
  profile: Profile,
): Promise<Profile> {
  return apiFetch<Profile>("/api/profile", {
    accessToken,
    method: "PUT",
    body: profile,
  });
}

export async function parseFromResume(
  accessToken: string,
  nimKey: string,
  file: File,
  format = "tex",
): Promise<ParseFromResumeResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("format", format);

  // Hard client-side ceiling so the UI never hangs longer than the user will
  // tolerate, even if the backend or network stalls. Backend caps itself at ~25s.
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 35_000);

  let response: Response;
  try {
    response = await fetch(apiUrl("/api/profile/parse-from-resume"), {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "X-NIM-Key": nimKey,
      },
      body: formData,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiRequestError(
        {
          code: "TIMEOUT",
          user_message:
            "Parsing took too long. Please try uploading again — if it keeps happening, fill the form in manually.",
          retry_possible: true,
          trace_id: "",
        },
        408,
      );
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    let detail;
    try {
      const json = await response.json();
      detail = json.error ?? { code: "UNKNOWN", user_message: response.statusText, retry_possible: false, trace_id: "" };
    } catch {
      detail = { code: "UNKNOWN", user_message: response.statusText, retry_possible: false, trace_id: "" };
    }
    throw new ApiRequestError(detail, response.status);
  }

  return response.json() as Promise<ParseFromResumeResponse>;
}
