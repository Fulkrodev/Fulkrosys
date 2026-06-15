"use client";

/**
 * AdminChatPanel · admin↔cliente chat from /admin/projects/[id]/chat
 * (CLUSTER 5 Phase 5C delta · mirror ClientChatPage pattern · R30 inverso
 * admin lingo).
 *
 * SSE realtime via useProjectEvents · admin recv chat_message_new ONLY
 * when sender_type=client (backend audience filter sse_dispatcher).
 * Auto mark-read on visibility · audit_log emit chat.message.read.
 *
 * Filosofía cliente-mínimo R30 inverso · admin VE messages + RESPONDE ·
 * NO cliente lingo mostrado.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { adminChatApi, SlaStatus } from "@/lib/api/admin-chat";
import type { ChatMessage, ChatThread } from "@/lib/api/client-portal-chat";
import { useProjectEvents } from "@/lib/admin-dashboard/useProjectEvents";
import { cn } from "@/lib/utils";

interface Props {
  projectId: string;
}

export function AdminChatPanel({ projectId }: Props) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const { data: threads = [], isLoading: threadsLoading } = useQuery<
    ChatThread[]
  >({
    queryKey: ["admin-chat", projectId, "threads"],
    queryFn: () => adminChatApi.listThreads(projectId),
  });

  const activeThread = threads[0];

  // CLUSTER 5 Phase 5C delta · admin SSE realtime · §2.7 audit-2026-06-15: una
  // SOLA conexión SSE (antes este componente abría un 2º EventSource al mismo
  // canal). chat_message_new lo sirve el propio hook vía onChatMessageNew.
  useProjectEvents({
    projectId,
    enabled: Boolean(projectId),
    onChatMessageNew: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-chat", projectId] });
    },
  });

  const { data: messages = [], isLoading: messagesLoading } = useQuery<
    ChatMessage[]
  >({
    queryKey: ["admin-chat", projectId, "messages", activeThread?.id],
    queryFn: () =>
      activeThread
        ? adminChatApi.listMessages(projectId, activeThread.id)
        : Promise.resolve([]),
    enabled: Boolean(activeThread?.id),
  });

  const { data: sla } = useQuery<SlaStatus | null>({
    queryKey: ["admin-chat", projectId, "sla", activeThread?.id],
    queryFn: () =>
      activeThread
        ? adminChatApi.getSla(projectId, activeThread.id)
        : Promise.resolve(null),
    enabled: Boolean(activeThread?.id),
    refetchInterval: 60_000,
  });

  const sendMutation = useMutation({
    mutationFn: () =>
      activeThread
        ? adminChatApi.postMessage(projectId, activeThread.id, draft)
        : Promise.reject(new Error("no thread")),
    onSuccess: () => {
      setDraft("");
      queryClient.invalidateQueries({
        queryKey: ["admin-chat", projectId],
      });
    },
  });

  const markReadMutation = useMutation({
    mutationFn: () =>
      activeThread
        ? adminChatApi.markRead(projectId, activeThread.id)
        : Promise.reject(new Error("no thread")),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["admin-chat", projectId],
      }),
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  // Auto mark-read on visibility (admin sees cliente messages → bulk mark).
  useEffect(() => {
    if (!activeThread) return;
    const hasUnreadClient = messages.some(
      (m) => m.sender_type === "client" && !m.read_at,
    );
    if (hasUnreadClient && !markReadMutation.isPending) {
      markReadMutation.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeThread?.id, messages.length]);

  if (threadsLoading) {
    return (
      <Card>
        <CardContent
          className="flex items-center gap-2 p-6 text-sm text-muted-foreground"
          data-testid="admin-chat-loading"
        >
          <Loader2 className="h-4 w-4 animate-spin" /> Cargando inbox…
        </CardContent>
      </Card>
    );
  }

  if (!activeThread) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Inbox cliente</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Sin hilos abiertos · cliente aún no inició conversación.
          </p>
        </CardContent>
      </Card>
    );
  }

  const slaBreached = sla?.sla_breached === true;
  const canSend = draft.trim().length > 0 && !sendMutation.isPending;

  return (
    <div className="flex flex-col gap-4" data-testid="admin-chat-active">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Inbox cliente
            {slaBreached ? (
              <span
                className="ml-2 inline-flex items-center gap-1 rounded bg-fulkro-danger/15 px-2 py-0.5 text-xs text-fulkro-danger"
                data-testid="admin-chat-sla-breached"
              >
                <AlertTriangle className="h-3 w-3" strokeWidth={2.3} />
                SLA 2h superado
              </span>
            ) : null}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {activeThread.subject || "Hilo abierto"} ·{" "}
            {activeThread.messages_count} mensajes
            {sla?.minutes_since_last_client_msg != null
              ? ` · último cliente hace ${sla.minutes_since_last_client_msg} min`
              : ""}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex h-[450px] flex-col gap-3 p-4">
          <div
            className="flex-1 space-y-2 overflow-y-auto"
            aria-live="polite"
            aria-label="Inbox cliente"
          >
            {messagesLoading ? (
              <p className="text-sm text-muted-foreground">
                Cargando mensajes…
              </p>
            ) : messages.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Sin mensajes en este hilo.
              </p>
            ) : (
              messages.map((m) => (
                <AdminMessageBubble key={m.id} message={m} />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="flex gap-2">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Responder al cliente..."
              rows={2}
              aria-label="Respuesta admin"
              className="flex-1 rounded border bg-card p-2 text-sm"
              data-testid="admin-chat-input"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && canSend) {
                  e.preventDefault();
                  sendMutation.mutate();
                }
              }}
            />
            <Button
              onClick={() => sendMutation.mutate()}
              disabled={!canSend}
              aria-label="Enviar respuesta"
              data-testid="admin-chat-send"
            >
              {sendMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" strokeWidth={2.3} />
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AdminMessageBubble({ message }: { message: ChatMessage }) {
  const isAdmin = message.sender_type === "admin";
  return (
    <div
      className={cn(
        "flex",
        isAdmin ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[75%] rounded-lg px-3 py-2 text-sm",
          isAdmin
            ? "bg-fulkro-info/10 text-fulkro-info"
            : "bg-muted text-foreground",
        )}
        data-testid={`admin-chat-message-${message.sender_type}`}
      >
        <p className="whitespace-pre-line">{message.content}</p>
        {message.created_at && (
          <p className="mt-1 text-xs text-muted-foreground">
            {new Date(message.created_at).toLocaleString("es")}
          </p>
        )}
      </div>
    </div>
  );
}
