"use client";

/**
 * Cliente API ligero para el portal cliente.
 *
 * Sesión gestionada por cookies httpOnly seteadas por el backend
 * (`fulkro_session`) + cookie CSRF no httpOnly (`fulkro_csrf`).
 * Frontend solo envía cookies (`credentials: "include"`) y añade
 * el header `X-CSRF-Token` en métodos mutantes. No hay token JWT
 * en localStorage — la cookie de sesión es invisible a JS por
 * diseño (mitiga XSS-token theft).
 *
 * Ver ADR-019 (CSRF triple binding).
 */

import { CSRF_HEADER } from "./constants";
import { getCsrfToken } from "./csrf";
import { detailToMessage } from "./utils";

export class ClientApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, message: string, data: unknown = null) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

type ClientApiInit = RequestInit & { json?: unknown; timeoutMs?: number };

const API_BASE = "/api/v1";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

/** Default request timeout (ms) before an in-flight fetch is aborted. */
export const DEFAULT_TIMEOUT_MS = 30_000;

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

export async function clientApi<T = unknown>(
  path: string,
  init: ClientApiInit = {},
): Promise<T> {
  const { json, headers, timeoutMs, signal: callerSignal, ...rest } = init;
  const method = (init.method ?? (json !== undefined ? "POST" : "GET")).toUpperCase();
  const finalHeaders = new Headers(headers);
  finalHeaders.set("Accept", "application/json");
  if (json !== undefined) {
    finalHeaders.set("Content-Type", "application/json");
  }
  if (!SAFE_METHODS.has(method)) {
    const csrf = getCsrfToken();
    if (csrf) finalHeaders.set(CSRF_HEADER, csrf);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    method,
    headers: finalHeaders,
    credentials: "include",
    signal: buildSignal(timeoutMs ?? DEFAULT_TIMEOUT_MS, callerSignal),
    body: json !== undefined ? JSON.stringify(json) : init.body,
  });

  const ct = response.headers.get("content-type") ?? "";
  const payload = ct.includes("application/json") ? await response.json().catch(() => null) : null;
  if (!response.ok) {
    throw new ClientApiError(
      response.status,
      detailToMessage(payload, response.statusText),
      payload,
    );
  }
  return payload as T;
}

export interface ClientLoginResponse {
  must_change_password: boolean;
  role: string;
  full_name: string | null;
}

export interface ClientMeResponse {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  scopes: string[];
  must_change_password: boolean;
}
