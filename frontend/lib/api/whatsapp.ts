/**
 * WhatsApp portal API client · MB-8 atom 8.3.
 *
 * Hits /api/v1/client-portal/whatsapp/* endpoints (Q3.D opt-in + Q7.C UI).
 */
import { clientApi } from "@/lib/client-portal-api";


export interface WhatsAppStatus {
  whatsapp_number: string | null;
  verified: boolean;
  opt_in_active: boolean;
  verified_at: string | null;
  opt_in_at: string | null;
  // M13 · false en modo demo (sin proveedor real) → mostrar "próximamente",
  // no el formulario de opt-in (el OTP nunca llegaría).
  provider_available?: boolean;
}


export interface WhatsAppMessage {
  id: string;
  thread_id: string;
  direction: "outbound" | "inbound";
  sender_type: "system" | "marcos" | "cliente";
  content: string;
  whatsapp_message_id: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  failed_at: string | null;
  failure_reason: string | null;
}


export interface WhatsAppThreadInfo {
  id: string;
  status: string;
  messages_count: number;
  last_inbound_at: string | null;
  last_outbound_at: string | null;
}


export async function fetchStatus(): Promise<WhatsAppStatus> {
  return clientApi<WhatsAppStatus>("/client-portal/whatsapp/status");
}


export async function verifyPhone(
  phoneRaw: string,
): Promise<{ phone_e164: string; otp_sent: boolean; error: string | null }> {
  return clientApi("/client-portal/whatsapp/verify-phone", {
    method: "POST",
    json: { phone_raw: phoneRaw },
  });
}


export async function verifyOtp(otp: string): Promise<{ verified: boolean }> {
  return clientApi("/client-portal/whatsapp/verify-otp", {
    method: "POST",
    json: { otp },
  });
}


export async function fetchThread(): Promise<{ thread: WhatsAppThreadInfo | null }> {
  return clientApi("/client-portal/whatsapp/thread");
}


export async function fetchThreadMessages(): Promise<{ messages: WhatsAppMessage[] }> {
  return clientApi("/client-portal/whatsapp/thread/messages");
}


export async function exportRgpd(): Promise<unknown> {
  return clientApi("/client-portal/whatsapp/export");
}
