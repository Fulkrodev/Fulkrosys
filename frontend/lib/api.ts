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

/** Default request timeout (ms) before an in-flight fetch is aborted. */
export const DEFAULT_TIMEOUT_MS = 30_000;

type FetchInit = RequestInit & { json?: unknown; timeoutMs?: number };

/**
 * Builds an AbortSignal that aborts on timeout, on caller's signal, or both.
 * Falls back gracefully when AbortSignal.any/timeout are unavailable.
 */
function buildSignal(timeoutMs: number, callerSignal?: AbortSignal | null): AbortSignal | undefined {
  const hasTimeout = typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function";
  const timeoutSignal = hasTimeout && timeoutMs > 0 ? AbortSignal.timeout(timeoutMs) : undefined;
  if (!callerSignal) return timeoutSignal;
  if (!timeoutSignal) return callerSignal;
  if (typeof AbortSignal.any === "function") {
    return AbortSignal.any([callerSignal, timeoutSignal]);
  }
  // Older runtimes without AbortSignal.any: prefer caller cancellation.
  return callerSignal;
}

export async function api<T = unknown>(path: string, init: FetchInit = {}): Promise<T> {
  const { json, headers, timeoutMs, signal: callerSignal, ...rest } = init;
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
    signal: buildSignal(timeoutMs ?? DEFAULT_TIMEOUT_MS, callerSignal),
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
