// Minimal fetch wrapper for the same-origin REST API.
//
// All requests use relative /api paths and include credentials so the HttpOnly
// session cookie is sent. No HTTP library is introduced (native fetch only).
// For mutations, the double-submit CSRF token is read from the readable CSRF
// cookie and echoed in the X-CSRF-Token header.

const CSRF_COOKIE = "community_csrf";
const CSRF_HEADER = "X-CSRF-Token";

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export class ApiError extends Error {
  // `body` carries the parsed error payload (e.g. FastAPI's { detail }) when
  // available, so callers can surface 409 conflict messages and 422 field
  // errors. Optional and defaulted for backward compatibility.
  constructor(
    public readonly status: number,
    message: string,
    public readonly body: unknown = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseBody(response: Response): Promise<unknown> {
  const contentType = response.headers?.get?.("content-type") ?? "";
  // Treat a missing/absent content-type as "attempt JSON" so callers still get
  // a parsed body when the header is unavailable; fall back to null on failure.
  if (contentType && !contentType.includes("application/json")) {
    return null;
  }
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function mutationHeaders(hasBody: boolean): Record<string, string> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (hasBody) {
    headers["Content-Type"] = "application/json";
  }
  const csrf = readCookie(CSRF_COOKIE);
  if (csrf) {
    headers[CSRF_HEADER] = csrf;
  }
  return headers;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new ApiError(response.status, `GET ${path} failed`, await parseBody(response));
  }
  return (await response.json()) as T;
}

export async function apiPost<T = void>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: mutationHeaders(body !== undefined),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new ApiError(response.status, `POST ${path} failed`, await parseBody(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await parseBody(response)) as T;
}

export async function apiPatch<T = void>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "PATCH",
    credentials: "include",
    headers: mutationHeaders(body !== undefined),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new ApiError(response.status, `PATCH ${path} failed`, await parseBody(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await parseBody(response)) as T;
}

export async function apiDelete(path: string): Promise<void> {
  const response = await fetch(path, {
    method: "DELETE",
    credentials: "include",
    headers: mutationHeaders(false),
  });
  if (!response.ok) {
    throw new ApiError(response.status, `DELETE ${path} failed`, await parseBody(response));
  }
}

// Extracts field-level validation errors from a FastAPI 422 response body into
// a { field: message } map. Model-level errors (loc without a field) are keyed
// under "__root__".
export function parseValidationErrors(body: unknown): Record<string, string> {
  const result: Record<string, string> = {};
  if (
    body &&
    typeof body === "object" &&
    "detail" in body &&
    Array.isArray((body as { detail: unknown }).detail)
  ) {
    for (const item of (body as { detail: Array<Record<string, unknown>> }).detail) {
      const loc = Array.isArray(item.loc) ? item.loc : [];
      // loc is typically ["body", "<field>"]; last string segment is the field.
      const field =
        typeof loc[loc.length - 1] === "string" ? String(loc[loc.length - 1]) : "__root__";
      const key = field === "body" ? "__root__" : field;
      result[key] = typeof item.msg === "string" ? item.msg : "Invalid value";
    }
  }
  return result;
}

// Extracts a human-readable message from an error body (FastAPI { detail: str }).
export function errorDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return fallback;
}
