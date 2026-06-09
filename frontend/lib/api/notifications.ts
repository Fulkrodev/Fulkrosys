/**
 * Notifications API client · MB-7 atom 7.4 plan v6.
 *
 * Hits existing /portal/inbox/* endpoints (ADR-020).
 */
import { clientApi } from "@/lib/client-portal-api";

export interface PortalNotification {
  id: string;
  type: string;
  title: string;
  body: string | null;
  target_url: string;
  priority: "low" | "normal" | "high" | "urgent";
  payload: Record<string, unknown> | null;
  emitted_by_motor: string;
  read_at: string | null;
  dismissed_at: string | null;
  actioned_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface InboxResponse {
  notifications: PortalNotification[];
  total: number;
  has_more: boolean;
}

export async function fetchUnreadCount(): Promise<number> {
  const resp = await clientApi<{ count: number }>(
    "/portal/inbox/count-unread",
  );
  return resp.count;
}

export async function fetchInbox(
  limit = 10,
): Promise<PortalNotification[]> {
  const qs = new URLSearchParams({
    include_read: "true",
    include_dismissed: "false",
    limit: String(limit),
    offset: "0",
  });
  const resp = await clientApi<InboxResponse>(
    `/portal/inbox?${qs.toString()}`,
  );
  return resp.notifications;
}

export async function markRead(notificationId: string): Promise<void> {
  await clientApi(`/portal/inbox/${notificationId}/mark-read`, {
    method: "POST",
  });
}

export async function markAllRead(): Promise<number> {
  const resp = await clientApi<{ ok: boolean; marked_count: number }>(
    "/portal/inbox/mark-all-read",
    { method: "POST" },
  );
  return resp.marked_count;
}

export async function dismissNotification(
  notificationId: string,
): Promise<void> {
  await clientApi(`/portal/inbox/${notificationId}/dismiss`, {
    method: "POST",
  });
}
