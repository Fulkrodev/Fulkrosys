/**
 * Admin Meetings API client wrapper (sub-bloque 7.B.1 FASE 7).
 *
 * Reusa frontend/lib/api.ts (admin context — CSRF + cookies admin).
 *
 * Endpoints backend (m_meetings/api.py registrados main.py):
 *   POST   /api/v1/admin/meetings
 *   GET    /api/v1/admin/meetings (filters)
 *   GET    /api/v1/admin/meetings/search?q=
 *   GET    /api/v1/admin/meetings/by-client/{client_id}
 *   GET    /api/v1/admin/meetings/{meeting_id}
 *   PATCH  /api/v1/admin/meetings/{meeting_id}
 *   POST   /api/v1/admin/meetings/{meeting_id}/complete
 *   POST   /api/v1/admin/meetings/{meeting_id}/cancel
 *   POST   /api/v1/admin/meetings/{meeting_id}/sse-init
 *   POST   /api/v1/admin/meetings/{meeting_id}/post-action
 *   DELETE /api/v1/admin/meetings/{meeting_id}
 *
 * SSE A18 stream consumer ver hooks/useMeetingSSE.ts (sub-bloque 7.B.6).
 */
"use client";

import { api } from "@/lib/api";
import type {
  MeetingCancel,
  MeetingComplete,
  MeetingCreate,
  MeetingDetail,
  MeetingListItem,
  MeetingPostActionRequest,
  MeetingPostActionResponse,
  MeetingSearchResult,
  MeetingUpdate,
  MeetingsFilters,
  SSEStartResponse,
} from "./schemas";

const base = "/api/v1/admin/meetings";

// ────────────────────────────────────────────────────────────────────
// CRUD + workflow
// ────────────────────────────────────────────────────────────────────

export function createMeeting(payload: MeetingCreate): Promise<MeetingDetail> {
  return api<MeetingDetail>(base, { method: "POST", json: payload });
}

export function getMeeting(meetingId: string): Promise<MeetingDetail> {
  return api<MeetingDetail>(`${base}/${meetingId}`);
}

export function listMeetings(
  filters: MeetingsFilters = {},
): Promise<MeetingListItem[]> {
  const qs = new URLSearchParams();
  if (filters.client_id) qs.set("client_id", filters.client_id);
  if (filters.project_id) qs.set("project_id", filters.project_id);
  if (filters.status) qs.set("status", filters.status);
  if (filters.limit) qs.set("limit", String(filters.limit));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return api<MeetingListItem[]>(`${base}${suffix}`);
}

export function updateMeeting(
  meetingId: string,
  payload: MeetingUpdate,
): Promise<MeetingDetail> {
  return api<MeetingDetail>(`${base}/${meetingId}`, {
    method: "PATCH",
    json: payload,
  });
}

export function completeMeeting(
  meetingId: string,
  payload: MeetingComplete,
): Promise<MeetingDetail> {
  return api<MeetingDetail>(`${base}/${meetingId}/complete`, {
    method: "POST",
    json: payload,
  });
}

export function cancelMeeting(
  meetingId: string,
  payload: MeetingCancel = {},
): Promise<MeetingDetail> {
  return api<MeetingDetail>(`${base}/${meetingId}/cancel`, {
    method: "POST",
    json: payload,
  });
}

export async function deleteMeeting(meetingId: string): Promise<void> {
  await api(`${base}/${meetingId}`, { method: "DELETE" });
}

// ────────────────────────────────────────────────────────────────────
// Search + histórica
// ────────────────────────────────────────────────────────────────────

export function searchMeetings(
  query: string,
  clientId?: string | null,
  limit = 25,
): Promise<MeetingSearchResult[]> {
  const qs = new URLSearchParams({ q: query, limit: String(limit) });
  if (clientId) qs.set("client_id", clientId);
  return api<MeetingSearchResult[]>(`${base}/search?${qs.toString()}`);
}

export function getMeetingsByClient(
  clientId: string,
  limit = 50,
): Promise<MeetingListItem[]> {
  return api<MeetingListItem[]>(
    `${base}/by-client/${clientId}?limit=${limit}`,
  );
}

// ────────────────────────────────────────────────────────────────────
// SSE init + PostAction
// ────────────────────────────────────────────────────────────────────

export function initMeetingSSE(meetingId: string): Promise<SSEStartResponse> {
  return api<SSEStartResponse>(`${base}/${meetingId}/sse-init`, {
    method: "POST",
    json: {},
  });
}

export function postMeetingAction(
  meetingId: string,
  payload: MeetingPostActionRequest,
): Promise<MeetingPostActionResponse> {
  return api<MeetingPostActionResponse>(
    `${base}/${meetingId}/post-action`,
    { method: "POST", json: payload },
  );
}
