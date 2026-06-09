/**
 * Admin Settings API client wrapper.
 *
 * Reusa frontend/lib/api.ts (CSRF + cookies + ApiError) — heredamos
 * el manejo común y solo añadimos typing por endpoint.
 *
 * Endpoints backend (commit 0e546bc + fb68d16):
 *   GET    /api/v1/admin/settings
 *   PATCH  /api/v1/admin/settings/{section}
 *   POST   /api/v1/admin/settings/branding/logo (multipart)
 *   GET    /api/v1/admin/settings/about
 *   POST   /api/v1/admin/settings/smtp/test
 */
import { api } from "@/lib/api";
import type {
  AdminSettingsAbout,
  AdminSettingsResponse,
  AnalyticsPrefs,
  BrandingSettings,
  FiscalSettings,
  GeneralSettings,
  NotificationsSettings,
  SmtpSettings,
  SmtpTestRequest,
  SmtpTestResponse,
} from "./schemas";

type SectionName =
  | "branding"
  | "notifications"
  | "smtp"
  | "general"
  | "analytics_prefs"
  | "fiscal";

type SectionPayload = {
  branding: BrandingSettings;
  notifications: NotificationsSettings;
  smtp: SmtpSettings;
  general: GeneralSettings;
  analytics_prefs: AnalyticsPrefs;
  fiscal: FiscalSettings;
};

export async function getAdminSettings(): Promise<AdminSettingsResponse> {
  return api<AdminSettingsResponse>("/api/v1/admin/settings");
}

export async function getAdminSettingsAbout(): Promise<AdminSettingsAbout> {
  return api<AdminSettingsAbout>("/api/v1/admin/settings/about");
}

export async function patchAdminSettingsSection<S extends SectionName>(
  section: S,
  payload: SectionPayload[S],
): Promise<AdminSettingsResponse> {
  return api<AdminSettingsResponse>(`/api/v1/admin/settings/${section}`, {
    method: "PATCH",
    json: payload,
  });
}

export async function uploadBrandingLogo(
  file: File,
): Promise<AdminSettingsResponse> {
  const formData = new FormData();
  formData.append("file", file);

  // api() detecta ausencia de `json` y NO setea Content-Type
  // → browser pone multipart/form-data; boundary=... automáticamente.
  return api<AdminSettingsResponse>("/api/v1/admin/settings/branding/logo", {
    method: "POST",
    body: formData,
  });
}

export async function testSmtpConfig(
  payload: SmtpTestRequest,
): Promise<SmtpTestResponse> {
  return api<SmtpTestResponse>("/api/v1/admin/settings/smtp/test", {
    method: "POST",
    json: payload,
  });
}

// FIX P4-1 · pricing editable (fuente única) ─────────────────────────────────
export interface PricingConfigItem {
  categoria: string;
  precio_proyecto: number;
  updated_at: string | null;
  updated_by: string | null;
}

export async function getPricing(): Promise<PricingConfigItem[]> {
  return api<PricingConfigItem[]>("/api/v1/admin/settings/pricing");
}

export async function updatePricing(payload: {
  BASICA?: number;
  MEDIA?: number;
  ALTA?: number;
}): Promise<PricingConfigItem[]> {
  return api<PricingConfigItem[]>("/api/v1/admin/settings/pricing", {
    method: "PUT",
    json: payload,
  });
}
