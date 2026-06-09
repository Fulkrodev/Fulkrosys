/**
 * Notifications DLQ admin API client · Sesión 3B-2B.11 Phase 11.3 (2026-05-27).
 *
 * 4 endpoints backend (DLQ derived desde notification_events failed retry_count >= 3):
 *   GET  /api/v1/admin/notifications/dlq                       list paginated
 *   GET  /api/v1/admin/notifications/dlq/summary               count widget
 *   POST /api/v1/admin/notifications/dlq/{event_id}/reprocess  re-queue
 *   POST /api/v1/admin/notifications/dlq/{event_id}/resolve    soft-delete
 */
import { api } from "@/lib/api";

export interface DlqEntry {
  event_id: string;
  event_type: string;
  recipient_email: string;
  project_id: string | null;
  status: string;
  retry_count: number;
  error: string | null;
  channels_attempted: string[];
  channels_failed: string[];
  template_used: string | null;
  created_at: string;
  updated_at: string;
}

export interface DlqListResponse {
  items: DlqEntry[];
  count: number;
}

export interface DlqSummary {
  total_count: number;
  last_24h_count: number;
  by_event_type: Record<string, number>;
}

export interface DlqActionResponse {
  success: boolean;
  rows_affected: number;
  reason: string | null;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) sp.set(k, String(v));
  }
  const q = sp.toString();
  return q ? `?${q}` : "";
}

export const notificationsDlqApi = {
  list: (
    params: { project_id?: string; limit?: number; offset?: number } = {},
  ): Promise<DlqListResponse> =>
    api<DlqListResponse>(`/api/v1/admin/notifications/dlq${buildQuery(params)}`),
  summary: (project_id?: string): Promise<DlqSummary> =>
    api<DlqSummary>(
      `/api/v1/admin/notifications/dlq/summary${buildQuery({ project_id })}`,
    ),
  reprocess: (event_id: string): Promise<DlqActionResponse> =>
    api<DlqActionResponse>(
      `/api/v1/admin/notifications/dlq/${event_id}/reprocess`,
      { method: "POST" },
    ),
  resolve: (
    event_id: string,
    resolution_note: string,
  ): Promise<DlqActionResponse> =>
    api<DlqActionResponse>(
      `/api/v1/admin/notifications/dlq/${event_id}/resolve`,
      { json: { resolution_note } },
    ),
};
