/**
 * Motor 14 — Legal templates DOCX API client (SAN-C.MB-10.2).
 *
 * Endpoints expuestos:
 *  - GET  /api/v1/contracts/legal-templates → catálogo 7 modelos
 *  - POST /api/v1/contracts/projects/{id}/legal-templates/{slug}/generate → DOCX blob
 */
import { api } from "@/lib/api";
import { CSRF_HEADER } from "@/lib/constants";
import { getCsrfToken } from "@/lib/csrf";

const BASE = "/api/v1/contracts";

export interface LegalTemplateInfo {
  code: string;
  slug: string;
  title: string;
  description: string;
  requires_provider: boolean;
  ccn_stic: string | null;
}

export interface GenerateLegalParams {
  provider_name?: string;
  provider_cif?: string;
  provider_role?: string;
}

export function listLegalTemplates(): Promise<LegalTemplateInfo[]> {
  return api(`${BASE}/legal-templates`);
}

export async function generateLegalTemplate(
  projectId: string,
  templateSlug: string,
  params: GenerateLegalParams = {},
): Promise<Blob> {
  const headers = new Headers();
  const csrf = getCsrfToken();
  if (csrf) headers.set(CSRF_HEADER, csrf);
  headers.set("Content-Type", "application/json");

  const response = await fetch(
    `${BASE}/projects/${projectId}/legal-templates/${templateSlug}/generate`,
    {
      method: "POST",
      headers,
      credentials: "include",
      body: JSON.stringify(params),
    },
  );

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      if (payload && typeof payload === "object" && "detail" in payload) {
        detail = String((payload as { detail: unknown }).detail);
      }
    } catch {
      // not JSON
    }
    throw new Error(detail);
  }
  return response.blob();
}
