/**
 * Branding API client · MB-9 atom 9.2.
 */
import { api } from "@/lib/api";
import { clientApi } from "@/lib/client-portal-api";


export interface BrandingView {
  client_id: string;
  primary_color: string | null;
  secondary_color: string | null;
  footer_text: string | null;
  logo_path: string | null;
  logo_mime_type?: string | null;
  has_logo: boolean;
}


export interface BrandingPatchBody {
  primary_color?: string | null;
  secondary_color?: string | null;
  footer_text?: string | null;
  unset_primary?: boolean;
  unset_secondary?: boolean;
  unset_footer?: boolean;
}


// Admin (Marcos)
export async function adminGetBranding(clientId: string): Promise<BrandingView> {
  return api<BrandingView>(`/api/v1/admin/clients/${clientId}/branding`);
}


export async function adminPatchBranding(
  clientId: string, body: BrandingPatchBody,
): Promise<BrandingView> {
  return api<BrandingView>(
    `/api/v1/admin/clients/${clientId}/branding`,
    { method: "PATCH", json: body },
  );
}


export async function adminDeleteLogo(clientId: string): Promise<BrandingView> {
  return api<BrandingView>(
    `/api/v1/admin/clients/${clientId}/branding/logo`,
    { method: "DELETE" },
  );
}


// Cliente (portal)
export async function portalGetBranding(): Promise<BrandingView> {
  return clientApi<BrandingView>("/client-portal/branding");
}
