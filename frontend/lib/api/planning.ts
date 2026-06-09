/**
 * Motor 17 — Planning API client.
 *
 * Endpoints exposed (subset · expand as needed):
 *  - POST /api/v1/planning/projects/{id}/pda/generate (DOCX blob)
 *
 * Usa fetch directo para descargas blob (api() wrapper solo JSON).
 */
import { CSRF_HEADER } from "@/lib/constants";
import { getCsrfToken } from "@/lib/csrf";

const BASE_PLANNING = "/api/v1/planning";

/**
 * POST /api/v1/planning/projects/{id}/pda/generate
 *
 * Descarga DOCX Plan de Adecuación (E-150 CCN-STIC 806). Aglutina datos
 * cross-motor M01+M02+M03+M04+M17 deterministicamente.
 *
 * Refs: SAN-C.MB-9.bis.2 · cierra fantasma frontend MB-9.3.
 */
export async function generatePdaDocx(projectId: string): Promise<Blob> {
  const headers = new Headers();
  const csrf = getCsrfToken();
  if (csrf) headers.set(CSRF_HEADER, csrf);

  const response = await fetch(
    `${BASE_PLANNING}/projects/${projectId}/pda/generate`,
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
      // not JSON · use statusText
    }
    throw new Error(detail);
  }

  return response.blob();
}
