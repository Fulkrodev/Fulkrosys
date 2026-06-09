"use client";

/**
 * ClientChatPage · cliente↔admin chat con SLA <2h soporte
 * (ADR-038 SAN-D MB-14.6).
 *
 * CLUSTER 5 Phase 5C delta · convert polling → SSE realtime via
 * useClientProjectEvents + onChatMessageNew handler. Auto-invalidate
 * cliente-chat queries on event (DRY pattern reuse from Phase 1A+2A+2D).
 *
 * Mark-read auto-fired on visibility (cliente reads admin messages) ·
 * audit_log emit chat.message.read Sub-atom 5.A (Phase 5B endpoint).
 *
 * Filosofía cliente-mínimo: cliente COMUNICA en lenguaje natural · SSE
 * realtime <2s admin reply · SLA <2h friendly framing R29.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import { useClientProjectId } from "@/hooks/useClientProjectId";
import {
  ChatMessage,
  ChatThread,
  clientChatApi,
} from "@/lib/api/client-portal-chat";
import { cn } from "@/lib/utils";

export function ClientChatPage() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const { projectId } = useClientProjectId();

  const { data: threads = [], isLoading: threadsLoading } = useQuery<
    ChatThread[]
  >({
    queryKey: ["client-chat", "threads"],
    queryFn: () => clientChatApi.listThreads(),
  });

  const activeThread = threads[0];

  // CLUSTER 5 Phase 5C delta · SSE realtime convert.
  // Polling fallback removed · EventSource auto-reconnect on network blips ·
  // backend audience filter sender_type=admin → cliente recv (NO own echo).
  useClientProjectEvents(projectId, {
    enabled: Boolean(projectId),
    onChatMessageNew: () => {
      queryClient.invalidateQueries({ queryKey: ["client-chat"] });
    },
  });

  const createThreadMutation = useMutation({
    mutationFn: () => clientChatApi.createThread("Consulta general"),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["client-chat"] }),
  });

  const { data: messages = [], isLoading: messagesLoading } = useQuery<
    ChatMessage[]
  >({
    queryKey: ["client-chat", "messages", activeThread?.id],
    queryFn: () =>
      activeThread
        ? clientChatApi.listMessages(activeThread.id)
        : Promise.resolve([]),
    enabled: Boolean(activeThread?.id),
  });

  const sendMutation = useMutation({
    mutationFn: () =>
      activeThread
        ? clientChatApi.postMessage(activeThread.id, draft)
        : Promise.reject(new Error("no thread")),
    onSuccess: () => {
      setDraft("");
      queryClient.invalidateQueries({ queryKey: ["client-chat"] });
    },
  });

  const markReadMutation = useMutation({
    mutationFn: () =>
      activeThread
        ? clientChatApi.markRead(activeThread.id)
        : Promise.reject(new Error("no thread")),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["client-chat"] }),
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  // CLUSTER 5 Phase 5C delta · auto mark-read when cliente sees admin
  // messages (any unread admin message → bulk mark on render). Idempotent
  // backend (Phase 5B returns 0 if nothing unread).
  useEffect(() => {
    if (!activeThread) return;
    const hasUnreadAdmin = messages.some(
      (m) => m.sender_type === "admin" && !m.read_at,
    );
    if (hasUnreadAdmin && !markReadMutation.isPending) {
      markReadMutation.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeThread?.id, messages.length]);

  if (threadsLoading) {
    return (
      <Card>
        <CardContent
          className="flex items-center gap-2 p-6 text-sm text-muted-foreground"
          data-testid="client-chat-loading"
        >
          <Loader2 className="h-4 w-4 animate-spin" /> Cargando chat…
        </CardContent>
      </Card>
    );
  }

  if (!activeThread) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Chat con Marcos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            SLA respuesta &lt;2h en horario laboral. Inicia conversación
            cuando lo necesites.
          </p>
          <Button
            onClick={() => createThreadMutation.mutate()}
            disabled={createThreadMutation.isPending}
            data-testid="client-chat-start"
          >
            {createThreadMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            Iniciar chat
          </Button>
        </CardContent>
      </Card>
    );
  }

  const canSend = draft.trim().length > 0 && !sendMutation.isPending;

  return (
    <div className="flex flex-col gap-4" data-testid="client-chat-active">
      <Card>
        <CardHeader>
          <CardTitle>Chat con Marcos · SLA &lt;2h</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {activeThread.subject || "Conversación abierta"} ·{" "}
            {activeThread.messages_count} mensajes
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex h-[450px] flex-col gap-3 p-4">
          <div
            className="flex-1 space-y-2 overflow-y-auto"
            aria-live="polite"
            aria-label="Conversación con Marcos"
          >
            {messagesLoading ? (
              <p className="text-sm text-muted-foreground">
                Cargando mensajes…
              </p>
            ) : messages.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Aún sin mensajes. Escribe el primero.
              </p>
            ) : (
              messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="flex gap-2">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Escribe a Marcos..."
              rows={2}
              aria-label="Mensaje a Marcos"
              className="flex-1 rounded border bg-card p-2 text-sm"
              data-testid="client-chat-input"
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
              aria-label="Enviar mensaje"
              data-testid="client-chat-send"
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

function MessageBubble({ message }: { message: ChatMessage }) {
  const isClient = message.sender_type === "client";
  return (
    <div
      className={cn(
        "flex",
        isClient ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[75%] rounded-lg px-3 py-2 text-sm",
          isClient
            ? "bg-fulkro-info/10 text-fulkro-info"
            : "bg-muted text-foreground",
        )}
        data-testid={`client-chat-message-${message.sender_type}`}
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
