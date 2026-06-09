/**
 * Admin WhatsApp API client · MB-8 atom 8.3 Q7.C.
 */
import { api } from "@/lib/api";

import type { WhatsAppMessage } from "@/lib/api/whatsapp";


export interface AdminThread {
  id: string;
  project_id: string;
  client_user_id: string | null;
  status: string;
  last_outbound_at: string | null;
  last_inbound_at: string | null;
  last_message_preview: string | null;
  messages_count: number;
}


export async function adminListThreads(): Promise<{ threads: AdminThread[] }> {
  return api("/api/v1/admin/whatsapp/threads");
}


export async function adminThreadMessages(
  threadId: string,
): Promise<{ messages: WhatsAppMessage[] }> {
  return api(`/api/v1/admin/whatsapp/threads/${threadId}/messages`);
}


export async function adminSendReply(
  threadId: string, content: string,
): Promise<WhatsAppMessage> {
  return api(`/api/v1/admin/whatsapp/threads/${threadId}/send`, {
    method: "POST",
    json: { content },
  });
}


export async function adminInviteOptIn(
  clientUserId: string, phoneRaw: string,
): Promise<{ otp_sent: boolean; phone_e164: string; error: string | null }> {
  return api(`/api/v1/admin/whatsapp/invite/${clientUserId}`, {
    method: "POST",
    json: { phone_raw: phoneRaw },
  });
}
