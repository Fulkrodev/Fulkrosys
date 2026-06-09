/**
 * Admin Chat API · admin inbox (ADR-038 SAN-D MB-14.5/6).
 */
import { api } from "@/lib/api";
import type { ChatMessage, ChatThread } from "@/lib/api/client-portal-chat";

export interface SlaStatus {
  thread_id: string;
  sla_breached: boolean;
  reason: string;
  minutes_since_last_client_msg: number | null;
  sla_threshold_minutes?: number;
}

export const adminChatApi = {
  listThreads: (projectId: string, status?: string): Promise<ChatThread[]> => {
    const qs = status ? `?status_filter=${status}` : "";
    return api<ChatThread[]>(
      `/api/v1/admin/projects/${projectId}/chat/threads${qs}`,
    );
  },

  listMessages: (
    projectId: string,
    threadId: string,
  ): Promise<ChatMessage[]> =>
    api<ChatMessage[]>(
      `/api/v1/admin/projects/${projectId}/chat/threads/${threadId}/messages`,
    ),

  postMessage: (
    projectId: string,
    threadId: string,
    content: string,
  ): Promise<ChatMessage> =>
    api<ChatMessage>(
      `/api/v1/admin/projects/${projectId}/chat/threads/${threadId}/messages`,
      { method: "POST", json: { content } },
    ),

  getSla: (projectId: string, threadId: string): Promise<SlaStatus> =>
    api<SlaStatus>(
      `/api/v1/admin/projects/${projectId}/chat/threads/${threadId}/sla`,
    ),

  /** CLUSTER 5 Phase 5B delta · admin bulk-marks client messages as read. */
  markRead: (
    projectId: string,
    threadId: string,
  ): Promise<{ marked_count: number }> =>
    api<{ marked_count: number }>(
      `/api/v1/admin/projects/${projectId}/chat/threads/${threadId}/mark-read`,
      { method: "POST" },
    ),
};
