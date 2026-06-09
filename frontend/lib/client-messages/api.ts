/**
 * Client Messages API client wrapper (sub-bloque 6.B.1 FASE 6).
 *
 * Reusa frontend/lib/client-portal-api.ts (clientApi + ClientApiError) —
 * heredamos cookies httpOnly + CSRF triple binding cliente.
 *
 * Endpoints backend (api_client.py registrados main.py):
 *   POST   /api/v1/client-portal/messages
 *   GET    /api/v1/client-portal/messages
 *   GET    /api/v1/client-portal/messages/unread-count
 *   GET    /api/v1/client-portal/messages/{thread_id}
 *   POST   /api/v1/client-portal/messages/{message_id}/mark-read
 *   POST   /api/v1/client-portal/messages/{message_id}/attachments
 *   POST   /api/v1/client-portal/messages/{message_id}/attachments/{aid}/complete
 *   GET    /api/v1/client-portal/messages/{message_id}/attachments/{aid}/download
 */
"use client";

import { clientApi } from "@/lib/client-portal-api";
import type {
  AttachmentOut,
  AttachmentUploadRequest,
  AttachmentUploadResponse,
  ClientSendMessageBody,
  MarkReadResponse,
  MessageOut,
  ThreadSummary,
  UnreadCountResponse,
} from "./schemas";

const base = "/client-portal/messages";

// ────────────────────────────────────────────────────────────────────
// SEND + LIST + DETAIL
// ────────────────────────────────────────────────────────────────────

export function sendMessage(payload: ClientSendMessageBody): Promise<MessageOut> {
  return clientApi<MessageOut>(base, { method: "POST", json: payload });
}

export function replyToThread(
  threadId: string,
  bodyMarkdown: string,
  projectId?: string | null,
): Promise<MessageOut> {
  return sendMessage({
    body_markdown: bodyMarkdown,
    thread_id: threadId,
    project_id: projectId ?? null,
  });
}

export function listInboxThreads(): Promise<ThreadSummary[]> {
  return clientApi<ThreadSummary[]>(base);
}

export function getUnreadCount(): Promise<UnreadCountResponse> {
  return clientApi<UnreadCountResponse>(`${base}/unread-count`);
}

export function getThread(threadId: string): Promise<MessageOut[]> {
  return clientApi<MessageOut[]>(`${base}/${threadId}`);
}

// ────────────────────────────────────────────────────────────────────
// MARK READ
// ────────────────────────────────────────────────────────────────────

export function markAsRead(messageId: string): Promise<MarkReadResponse> {
  return clientApi<MarkReadResponse>(
    `${base}/${messageId}/mark-read`,
    { method: "POST", json: {} },
  );
}

// ────────────────────────────────────────────────────────────────────
// ATTACHMENTS — 3-step presigned PUT flow
// ────────────────────────────────────────────────────────────────────

export function requestAttachmentUpload(
  messageId: string,
  request: AttachmentUploadRequest,
): Promise<AttachmentUploadResponse> {
  return clientApi<AttachmentUploadResponse>(
    `${base}/${messageId}/attachments`,
    { method: "POST", json: request },
  );
}

export function completeAttachmentUpload(
  messageId: string,
  attachmentId: string,
): Promise<AttachmentOut> {
  return clientApi<AttachmentOut>(
    `${base}/${messageId}/attachments/${attachmentId}/complete`,
    { method: "POST", json: {} },
  );
}

export function getAttachmentDownload(
  messageId: string,
  attachmentId: string,
): Promise<AttachmentOut> {
  return clientApi<AttachmentOut>(
    `${base}/${messageId}/attachments/${attachmentId}/download`,
  );
}

/**
 * Upload directo a MinIO via presigned PUT URL.
 *
 * NOTA: este fetch va a MinIO (no a /api/v1) — sin cookies, sin CSRF.
 * El presigned URL contiene la firma temporal y headers requeridos.
 */
export async function putToPresignedUrl(
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
