/**
 * API client · Agent 21 Detector Discrepancias.
 *
 * Endpoints prefix `/api/v1` project-scoped:
 *   POST   /projects/{id}/a21/scan
 *   GET    /projects/{id}/a21/scans?limit=N
 *   GET    /projects/{id}/a21/discrepancies?resolution_status&severity&scan_run_id
 *   PATCH  /projects/{id}/a21/discrepancies/{did}/resolve
 */
import { api } from "@/lib/api";

const BASE = "/api/v1";

export type DiscrepancySeverity = "critical" | "high" | "medium" | "low";
export type ResolutionStatus =
  | "open"
  | "acknowledged"
  | "resolved"
  | "dismissed";
export type RunStatus = "pending" | "running" | "completed" | "failed";

export interface ScanRunOut {
  id: string;
  project_id: string;
  run_status: RunStatus;
  motors_scanned: string[];
  discrepancies_found: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface DiscrepancyOut {
  id: string;
  scan_run_id: string;
  project_id: string;
  discrepancy_type: string;
  severity: DiscrepancySeverity;
  motor_a: string;
  motor_b: string;
  description: string;
  evidence_a: Record<string, unknown>;
  evidence_b: Record<string, unknown>;
  resolution_status: ResolutionStatus;
  resolution_notes: string | null;
  resolved_at: string | null;
  created_at: string | null;
}

export interface ResolveDiscrepancyBody {
  new_status: ResolutionStatus;
  notes?: string | null;
}

export const agent21Api = {
  triggerScan: (projectId: string) =>
    api<ScanRunOut>(`${BASE}/projects/${projectId}/a21/scan`, {
      method: "POST",
    }),

  listScans: (projectId: string, limit = 10) =>
    api<ScanRunOut[]>(
      `${BASE}/projects/${projectId}/a21/scans?limit=${limit}`,
    ),

  listDiscrepancies: (
    projectId: string,
    opts: {
      resolutionStatus?: ResolutionStatus;
      severity?: DiscrepancySeverity;
      scanRunId?: string;
    } = {},
  ) => {
    const sp = new URLSearchParams();
    if (opts.resolutionStatus) sp.set("resolution_status", opts.resolutionStatus);
    if (opts.severity) sp.set("severity", opts.severity);
    if (opts.scanRunId) sp.set("scan_run_id", opts.scanRunId);
    const qs = sp.toString();
    return api<DiscrepancyOut[]>(
      `${BASE}/projects/${projectId}/a21/discrepancies${qs ? `?${qs}` : ""}`,
    );
  },

  resolve: (
    projectId: string,
    discrepancyId: string,
    body: ResolveDiscrepancyBody,
  ) =>
    api<DiscrepancyOut>(
      `${BASE}/projects/${projectId}/a21/discrepancies/${discrepancyId}/resolve`,
      { method: "PATCH", json: body },
    ),
};
