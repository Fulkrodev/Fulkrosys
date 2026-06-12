/**
 * Retainer check-in · ADMIN curación API client (feat/fulkro-100 · Ola 3).
 *
 * Marcos lista / genera / cura / ENVÍA los check-ins trimestrales del retainer.
 * Backend: backend/app/motors/m23_retainer/retainer_checkin_admin_api.py
 * (require_owner · ADR-013). Workflow: draft → curated_by_admin → sent_to_client.
 */
import { api } from "@/lib/api";

export type AdminCurationStatus =
  | "draft"
  | "curated_by_admin"
  | "sent_to_client";

export interface AdminCheckinReport {
  id: string;
  project_id: string;
  period_quarter: string;
  admin_curation_status: AdminCurationStatus | string;
  summary_jsonb: Record<string, unknown>;
  admin_curated_at?: string | null;
  sent_at?: string | null;
  client_review_status?: string | null;
  created_at?: string | null;
}

const BASE = "/api/v1/admin/retainer-checkin";

export const retainerCheckinAdminApi = {
  list: (projectId: string) =>
    api<AdminCheckinReport[]>(`${BASE}/projects/${projectId}/reports`),

  generate: (projectId: string, periodQuarter?: string | null) =>
    api<AdminCheckinReport>(
      `${BASE}/projects/${projectId}/reports/generate`,
      { json: { period_quarter: periodQuarter ?? null } },
    ),

  curate: (
    reportId: string,
    summaryEdits?: Record<string, unknown> | null,
  ) =>
    api<AdminCheckinReport>(
      `${BASE}/reports/${reportId}/curate`,
      { json: { summary_edits: summaryEdits ?? null } },
    ),

  send: (reportId: string) =>
    api<AdminCheckinReport>(`${BASE}/reports/${reportId}/send`, {
      method: "POST",
    }),
};
