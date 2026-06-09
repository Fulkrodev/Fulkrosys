"use client";

/**
 * React Query hooks ClientNotifications (SAN-E v3.MB-4.bis3).
 *
 * Polling: inbox cada 30s · unread count cada 15s para badge UI.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  countUnread,
  dismiss,
  listInbox,
  markActioned,
  markRead,
} from "@/lib/client-notifications/api";

export const inboxKeys = {
  all: () => ["client-inbox"] as const,
  list: (opts?: { include_read?: boolean; include_dismissed?: boolean }) =>
    ["client-inbox", "list", opts ?? {}] as const,
  unreadCount: () => ["client-inbox", "unread-count"] as const,
};

export function useInbox(opts?: {
  include_read?: boolean;
  include_dismissed?: boolean;
}) {
  return useQuery({
    queryKey: inboxKeys.list(opts),
    queryFn: () => listInbox(opts),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: inboxKeys.unreadCount(),
    queryFn: countUnread,
    staleTime: 15_000,
    refetchInterval: 15_000,
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) => markRead(notificationId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["client-inbox"] });
    },
  });
}

export function useDismiss() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) => dismiss(notificationId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["client-inbox"] });
    },
  });
}

export function useMarkActioned() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) => markActioned(notificationId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["client-inbox"] });
    },
  });
}
