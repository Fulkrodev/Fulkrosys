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

type ClientApiInit = RequestInit & { json?: unknown };

const API_BASE = "/api/v1";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export async function clientApi<T = unknown>(
  path: string,
  init: ClientApiInit = {},
): Promise<T> {
  const { json, headers, ...rest } = init;
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
