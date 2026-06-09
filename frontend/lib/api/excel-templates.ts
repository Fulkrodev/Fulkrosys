/**
 * Motor 6 — Excel templates API client (SAN-C.MB-10.1).
 *
 * Endpoints expuestos (router M06 sin prefix interno · ver main.py):
 *  - GET  /api/v1/excel-templates → catálogo 16 plantillas
 *  - POST /api/v1/projects/{id}/excel-templates/{slug}/generate → XLSX blob
 *
 * NOTA SAN-C.MB-10.bis: corregido en path-fix · originalmente apuntaba
 * a ``/api/v1/document-factory/...`` que no existe (404 detectado en
 * smoke curl).
 */
import { api } from "@/lib/api";
import { CSRF_HEADER } from "@/lib/constants";
import { getCsrfToken } from "@/lib/csrf";

const BASE = "/api/v1";

export interface ExcelTemplateInfo {
  slug: string;
  code: string;
  title: string;
  description: string;
  ccn_stic: string | null;
}

/** GET catálogo canónico 16 plantillas Excel. */
export function listExcelTemplates(): Promise<ExcelTemplateInfo[]> {
  return api(`${BASE}/excel-templates`);
}

/** POST genera XLSX para template + descarga blob. */
export async function generateExcelTemplate(
  projectId: string,
  templateSlug: string,
): Promise<Blob> {
  const headers = new Headers();
  const csrf = getCsrfToken();
  if (csrf) headers.set(CSRF_HEADER, csrf);

  const response = await fetch(
    `${BASE}/projects/${projectId}/excel-templates/${templateSlug}/generate`,
    { method: "POST", headers, credentials: "include" },
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
