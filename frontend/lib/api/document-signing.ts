/**
 * API client · firma de documento (acta E-012 / MAGERIT E-028 / DdA E-040 /
 * conformidad) vía magic-link FIRMA_DOCUMENTO.
 *
 * Endpoint PÚBLICO (sin auth · la puerta es el magic-link con OTP · el firmante
 * —Responsable de la Información/Servicio, Dirección, RSEG— firma SIN cuenta):
 *   POST /api/v1/document-signing/sign
 *
 * §3.1 audit-2026-06-15 · reemplaza el mock LegacyDocumentSignFlow (que fingía la
 * firma con setTimeout sin registrar nada): ahora consume el magic-link y registra
 * la firma Ed25519 REAL sobre el hash del snapshot del documento (hash chain R6).
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/document-signing";

export interface SignDocumentRequest {
  token: string;
  otp?: string | null;
  accepted: boolean;
}

export interface SignDocumentResponse {
  status: string;
  document_type?: string | null;
  label?: string | null;
  event_hash?: string | null;
}

/** Público · firma el documento tras la puerta magic-link FIRMA_DOCUMENTO. */
export function signDocument(
  req: SignDocumentRequest,
): Promise<SignDocumentResponse> {
  return api<SignDocumentResponse>(`${BASE}/sign`, { json: req });
}
