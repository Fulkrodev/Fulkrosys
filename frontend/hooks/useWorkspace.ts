"use client";

/**
 * React Query hooks para Motor 20 - Collaborative Workspace (SAN-E v3.MB-4.2).
 *
 * 0 mocks. Endpoints reales (22 totales bajo /api/v1/projects/{id}/workspace).
 * 3 sub-features wired: Files · Chat · Feed (videocalls diferido).
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  addFeedItem,
  archiveWorkspace,
  createWorkspace,
  deleteWorkspaceFile,
  getFeedUnreadCount,
  getFilesTree,
  getWorkspace,
  getWorkspaceSummary,
  listChatMessages,
  listFeedItems,
  listWorkspaceFiles,
  markFeedRead,
  sendChatMessage,
  uploadWorkspaceFile,
  type AddFeedItemBody,
  type ArchiveBody,
  type CreateWorkspaceBody,
  type SendMessageBody,
  type UploadFileBody,
} from "@/lib/admin-workspace/api";

// =====================================================================
// Centralized keys
// =====================================================================

export const workspaceKeys = {
  all: () => ["workspace"] as const,
  workspace: (projectId: string) => ["workspace", "meta", projectId] as const,
  summary: (projectId: string) => ["workspace", "summary", projectId] as const,
  files: (projectId: string, opts?: { carpeta?: string; estado?: string }) =>
    ["workspace", "files", projectId, opts ?? {}] as const,
  filesTree: (projectId: string) => ["workspace", "files-tree", projectId] as const,
  chat: (projectId: string, opts?: { before?: string }) =>
    ["workspace", "chat", projectId, opts ?? {}] as const,
  feed: (projectId: string, opts?: { tipo?: string; limit?: number; offset?: number }) =>
    ["workspace", "feed", projectId, opts ?? {}] as const,
  unreadCount: (projectId: string) =>
    ["workspace", "feed", "unread", projectId] as const,
};

// =====================================================================
// Queries
// =====================================================================

export function useWorkspace(projectId: string) {
  return useQuery({
    queryKey: workspaceKeys.workspace(projectId),
    queryFn: () => getWorkspace(projectId),
    enabled: !!projectId,
    retry: false,
  });
}

export function useWorkspaceSummary(projectId: string) {
  return useQuery({
    queryKey: workspaceKeys.summary(projectId),
    queryFn: () => getWorkspaceSummary(projectId),
    enabled: !!projectId,
    staleTime: 30_000,
    retry: false,
  });
}

export function useWorkspaceFiles(
  projectId: string,
  opts?: { carpeta?: string; estado?: string },
) {
  return useQuery({
    queryKey: workspaceKeys.files(projectId, opts),
    queryFn: () => listWorkspaceFiles(projectId, opts),
    enabled: !!projectId,
  });
}

export function useFilesTree(projectId: string) {
  return useQuery({
    queryKey: workspaceKeys.filesTree(projectId),
    queryFn: () => getFilesTree(projectId),
    enabled: !!projectId,
  });
}

export function useChatMessages(projectId: string, opts?: { before?: string }) {
  return useQuery({
    queryKey: workspaceKeys.chat(projectId, opts),
    queryFn: () => listChatMessages(projectId, { limit: 100, before: opts?.before }),
    enabled: !!projectId,
  });
}

export function useFeedItems(
  projectId: string,
  opts?: { tipo?: string; limit?: number; offset?: number },
) {
  return useQuery({
    queryKey: workspaceKeys.feed(projectId, opts),
    queryFn: () => listFeedItems(projectId, opts),
    enabled: !!projectId,
  });
}

export function useFeedUnreadCount(projectId: string) {
  return useQuery({
    queryKey: workspaceKeys.unreadCount(projectId),
    queryFn: () => getFeedUnreadCount(projectId),
    enabled: !!projectId,
    staleTime: 15_000,
  });
}

// =====================================================================
// Mutations
// =====================================================================

export function useCreateWorkspace(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateWorkspaceBody = {}) => createWorkspace(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workspace"] });
    },
  });
}

export function useArchiveWorkspace(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ArchiveBody = {}) => archiveWorkspace(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.workspace(projectId) });
    },
  });
}

export function useUploadFile(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: UploadFileBody) => uploadWorkspaceFile(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workspace", "files", projectId] });
      void qc.invalidateQueries({ queryKey: workspaceKeys.summary(projectId) });
      void qc.invalidateQueries({ queryKey: workspaceKeys.filesTree(projectId) });
    },
  });
}

export function useDeleteFile(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileId: string) => deleteWorkspaceFile(projectId, fileId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workspace", "files", projectId] });
      void qc.invalidateQueries({ queryKey: workspaceKeys.summary(projectId) });
    },
  });
}

export function useSendMessage(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SendMessageBody) => sendChatMessage(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workspace", "chat", projectId] });
      void qc.invalidateQueries({ queryKey: workspaceKeys.summary(projectId) });
    },
  });
}

export function useAddFeedItem(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AddFeedItemBody) => addFeedItem(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workspace", "feed", projectId] });
      void qc.invalidateQueries({ queryKey: workspaceKeys.unreadCount(projectId) });
    },
  });
}

export function useMarkFeedRead(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => markFeedRead(projectId, itemId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workspace", "feed", projectId] });
      void qc.invalidateQueries({ queryKey: workspaceKeys.unreadCount(projectId) });
    },
  });
}
