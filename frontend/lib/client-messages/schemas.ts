/**
 * Client Messages schemas TypeScript (sub-bloque 6.B.1 FASE 6).
 *
 * Espejo de backend/app/motors/m29_client_messaging/schemas.py.
 * Mantener sincronizado manualmente al cambiar contratos backend.
 *
 * Compartido entre context cliente (lib/client-messages) y admin
 * (lib/admin-messages — re-exporta tipos comunes desde aquí).
 */

export const FROM_ROLES = ["client", "admin"] as const;
export type FromRole = (typeof FROM_ROLES)[number];

export const EMAIL_FORWARD_STATUS_VALUES = [
  "pending",
  "sent",
  "failed",
  "skipped",
] as const;
export type EmailForwardStatus = (typeof EMAIL_FORWARD_STATUS_VALUES)[number];

/**
 * MIME whitelist espejo backend (10 tipos). Usar en validateAttachment
 * client-side ANTES de solicitar presigned PUT URL para feedback inmediato.
 */
export const ALLOWED_MIME_TYPES = [
  "image/png",
  "image/jpeg",
  "image/gif",
  "image/webp",
  "application/pdf",
  "text/plain",
  "text/csv",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/zip",
] as const;
export type AllowedMimeType = (typeof ALLOWED_MIME_TYPES)[number];

export const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024; // 10 MB

// ────────────────────────────────────────────────────────────────────
// Cliente — input bodies
// ────────────────────────────────────────────────────────────────────

export interface ClientSendMessageBody {
  body_markdown: string;
  thread_id?: string | null;
  project_id?: string | null;
}

// ────────────────────────────────────────────────────────────────────
// Attachment upload flow
// ────────────────────────────────────────────────────────────────────

export interface AttachmentUploadRequest {
  filename: string;
  mime_type: string;
  size_bytes: number;
}

export interface AttachmentUploadResponse {
  attachment_id: string;
  upload_url: string;
  upload_method: string; // "PUT"
  upload_headers: Record<string, string>;
}

export interface AttachmentOut {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  download_url?: string | null;
  uploaded_at?: string | null;
}

// ────────────────────────────────────────────────────────────────────
// Output — message + thread
// ────────────────────────────────────────────────────────────────────

export interface MessageOut {
  id: string;
  thread_id: string;
  client_id: string;
  project_id?: string | null;
  from_role: FromRole;
  from_user_id: string;
  to_contact_id?: string | null;
  body_markdown: string;
  body_html?: string | null;
  is_read_by_admin: boolean;
  is_read_by_client: boolean;
  forwarded_to_email?: string | null;
  forwarded_at?: string | null;
  email_forward_status?: EmailForwardStatus | null;
  created_at: string;
  attachments: AttachmentOut[];
}

export interface ThreadSummary {
  thread_id: string;
  client_id: string;
  last_message_id: string;
  last_message_excerpt: string;
  last_message_at: string;
  last_message_from_role: FromRole;
  total_messages: number;
  unread_for_admin: number;
  unread_for_client: number;
  has_attachments: boolean;
  last_to_contact_id?: string | null;
}

// ────────────────────────────────────────────────────────────────────
// Unread + mark-read
// ────────────────────────────────────────────────────────────────────

export interface UnreadCountResponse {
  unread_total: number;
  unread_threads: number;
}

export interface MarkReadResponse {
  message_id: string;
  is_read_by_admin: boolean;
  is_read_by_client: boolean;
}

// ────────────────────────────────────────────────────────────────────
// Filtros UI cliente
// ────────────────────────────────────────────────────────────────────

export type InboxFilter = "all" | "unread" | "with_attachments";
