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

export async function apiFetch<T>(
  path: string,
  { accessToken, nimKey, body, ...init }: FetchOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  if (nimKey) {
    headers["X-NIM-Key"] = nimKey;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

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
