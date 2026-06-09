/**
 * Schemas TypeScript NotificationOrchestrator MB-16.5 (ADR-039).
 *
 * Mirror exacto de los modelos Pydantic del backend
 * (backend/app/notifications/api.py). Sincronizar manualmente si
 * el backend evoluciona.
 */

export type NotificationStatus =
  | "queued"
  | "dispatching"
  | "delivered"
  | "failed"
  | "suppressed_dnd";

export type DigestMode = "immediate" | "hourly" | "daily";

export interface NotificationPreference {
  id: string;
  client_user_id: string;
  email_enabled: boolean;
  portal_sse_enabled: boolean;
  dnd_start_local: string | null;
  dnd_end_local: string | null;
  timezone: string;
  digest_mode: DigestMode;
  created_at: string;
  updated_at: string | null;
}

export interface NotificationPreferenceUpdate {
  email_enabled?: boolean;
  portal_sse_enabled?: boolean;
  dnd_start_local?: string | null;
  dnd_end_local?: string | null;
  timezone?: string;
  digest_mode?: DigestMode;
}

export interface NotificationEvent {
  id: string;
  event_type: string;
  recipient_user_id: string | null;
  recipient_email: string;
  project_id: string | null;
  channels_attempted: string[];
  channels_succeeded: string[];
  channels_failed: string[];
  status: NotificationStatus;
  error: string | null;
  template_used: string | null;
  retry_count: number;
  payload_jsonb: Record<string, unknown>;
  created_at: string;
  dispatched_at: string | null;
  delivered_at: string | null;
}

export interface NotificationEventsListResponse {
  items: NotificationEvent[];
  total: number;
  limit: number;
  offset: number;
}

export interface RedispatchResponse {
  status: string;
  event_id: string | null;
  channels_succeeded: string[] | null;
  channels_failed: string[] | null;
}

export const NOTIFICATION_STATUSES: NotificationStatus[] = [
  "queued",
  "dispatching",
  "delivered",
  "failed",
  "suppressed_dnd",
];

export const DIGEST_MODES: DigestMode[] = ["immediate", "hourly", "daily"];
