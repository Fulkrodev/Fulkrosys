/**
 * Admin Messages schemas TypeScript (sub-bloque 6.B.2 FASE 6).
 *
 * Re-exporta tipos compartidos desde lib/client-messages/schemas
 * (single source of truth) + añade tipos específicos admin
 * (AdminSendMessageBody con to_contact_id y client_id explícitos).
 */

export type {
  AllowedMimeType,
  AttachmentOut,
  AttachmentUploadRequest,
  AttachmentUploadResponse,
  EmailForwardStatus,
  FromRole,
  MarkReadResponse,
  MessageOut,
  ThreadSummary,
  UnreadCountResponse,
} from "@/lib/client-messages/schemas";

export {
  ALLOWED_MIME_TYPES,
  EMAIL_FORWARD_STATUS_VALUES,
  FROM_ROLES,
  MAX_ATTACHMENT_BYTES,
} from "@/lib/client-messages/schemas";

// ────────────────────────────────────────────────────────────────────
// Admin — input bodies
// ────────────────────────────────────────────────────────────────────

export interface AdminSendMessageBody {
  body_markdown: string;
  client_id?: string | null;
  thread_id?: string | null;
  project_id?: string | null;
  to_contact_id?: string | null;
}

// ────────────────────────────────────────────────────────────────────
// Filtros admin inbox
// ────────────────────────────────────────────────────────────────────

export interface AdminInboxFilters {
  client_id?: string | null;
  contact_id?: string | null;
  only_unread?: boolean;
}
