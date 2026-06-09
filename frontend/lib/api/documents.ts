/**
 * Motor 6 — Document Factory API client (subset rectores · MB-9.bis.3).
 *
 * Endpoints expuestos:
 *  - POST /api/v1/projects/{id}/manual-sgsi/generate (DOCX blob)
 *  - POST /api/v1/projects/{id}/plan-director/generate (DOCX blob)
 *
 * Usa fetch directo (api() wrapper solo JSON). Para artefactos
 * documentales completos del Motor 6 (templates · render · catalog),
 * consultar otros módulos en `/api/v1/document-factory`.
 */
import { CSRF_HEADER } from "@/lib/constants";
import { getCsrfToken } from "@/lib/csrf";

const BASE = "/api/v1";

async function _downloadDocxPost(path: string): Promise<Blob> {
  const headers = new Headers();
  const csrf = getCsrfToken();
  if (csrf) headers.set(CSRF_HEADER, csrf);

  const response = await fetch(path, {
    method: "POST",
    headers,
    credentials: "include",
  });

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

/** POST /api/v1/projects/{id}/manual-sgsi/generate · DOCX E-160. */
export function generateManualSgsiDocx(projectId: string): Promise<Blob> {
  return _downloadDocxPost(`${BASE}/projects/${projectId}/manual-sgsi/generate`);
}

/** POST /api/v1/projects/{id}/plan-director/generate · DOCX E-170. */
export function generatePlanDirectorDocx(projectId: string): Promise<Blob> {
  return _downloadDocxPost(
    `${BASE}/projects/${projectId}/plan-director/generate`,
  );
}
