/**
 * Admin Personalización API client · sub-atom 1.E.2.bis Phase D.
 *
 * Wraps admin_branding_api production endpoints (M21):
 *   GET    /api/v1/admin/clients/{client_id}/branding
 *   PATCH  /api/v1/admin/clients/{client_id}/branding
 *   DELETE /api/v1/admin/clients/{client_id}/branding/logo
 *
 * + logo upload via /api/v1/clients/{client_id}/logo (multipart core API).
 *
 * Cliente-level branding (per ADR-054 Phase 0 decision · piloto MEDIA
 * 1 cliente ≈ 1 proyecto típico · per-project capability Future demand-driven).
 */
import { api } from "@/lib/api";

export interface BrandingView {
  client_id: string;
  primary_color: string | null;
  secondary_color: string | null;
  footer_text: string | null;
  logo_path: string | null;
  logo_mime_type: string | null;
  has_logo: boolean;
}

export interface BrandingPatch {
  primary_color?: string | null;
  secondary_color?: string | null;
  footer_text?: string | null;
  unset_primary?: boolean;
  unset_secondary?: boolean;
  unset_footer?: boolean;
}

export async function getClientBranding(
  clientId: string,
): Promise<BrandingView> {
  return api<BrandingView>(`/api/v1/admin/clients/${clientId}/branding`);
}

export async function patchClientBranding(
  clientId: string,
  body: BrandingPatch,
): Promise<BrandingView> {
  return api<BrandingView>(`/api/v1/admin/clients/${clientId}/branding`, {
    method: "PATCH",
    json: body,
  });
}

export async function deleteClientLogo(
  clientId: string,
): Promise<BrandingView> {
  return api<BrandingView>(
    `/api/v1/admin/clients/${clientId}/branding/logo`,
    { method: "DELETE" },
  );
}
