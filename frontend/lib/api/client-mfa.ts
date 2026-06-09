"use client";

/**
 * MFA cliente API wrapper.
 *
 * 2026-06-09 · método por defecto = CÓDIGO AL EMAIL (sustituye TOTP "más rollo"):
 *   - emailStart()  → envía un código de 6 dígitos al email del cliente.
 *   - emailConfirm(code) → confirma el código y ACTIVA la verificación en 2 pasos.
 * En login, el código se envía automáticamente y el cliente lo teclea.
 *
 * (TOTP legacy `initiate`/`confirm` se conserva para method='totp'.)
 *
 * Endpoints under `/client-portal/settings/mfa/*` · clientApi wrapper canonical
 * (CSRF triple binding + cookie session).
 */
import { clientApi } from "@/lib/client-portal-api";

export interface MfaStatus {
  method: "email" | "totp";
  mfa_enabled: boolean;
  enrolled: boolean;
  verified: boolean;
  email: string | null;
  backup_codes_remaining: number;
  last_used_at: string | null;
}

export interface MfaInitiateResponse {
  secret: string;
  otpauth_uri: string;
}

export interface MfaConfirmResponse {
  backup_codes: string[];
}

export const clientMfaApi = {
  async status(): Promise<MfaStatus> {
    return clientApi<MfaStatus>("/client-portal/settings/mfa/status");
  },

  // ── Email code (default) ───────────────────────────────────────────
  async emailStart(): Promise<void> {
    await clientApi<void>("/client-portal/settings/mfa/email/start", {
      method: "POST",
    });
  },
  async emailConfirm(code: string): Promise<MfaStatus> {
    return clientApi<MfaStatus>("/client-portal/settings/mfa/email/confirm", {
      json: { code },
    });
  },

  // ── TOTP (legacy · method='totp') ──────────────────────────────────
  async initiate(): Promise<MfaInitiateResponse> {
    return clientApi<MfaInitiateResponse>(
      "/client-portal/settings/mfa/initiate",
      { method: "POST" },
    );
  },
  async confirm(code: string): Promise<MfaConfirmResponse> {
    return clientApi<MfaConfirmResponse>(
      "/client-portal/settings/mfa/confirm",
      { json: { code } },
    );
  },

  async disable(code?: string): Promise<void> {
    await clientApi<void>("/client-portal/settings/mfa/disable", {
      json: code ? { code } : {},
    });
  },
};
