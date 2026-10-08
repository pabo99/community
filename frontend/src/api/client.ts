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
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new ApiError(response.status, `GET ${path} failed`);
  }
  return (await response.json()) as T;
}

export async function apiPost(path: string): Promise<void> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const csrf = readCookie(CSRF_COOKIE);
  if (csrf) {
    headers[CSRF_HEADER] = csrf;
  }
  const response = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    throw new ApiError(response.status, `POST ${path} failed`);
  }
}
