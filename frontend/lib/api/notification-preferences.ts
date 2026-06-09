/**
 * Notification Preferences API · CLUSTER 5 Phase 5E delta.
 *
 * GET /portal/notifications/preferences · PUT /portal/notifications/preferences
 * (require_client_user). Schema includes whatsapp_enabled +
 * event_opt_outs granular per-event toggles.
 */
import { clientApi } from "@/lib/client-portal-api";

export interface NotificationPreferences {
  id: string;
  client_user_id: string;
  email_enabled: boolean;
  portal_sse_enabled: boolean;
  whatsapp_enabled: boolean;
  event_opt_outs: Record<string, boolean>;
  dnd_start_local: string | null;
  dnd_end_local: string | null;
  timezone: string;
  digest_mode: string;
  created_at: string;
  updated_at: string | null;
}

export interface NotificationPreferencesUpdate {
  email_enabled?: boolean;
  portal_sse_enabled?: boolean;
  whatsapp_enabled?: boolean;
  event_opt_outs?: Record<string, boolean>;
  dnd_start_local?: string | null;
  dnd_end_local?: string | null;
  timezone?: string;
  digest_mode?: string;
}

export const notificationPreferencesApi = {
  get: (): Promise<NotificationPreferences> =>
    clientApi<NotificationPreferences>(
      "/portal/notifications/preferences",
    ),

  update: (
    body: NotificationPreferencesUpdate,
  ): Promise<NotificationPreferences> =>
    clientApi<NotificationPreferences>(
      "/portal/notifications/preferences",
      { method: "PUT", json: body },
    ),
};
