"use client";

/**
 * Client Notifications API client (SAN-E v3.MB-4.bis3 · ADR-020 IMPLEMENTED FULLY).
 *
 * Wraps endpoints /api/v1/portal/inbox/* (M21 notifications_inbox_api).
 * Auth: ClientUser session via clientApi helper (cookie + CSRF).
 */

import { clientApi } from "@/lib/client-portal-api";

// =====================================================================
// Types
// =====================================================================

export type NotificationPriority = "low" | "normal" | "high" | "urgent";

export type NotificationType =
  | "evidence_request"
  | "acta_review"
  | "retainer_offer"
  | "retainer_reconsideration"
  | "onboarding_ready"
  | "generic_alert"
  | "invoice_review"
  | "risk_validation"
  | "compliance_confirmation"
  | "meeting_invite"
  | "scope_change_validation"
  | "incident_report"
  | "nps_survey"
  | "vote_request"
  | "report_available"
  | "renewal_campaign"
  | "info_request";

export interface ClientNotification {
  id: string;
  type: NotificationType | string;
  title: string;
  body: string | null;
  target_url: string;
  priority: NotificationPriority | string;
  payload: Record<string, unknown> | null;
  emitted_by_motor: string;
  read_at: string | null;
  dismissed_at: string | null;
  actioned_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface InboxResponse {
  notifications: ClientNotification[];
  total: number;
  has_more: boolean;
}

export interface CountUnreadResponse {
  count: number;
}

// =====================================================================
// API functions
// =====================================================================

const BASE = "/portal/inbox";

export async function listInbox(opts?: {
  include_read?: boolean;
  include_dismissed?: boolean;
  limit?: number;
  offset?: number;
}): Promise<InboxResponse> {
  const qs = new URLSearchParams();
  if (opts?.include_read) qs.set("include_read", "true");
  if (opts?.include_dismissed) qs.set("include_dismissed", "true");
  if (opts?.limit !== undefined) qs.set("limit", String(opts.limit));
  if (opts?.offset !== undefined) qs.set("offset", String(opts.offset));
  const suffix = qs.toString() ? `?${qs}` : "";
  return clientApi<InboxResponse>(`${BASE}${suffix}`);
}

export async function countUnread(): Promise<number> {
  const res = await clientApi<CountUnreadResponse>(`${BASE}/count-unread`);
  return res.count;
}

export async function markRead(notificationId: string): Promise<void> {
  await clientApi(`${BASE}/${notificationId}/mark-read`, { method: "POST" });
}

export async function dismiss(notificationId: string): Promise<void> {
  await clientApi(`${BASE}/${notificationId}/dismiss`, { method: "POST" });
}

export async function markActioned(notificationId: string): Promise<void> {
  await clientApi(`${BASE}/${notificationId}/mark-actioned`, { method: "POST" });
}
