/**
 * API client · firma del contrato comercial con canvas Ed25519 (#43).
 *
 * Endpoint PÚBLICO (sin auth · la puerta es el magic-link FIRMA_CONTRATO con
 * OTP + geo · el lead firma SIN cuenta · la firma crea al cliente #7):
 *   POST /api/v1/contract-signing/confirm
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/contract-signing";

export interface ConfirmContractSignatureRequest {
  token: string;
  otp: string;
  signature_canvas_dataurl: string;
  signed_name: string;
  signed_surname: string;
  geo_lat?: number | null;
  geo_lon?: number | null;
}

export interface ConfirmContractSignatureResponse {
  status: string;
  contract_id: string;
  signed_at?: string;
  signing_intent_id?: string;
  signing_event_id?: string;
  event_hash_sha256?: string;
  signer_user_id?: string;
}

/**
 * Público · firma el contrato comercial vía canvas Ed25519 tras la puerta
 * magic-link FIRMA_CONTRATO. La firma es atómica con la conversión #7
 * (promueve el proyecto + crea el cliente).
 */
export function confirmContractSignature(
  req: ConfirmContractSignatureRequest,
): Promise<ConfirmContractSignatureResponse> {
  return api<ConfirmContractSignatureResponse>(`${BASE}/confirm`, { json: req });
}

/**
 * #34 (FRENTE B) · descarga el DOCX EXACTO que se va a firmar ANTES de firmar
 * (cierra el "contrato mudo"). Endpoint público read-only que NO consume el
 * magic-link · el token es la credencial. WYSIWYS (lo que firmas es lo que lees).
 */
export async function downloadContractPreview(token: string): Promise<void> {
  const res = await fetch(
    `${BASE}/preview?token=${encodeURIComponent(token)}`,
    { credentials: "include" },
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "contrato_servicios_fulkro.docx";
  a.click();
  URL.revokeObjectURL(url);
}
