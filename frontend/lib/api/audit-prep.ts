/**
 * API client · Motor 09 Audit Preparation.
 *
 * Endpoints servidos desde m09 con prefix `/api/v1/audit-prep`.
 *   POST /projects/{id}/runs                       crea run de preparación
 *   GET /projects/{id}/runs                        list de runs
 *   GET /projects/{id}/runs/{run_id}               run detail
 *   GET /projects/{id}/runs/{run_id}/dossier       download ZIP
 *   GET /projects/{id}/runs/{run_id}/dossier/index JSON index sections
 *   GET /projects/{id}/summary                     summary
 *   GET /projects/{id}/readiness                   readiness assessment
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/audit-prep";

export interface AuditPrepRun {
  id: string;
  project_id?: string;
  categoria?: string;
  status?: string;
  estado?: string;
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
}

export interface DossierIndex {
  documents?: Array<Record<string, unknown>>;
  evidence?: Array<Record<string, unknown>>;
  records?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

export const auditPrepApi = {
  listRuns: (projectId: string) =>
    api<AuditPrepRun[]>(`${BASE}/projects/${projectId}/runs`),

  /**
   * Crea el run de preparación que la pantalla `/dossier` necesita para
   * enseñar algo. La categoría NO se manda: la pone el backend desde el
   * proyecto, que es quien la sabe (y si no la tiene, responde 422 diciéndolo
   * en vez de suponer la más baja).
   */
  createRun: (projectId: string) =>
    api<AuditPrepRun>(`${BASE}/projects/${projectId}/runs`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  dossierIndex: (projectId: string, runId: string) =>
    api<DossierIndex>(`${BASE}/projects/${projectId}/runs/${runId}/dossier/index`),

  dossierDownloadUrl: (projectId: string, runId: string) =>
    `${BASE}/projects/${projectId}/runs/${runId}/dossier`,

  /**
   * URL for signed-manifest dossier download · Sesión 3B-2B.6 Cluster 1 Phase 1.
   * MANIFEST.json includes `_signature` block Ed25519 (M05 keypair) ·
   * auditor ENAC verifica integridad + autoría independientemente.
   */
  dossierSignedDownloadUrl: (projectId: string, runId: string) =>
    `${BASE}/projects/${projectId}/runs/${runId}/dossier?sign_manifest=true`,

  /**
   * POST convenience · find latest run + generate signed ZIP en single call.
   * Backend stream attachment directly (no JSON wrapper). Use via window.location
   * o fetch+blob para download. Returns 404 si no hay runs (instructions to create).
   */
  generateSignedZipUrl: (projectId: string) =>
    `${BASE}/projects/${projectId}/dossier/generate-signed-zip`,

  summary: (projectId: string) =>
    api<Record<string, unknown>>(`${BASE}/projects/${projectId}/summary`),
};
