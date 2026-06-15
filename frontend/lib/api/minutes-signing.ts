/**
 * API client · aprobación/firma de acta (E-005) vía magic-link APROBACION_ACTA.
 *
 * Endpoint PÚBLICO (sin auth · la puerta es el magic-link con OTP · el asistente
 * aprueba SIN cuenta):
 *   POST /api/v1/minutes-signing/approve
 *
 * Reemplaza el antiguo LegacyDocumentSignFlow (mock que NO registraba nada):
 * ahora consume el magic-link y registra la firma real del asistente en m18.
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/minutes-signing";

export interface ApproveActaRequest {
  token: string;
  otp?: string | null;
  accepted: boolean;
}

export interface ApproveActaResponse {
  status: string;
  minutes_id: string;
  estado: string;
  codigo?: string | null;
}

/** Público · aprueba/firma el acta tras la puerta magic-link APROBACION_ACTA. */
export function approveActa(
  req: ApproveActaRequest,
): Promise<ApproveActaResponse> {
  return api<ApproveActaResponse>(`${BASE}/approve`, { json: req });
}
