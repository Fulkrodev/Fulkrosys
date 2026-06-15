import { CSRF_HEADER } from "./constants";
import { getCsrfToken } from "./csrf";
import { detailToMessage } from "./utils";

/** Fetch wrapper that adds CSRF header on mutating calls and parses JSON. */

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data: unknown = null) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

type FetchInit = RequestInit & { json?: unknown };

export async function api<T = unknown>(path: string, init: FetchInit = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const method = (init.method ?? (json !== undefined ? "POST" : "GET")).toUpperCase();
  const finalHeaders = new Headers(headers);
  finalHeaders.set("Accept", "application/json");

  if (json !== undefined) {
    finalHeaders.set("Content-Type", "application/json");
  }

  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) finalHeaders.set(CSRF_HEADER, csrf);
  }

  const response = await fetch(path, {
    ...rest,
    method,
    headers: finalHeaders,
    credentials: "include",
    body: json !== undefined ? JSON.stringify(json) : init.body,
  });

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    throw new ApiError(
      response.status,
      detailToMessage(payload, response.statusText),
      payload,
    );
  }

  return payload as T;
}
