/**
 * Workflow Deliverables API · sub-atom 1.C.D.D.2 v3.8.
 *
 * Consume 3 endpoints reader (admin + cliente · backend 1.C.D.D.1):
 *   GET /api/v1/projects/{id}/workflow-engine/steps/{template_id}/deliverables
 *   GET /api/v1/projects/{id}/workflow-engine/deliverables/{evidence_id}/download
 *   GET /api/v1/projects/{id}/workflow-engine/steps/{template_id}/deliverables/bulk-zip
 *
 * Auth dual: pasa `mode: "admin" | "client"` para seleccionar wrapper.
 * - admin → api() (header CSRF · same-origin)
 * - client → clientApi() (cookie + CSRF · /api/v1 auto-prefix)
 *
 * OPS-044 sostenido · NO double prefix.
 */
import { api } from "@/lib/api";
import { clientApi } from "@/lib/client-portal-api";

export type DeliverableStatus = "available" | "needs_regen" | "missing";

export interface DeliverableState {
  code: string;
  status: DeliverableStatus;
  evidence_id: string | null;
  fichero_nombre_original: string | null;
  fichero_mime_type: string | null;
  fichero_tamano_bytes: number | null;
  hash_sha256: string | null;
  fecha_evidencia: string | null;
  fecha_caducidad: string | null;
  vigente: boolean | null;
}

export interface StepDeliverablesResponse {
  project_id: string;
  template_id: string;
  template_title: string;
  deliverable_codes: string[];
  deliverables: DeliverableState[];
  counts: {
    available: number;
    needs_regen: number;
    missing: number;
  };
}

export type ApiMode = "admin" | "client";

export async function listStepDeliverables(
  projectId: string,
  templateId: string,
  mode: ApiMode = "admin",
): Promise<StepDeliverablesResponse> {
  if (mode === "client") {
    return clientApi<StepDeliverablesResponse>(
      `/projects/${projectId}/workflow-engine/steps/${templateId}/deliverables`,
    );
  }
  return api<StepDeliverablesResponse>(
    `/api/v1/projects/${projectId}/workflow-engine/steps/${templateId}/deliverables`,
  );
}

/**
 * Trigger browser download del deliverable individual.
 * Backend retorna FileResponse · browser handles download via window.location.
 */
export function downloadDeliverableUrl(
  projectId: string,
  evidenceId: string,
): string {
  // Same URL admin+client · same-origin cookies forman auth
  return `/api/v1/projects/${projectId}/workflow-engine/deliverables/${evidenceId}/download`;
}

/**
 * Trigger browser download bulk ZIP per step.
 * Backend retorna StreamingResponse · navega URL para download attachment.
 */
export function downloadBulkZipUrl(
  projectId: string,
  templateId: string,
): string {
  return `/api/v1/projects/${projectId}/workflow-engine/steps/${templateId}/deliverables/bulk-zip`;
}
