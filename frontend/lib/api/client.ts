import { useAuthStore } from "@/lib/store/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ApiError {
  code: string;
  stage?: string;
  user_message: string;
  retry_possible: boolean;
  trace_id: string;
}

export class ApiRequestError extends Error {
  constructor(
    public readonly detail: ApiError,
    public readonly status: number,
  ) {
    super(detail.user_message);
    this.name = "ApiRequestError";
  }
}

interface FetchOptions extends Omit<RequestInit, "body"> {
  accessToken?: string;
  nimKey?: string;
  body?: unknown;
}

// Shared so that many parallel 401s trigger a single refresh, not a stampede.
let refreshPromise: Promise<string | null> | null = null;

/** Exchange the stored refresh token for a new access token; updates the store. */
async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken } = useAuthStore.getState();
  if (!refreshToken) return null;
  try {
    const resp = await fetch(`${API_BASE}/api/auth/google/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resp.ok) return null;
    const data = (await resp.json()) as { access_token: string };
    useAuthStore.setState({ accessToken: data.access_token });
    return data.access_token;
  } catch {
    return null;
  }
}

function refreshOnce(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function apiFetch<T>(
  path: string,
  { accessToken, nimKey, body, ...init }: FetchOptions = {},
): Promise<T> {
  const serializedBody = body !== undefined ? JSON.stringify(body) : undefined;

  const buildHeaders = (token?: string): Record<string, string> => {
    const h: Record<string, string> = { ...(init.headers as Record<string, string>) };
    if (token) h["Authorization"] = `Bearer ${token}`;
    if (nimKey) h["X-NIM-Key"] = nimKey;
    if (body !== undefined) h["Content-Type"] = "application/json";
    return h;
  };

  let response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: buildHeaders(accessToken),
    body: serializedBody,
  });

  // The Google access token expires after ~1h. On a 401, transparently refresh
  // it once and retry, so the user isn't bounced back to the login screen.
  if (response.status === 401 && accessToken) {
    const newToken = await refreshOnce();
    if (newToken) {
      response = await fetch(`${API_BASE}${path}`, {
        ...init,
        headers: buildHeaders(newToken),
        body: serializedBody,
      });
    }
  }

  if (!response.ok) {
    let detail: ApiError;
    try {
      const json = await response.json();
      detail = json.error ?? {
        code: "UNKNOWN",
        user_message: response.statusText,
        retry_possible: false,
        trace_id: "",
      };
    } catch {
      detail = {
        code: "UNKNOWN",
        user_message: response.statusText,
        retry_possible: false,
        trace_id: "",
      };
    }
    throw new ApiRequestError(detail, response.status);
  }

  return response.json() as Promise<T>;
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
