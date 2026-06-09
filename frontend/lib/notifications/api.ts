/**
 * API client NotificationOrchestrator MB-16.5 (ADR-039).
 *
 * Endpoints cliente (cookies + CSRF triple binding):
 *   GET /api/v1/portal/notifications/preferences
 *   PUT /api/v1/portal/notifications/preferences
 *
 * Endpoints admin Marcos (cookies + CSRF triple binding):
 *   GET  /api/v1/admin/notifications/events?status=...&event_type=...
 *   POST /api/v1/admin/notifications/events/{id}/redispatch
 */
import { api } from "@/lib/api";
import { clientApi } from "@/lib/client-portal-api";

import type {
  NotificationEventsListResponse,
  NotificationPreference,
  NotificationPreferenceUpdate,
  NotificationStatus,
  RedispatchResponse,
} from "./schemas";

export async function getMyNotificationPreferences(): Promise<NotificationPreference> {
  return clientApi<NotificationPreference>(
    "/portal/notifications/preferences",
  );
}

export async function updateMyNotificationPreferences(
  payload: NotificationPreferenceUpdate,
): Promise<NotificationPreference> {
  return clientApi<NotificationPreference>(
    "/portal/notifications/preferences",
    {
      method: "PUT",
      json: payload,
    },
  );
}

export interface ListNotificationEventsParams {
  status?: NotificationStatus;
  event_type?: string;
  limit?: number;
  offset?: number;
}

export async function listNotificationEventsAdmin(
  params: ListNotificationEventsParams = {},
): Promise<NotificationEventsListResponse> {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.event_type) search.set("event_type", params.event_type);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  const query = search.toString();
  const path = `/api/v1/admin/notifications/events${query ? `?${query}` : ""}`;
  return api<NotificationEventsListResponse>(path);
}

export async function redispatchNotificationEventAdmin(
  eventId: string,
): Promise<RedispatchResponse> {
  return api<RedispatchResponse>(
    `/api/v1/admin/notifications/events/${eventId}/redispatch`,
    { method: "POST" },
  );
}
