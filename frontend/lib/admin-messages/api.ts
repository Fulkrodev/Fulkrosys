/**
 * Admin Messages API client wrapper (sub-bloque 6.B.2 FASE 6).
 *
 * Reusa frontend/lib/api.ts (admin context — CSRF + cookies admin).
 *
 * Endpoints backend (api_admin.py registrados main.py):
 *   POST   /api/v1/admin/messages
 *   GET    /api/v1/admin/messages?client_id=&contact_id=&only_unread=
 *   GET    /api/v1/admin/messages/unread-count
 *   GET    /api/v1/admin/messages/search?q=
 *   GET    /api/v1/admin/messages/{thread_id}
 *   POST   /api/v1/admin/messages/{message_id}/mark-read
 *   DELETE /api/v1/admin/messages/{message_id}
 *   POST   /api/v1/admin/messages/{message_id}/attachments
 *   POST   /api/v1/admin/messages/{message_id}/attachments/{aid}/complete
 *   GET    /api/v1/admin/messages/{message_id}/attachments/{aid}/download
 */
"use client";

import { api } from "@/lib/api";
import type {
  AdminInboxFilters,
  AdminSendMessageBody,
  AttachmentOut,
  AttachmentUploadRequest,
  AttachmentUploadResponse,
  MarkReadResponse,
  MessageOut,
  ThreadSummary,
  UnreadCountResponse,
} from "./schemas";

const base = "/api/v1/admin/messages";

// ────────────────────────────────────────────────────────────────────
// SEND + LIST + DETAIL
// ────────────────────────────────────────────────────────────────────

export function sendAdminMessage(
  payload: AdminSendMessageBody,
): Promise<MessageOut> {
  return api<MessageOut>(base, { method: "POST", json: payload });
}

export function replyAsAdmin(
  threadId: string,
  bodyMarkdown: string,
  toContactId?: string | null,
): Promise<MessageOut> {
  return sendAdminMessage({
    body_markdown: bodyMarkdown,
    thread_id: threadId,
    to_contact_id: toContactId ?? null,
  });
}

export function listAdminThreads(
  filters: AdminInboxFilters = {},
  limit = 50,
): Promise<ThreadSummary[]> {
  const qs = new URLSearchParams();
  if (filters.client_id) qs.set("client_id", filters.client_id);
  if (filters.contact_id) qs.set("contact_id", filters.contact_id);
  if (filters.only_unread) qs.set("only_unread", "true");
  qs.set("limit", String(limit));
  return api<ThreadSummary[]>(`${base}?${qs.toString()}`);
}

export function getAdminUnreadCount(
  clientId?: string | null,
): Promise<UnreadCountResponse> {
  const qs = new URLSearchParams();
  if (clientId) qs.set("client_id", clientId);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return api<UnreadCountResponse>(`${base}/unread-count${suffix}`);
}

export function searchAdminMessages(
  query: string,
  clientId?: string | null,
  limit = 25,
): Promise<MessageOut[]> {
  const qs = new URLSearchParams({ q: query, limit: String(limit) });
  if (clientId) qs.set("client_id", clientId);
  return api<MessageOut[]>(`${base}/search?${qs.toString()}`);
}

export function getThreadAdmin(threadId: string): Promise<MessageOut[]> {
  return api<MessageOut[]>(`${base}/${threadId}`);
}

// ────────────────────────────────────────────────────────────────────
// MARK READ + DELETE
// ────────────────────────────────────────────────────────────────────

export function markAdminAsRead(
  messageId: string,
): Promise<MarkReadResponse> {
  return api<MarkReadResponse>(
    `${base}/${messageId}/mark-read`,
    { method: "POST", json: {} },
  );
}

export async function deleteAdminMessage(messageId: string): Promise<void> {
  await api(`${base}/${messageId}`, { method: "DELETE" });
}

// ────────────────────────────────────────────────────────────────────
// ATTACHMENTS — 3-step presigned PUT flow
// ────────────────────────────────────────────────────────────────────

export function requestAdminAttachmentUpload(
  messageId: string,
  request: AttachmentUploadRequest,
): Promise<AttachmentUploadResponse> {
  return api<AttachmentUploadResponse>(
    `${base}/${messageId}/attachments`,
    { method: "POST", json: request },
  );
}

export function completeAdminAttachmentUpload(
  messageId: string,
  attachmentId: string,
): Promise<AttachmentOut> {
  return api<AttachmentOut>(
    `${base}/${messageId}/attachments/${attachmentId}/complete`,
    { method: "POST", json: {} },
  );
}

export function getAdminAttachmentDownload(
  messageId: string,
  attachmentId: string,
): Promise<AttachmentOut> {
  return api<AttachmentOut>(
    `${base}/${messageId}/attachments/${attachmentId}/download`,
  );
}

/**
 * Upload directo a MinIO via presigned PUT URL — admin context.
 */
export async function putAdminToPresignedUrl(
  uploadUrl: string,
  file: File | Blob,
  headers: Record<string, string>,
): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: "PUT",
    headers,
    body: file,
  });
  if (!res.ok) {
    throw new Error(
      `Upload MinIO falló: HTTP ${res.status} ${res.statusText}`,
    );
  }
}
