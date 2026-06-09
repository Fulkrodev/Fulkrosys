"use client";

/**
 * useCopilotConversations · memoria conversacional del copiloto admin (#23 Ola 5).
 *
 * Wrappers tanstack-query sobre el cliente API copilot-conversations (CRUD que
 * ya existía en backend · Sesión 3B-2B.4 Phase 2.4 · sin UI hasta ahora).
 *
 * Memoria POR PROYECTO · el RLS `copilot_isolation` se respeta server-side.
 * Persiste-primero: el envío usa el endpoint no-stream existente.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createConversation,
  deleteConversation,
  getConversation,
  listMemoryProjects,
  listProjectConversations,
  sendConversationChat,
  type ConversationChatBody,
  type CreateConversationBody,
} from "@/lib/api/copilot-conversations";

const KEYS = {
  projects: ["copilot-memory-projects"] as const,
  conversations: (projectId: string) =>
    ["copilot-conversations", projectId] as const,
  conversation: (projectId: string, conversationId: string) =>
    ["copilot-conversation", projectId, conversationId] as const,
};

/** Lista proyectos para el selector de memoria. */
export function useMemoryProjects() {
  return useQuery({
    queryKey: KEYS.projects,
    queryFn: listMemoryProjects,
  });
}

/** Lista conversaciones de un proyecto (la barra lateral). */
export function useProjectConversations(projectId: string | null) {
  return useQuery({
    queryKey: KEYS.conversations(projectId ?? "none"),
    queryFn: () => listProjectConversations(projectId as string),
    enabled: !!projectId,
    select: (data) => data.conversations,
  });
}

/** Detalle + historial de mensajes de una conversación (el recall). */
export function useConversation(
  projectId: string | null,
  conversationId: string | null,
) {
  return useQuery({
    queryKey: KEYS.conversation(projectId ?? "none", conversationId ?? "none"),
    queryFn: () =>
      getConversation(projectId as string, conversationId as string),
    enabled: !!projectId && !!conversationId,
  });
}

export function useCreateConversation(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateConversationBody) =>
      createConversation(projectId as string, body),
    onSuccess: () => {
      if (projectId) {
        void qc.invalidateQueries({ queryKey: KEYS.conversations(projectId) });
      }
    },
  });
}

export function useDeleteConversation(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) =>
      deleteConversation(projectId as string, conversationId),
    onSuccess: () => {
      if (projectId) {
        void qc.invalidateQueries({ queryKey: KEYS.conversations(projectId) });
      }
    },
  });
}

/**
 * Envía un mensaje y persiste (user + assistant). Al terminar invalida el
 * detalle de la conversación → el historial se re-pinta con lo recién guardado.
 */
export function useSendConversationMessage(
  projectId: string | null,
  conversationId: string | null,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ConversationChatBody) =>
      sendConversationChat(
        projectId as string,
        conversationId as string,
        body,
      ),
    onSuccess: () => {
      if (projectId && conversationId) {
        void qc.invalidateQueries({
          queryKey: KEYS.conversation(projectId, conversationId),
        });
        void qc.invalidateQueries({
          queryKey: KEYS.conversations(projectId),
        });
      }
    },
  });
}
