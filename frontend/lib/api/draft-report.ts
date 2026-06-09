/**
 * Draft audit report API client · CLUSTER 3 Phase C4.3.
 *
 * Wraps backend draft_report_api endpoints (auditor + admin).
 * Preview returns HTML string · POST returns PDF Blob.
 */
const PUBLIC_BASE = "/api/v1/public/auditor-portal";
const ADMIN_BASE = "/api/v1/admin/projects";

export type Recommendation =
  | "APROBAR"
  | "APROBAR_CON_CONDICIONES"
  | "NO_APROBAR";

export interface GenerateReportBody {
  auditor_opinion_text?: string;
  recommendation?: Recommendation;
  auditor_name?: string;
  audit_period_start?: string;
  audit_period_end?: string;
}

export interface GeneratedReportMeta {
  pdf_sha256: string;
  signature_algorithm: string;
  recommendation: Recommendation;
  size_bytes: number;
}

async function _fetchPdf(
  url: string,
  body?: GenerateReportBody,
): Promise<{ blob: Blob; meta: GeneratedReportMeta }> {
  const response = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body ?? {}),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }
  const blob = await response.blob();
  const meta: GeneratedReportMeta = {
    pdf_sha256: response.headers.get("x-pdf-sha256") ?? "",
    signature_algorithm:
      response.headers.get("x-signature-algorithm") ?? "Ed25519",
    recommendation:
      (response.headers.get("x-recommendation") as Recommendation) ??
      "APROBAR_CON_CONDICIONES",
    size_bytes: blob.size,
  };
  return { blob, meta };
}

async function _fetchHtml(url: string): Promise<string> {
  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.text();
}

// ══════════════════════════════════════════════════════════════════════
// Auditor portal API
// ══════════════════════════════════════════════════════════════════════

export async function generateDraftReportAuditor(
  token: string,
  body?: GenerateReportBody,
): Promise<{ blob: Blob; meta: GeneratedReportMeta }> {
  return _fetchPdf(
    `${PUBLIC_BASE}/${token}/audit/draft-report`,
    body,
  );
}

export async function getDraftReportPreviewAuditor(
  token: string,
): Promise<string> {
  return _fetchHtml(`${PUBLIC_BASE}/${token}/audit/draft-report/preview`);
}

// ══════════════════════════════════════════════════════════════════════
// Admin API
// ══════════════════════════════════════════════════════════════════════

export async function generateDraftReportAdmin(
  projectId: string,
  body?: GenerateReportBody,
): Promise<{ blob: Blob; meta: GeneratedReportMeta }> {
  return _fetchPdf(
    `${ADMIN_BASE}/${projectId}/audit/draft-report`,
    body,
  );
}

export async function getDraftReportPreviewAdmin(
  projectId: string,
): Promise<string> {
  return _fetchHtml(
    `${ADMIN_BASE}/${projectId}/audit/draft-report/preview`,
  );
}

// ══════════════════════════════════════════════════════════════════════
// UI helpers
// ══════════════════════════════════════════════════════════════════════

export const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  APROBAR: "Aprobar",
  APROBAR_CON_CONDICIONES: "Aprobar con condiciones",
  NO_APROBAR: "No aprobar",
};

export const RECOMMENDATION_VARIANT: Record<
  Recommendation,
  "success" | "warning" | "danger"
> = {
  APROBAR: "success",
  APROBAR_CON_CONDICIONES: "warning",
  NO_APROBAR: "danger",
};

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 100);
}
