/**
 * Client Chat API · cliente portal (ADR-038 SAN-D MB-14.5/6).
 */
import { clientApi } from "@/lib/client-portal-api";

export type ChatSenderType = "client" | "admin" | "system";

export interface ChatThread {
  id: string;
  project_id: string;
  subject: string | null;
  status: string;
  messages_count: number;
  last_client_message_at: string | null;
  last_admin_response_at: string | null;
  created_at: string | null;
}

export interface ChatMessage {
  id: string;
  thread_id: string;
  sender_type: ChatSenderType;
  sender_user_id: string | null;
  content: string;
  created_at: string | null;
  /** CLUSTER 5 Phase 5A delta · read tracking (NULL = unread by counterparty). */
  read_at?: string | null;
}

export const clientChatApi = {
  listThreads: (): Promise<ChatThread[]> =>
    clientApi<ChatThread[]>("/client-portal/chat/threads"),

  createThread: (subject?: string): Promise<ChatThread> =>
    clientApi<ChatThread>("/client-portal/chat/threads", {
      method: "POST",
      json: { subject: subject ?? null },
    }),

  listMessages: (threadId: string): Promise<ChatMessage[]> =>
    clientApi<ChatMessage[]>(
      `/client-portal/chat/threads/${threadId}/messages`,
    ),

  postMessage: (threadId: string, content: string): Promise<ChatMessage> =>
    clientApi<ChatMessage>(
      `/client-portal/chat/threads/${threadId}/messages`,
      {
        method: "POST",
        json: { content },
      },
    ),

  /** CLUSTER 5 Phase 5B delta · cliente bulk-marks admin messages as read. */
  markRead: (threadId: string): Promise<{ marked_count: number }> =>
    clientApi<{ marked_count: number }>(
      `/client-portal/chat/threads/${threadId}/mark-read`,
      { method: "POST" },
    ),
};
