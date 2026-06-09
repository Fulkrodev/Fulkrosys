/**
 * Attachments helpers — validation client-side ANTES presigned URL request.
 *
 * Defensa profunda: backend valida (CHECK BD + service + Pydantic), pero
 * client-side valida primero para UX (feedback inmediato sin round-trip).
 */

import {
  ALLOWED_MIME_TYPES,
  MAX_ATTACHMENT_BYTES,
  type AllowedMimeType,
} from "./schemas";

export interface ValidationOk {
  ok: true;
}

export interface ValidationError {
  ok: false;
  error: string;
}

export type AttachmentValidationResult = ValidationOk | ValidationError;

/**
 * Valida MIME whitelist + size 10 MB. NO inspecciona contenido (server-side
 * hace HEAD MinIO post-upload para verificar size real).
 */
export function validateAttachment(file: File): AttachmentValidationResult {
  if (file.size === 0) {
    return { ok: false, error: "Archivo vacío." };
  }
  if (file.size > MAX_ATTACHMENT_BYTES) {
    return {
      ok: false,
      error: `Archivo > 10 MB (${(file.size / 1024 / 1024).toFixed(1)} MB). Comprime o divide.`,
    };
  }
  if (!ALLOWED_MIME_TYPES.includes(file.type as AllowedMimeType)) {
    return {
      ok: false,
      error:
        `Tipo no permitido (${file.type || "desconocido"}). Permitidos: ` +
        "PDF, PNG, JPG, GIF, WEBP, DOCX, XLSX, CSV, TXT, ZIP.",
    };
  }
  return { ok: true };
}

/**
 * Genera una etiqueta legible del tamaño del archivo.
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/**
 * Detecta icon emoji apropiado por mime_type.
 */
export function mimeIcon(mime: string): string {
  if (mime.startsWith("image/")) return "🖼";
  if (mime === "application/pdf") return "📄";
  if (mime.includes("wordprocessingml")) return "📝";
  if (mime.includes("spreadsheetml")) return "📊";
  if (mime === "text/csv" || mime === "text/plain") return "📋";
  if (mime === "application/zip") return "🗂";
  return "📎";
}
