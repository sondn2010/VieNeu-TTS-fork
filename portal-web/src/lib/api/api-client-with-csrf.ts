/**
 * `fetch` wrapper: adds `X-CSRF-Token` (from `GET /auth/csrf`) to every
 * mutating request, always sends `credentials: "same-origin"`, and parses
 * the error envelope into a typed `ApiError`.
 */
import { ApiError } from "./api-error";

let cachedCsrfToken: string | null = null;

async function fetchCsrfToken(): Promise<string> {
  const resp = await fetch("/api/v1/auth/csrf", { credentials: "same-origin" });
  if (!resp.ok) {
    throw new ApiError(resp.status, "CSRF_FETCH_FAILED", "could not fetch a CSRF token");
  }
  const body = (await resp.json()) as { csrf_token: string };
  return body.csrf_token;
}

export async function getCsrfToken(forceRefresh = false): Promise<string> {
  if (cachedCsrfToken && !forceRefresh) return cachedCsrfToken;
  cachedCsrfToken = await fetchCsrfToken();
  return cachedCsrfToken;
}

/** Test-only: clears the cached token so each test starts from the same
 * state, without resorting to `vi.resetModules()` (which would create a
 * second `ApiError` class instance and break `instanceof` checks). */
export function resetCsrfTokenCacheForTests(): void {
  cachedCsrfToken = null;
}

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** JSON-encoded as the body (sets Content-Type: application/json). */
  body?: unknown;
  /** The body as-is (e.g. FormData for a file upload) — never JSON-encoded. */
  rawBody?: BodyInit;
  /** Extra headers (e.g. `If-Match`) layered under the CSRF header. */
  headers?: Record<string, string>;
}

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

async function parseErrorEnvelope(resp: Response): Promise<ApiError> {
  let code = "ERROR";
  let message = `request failed with status ${resp.status}`;
  let extra: Record<string, unknown> = {};
  try {
    const body = (await resp.json()) as { error?: { code?: string; message?: string } & Record<string, unknown> };
    if (body.error) {
      const { code: bodyCode, message: bodyMessage, ...rest } = body.error;
      code = bodyCode ?? code;
      message = bodyMessage ?? message;
      extra = rest;
    }
  } catch {
    // Non-JSON error body: keep the generic defaults above.
  }
  return new ApiError(resp.status, code, message, extra);
}

export async function apiFetch<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { ...options.headers };
  let body: BodyInit | undefined;

  if (options.rawBody !== undefined) {
    body = options.rawBody;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  if (MUTATING_METHODS.has(method)) {
    headers["X-CSRF-Token"] = await getCsrfToken();
  }

  let resp = await fetch(path, { method, headers, body, credentials: "same-origin" });

  if (resp.status === 403 && MUTATING_METHODS.has(method)) {
    // The cached token may be stale (a new session, a rotated nonce) —
    // refresh once and retry exactly once.
    headers["X-CSRF-Token"] = await getCsrfToken(true);
    resp = await fetch(path, { method, headers, body, credentials: "same-origin" });
  }

  if (!resp.ok) {
    throw await parseErrorEnvelope(resp);
  }
  if (resp.status === 204) {
    return undefined as T;
  }
  return (await resp.json()) as T;
}
