"use client";

/**
 * CopilotConversationChat · chat con MEMORIA persistida por proyecto (#23 Ola 5).
 *
 * A diferencia de CopilotChat (stateless, streaming RAG), este panel carga el
 * historial real de una conversación (getConversation) y envía por el endpoint
 * que PERSISTE user+assistant (sendConversationChat). Recall verdadero: al
 * recargar la página, la conversación sigue ahí.
 *
 * Persiste-primero (sin streaming · decisión Ola 5). Streaming = fast-follow.
 */
import { Loader2, Send } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  useConversation,
  useSendConversationMessage,
} from "@/hooks/useCopilotConversations";
import type { CopilotConversationMessage } from "@/lib/api/copilot-conversations";
import { cn } from "@/lib/utils";

interface CopilotConversationChatProps {
  projectId: string;
  conversationId: string;
}

export function CopilotConversationChat({
  projectId,
  conversationId,
}: CopilotConversationChatProps) {
  const { data, isLoading, isError, refetch } = useConversation(
    projectId,
    conversationId,
  );
  const sendMutation = useSendConversationMessage(projectId, conversationId);
  const [input, setInput] = React.useState("");
  const scrollRef = React.useRef<HTMLDivElement>(null);

  const messages = data?.messages ?? [];

  React.useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.length, sendMutation.isPending]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const content = input.trim();
    if (!content || sendMutation.isPending) return;
    setInput("");
    try {
      await sendMutation.mutateAsync({ content, include_project_context: true });
    } catch {
      // Restaura el texto para que Marcos no lo pierda si falla.
      setInput(content);
    }
  }

  return (
    <div
      className="flex h-[calc(100dvh-16rem)] min-h-[24rem] flex-col rounded-xl border bg-card"
      data-testid="copilot-memory-chat"
    >
      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto p-4"
        data-testid="copilot-memory-messages"
      >
        {isLoading && (
          <p className="text-sm text-muted-foreground">Cargando conversación…</p>
        )}
        {isError && (
          <div
            role="alert"
            className="space-y-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
          >
            <p>No he podido cargar esta conversación.</p>
            <Button size="sm" variant="outline" onClick={() => void refetch()}>
              Reintentar
            </Button>
          </div>
        )}
        {!isLoading && !isError && messages.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Conversación nueva. Escribe tu primera pregunta abajo · quedará
            guardada en este proyecto.
          </p>
        )}
        {messages.map((m) => (
          <MemoryBubble key={m.id} message={m} />
        ))}
        {sendMutation.isPending && (
          <div className="flex justify-start">
            <div className="rounded-2xl border bg-muted/40 px-4 py-2.5 text-sm text-muted-foreground">
              <Loader2 className="inline size-3.5 animate-spin" /> Pensando…
            </div>
          </div>
        )}
      </div>

      <form
        onSubmit={submit}
        className="flex items-center gap-2 border-t p-3"
        data-testid="copilot-memory-form"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe a tu copiloto… (se guarda en este proyecto)"
          disabled={sendMutation.isPending}
          aria-label="Mensaje al copiloto"
          className="flex-1 rounded-md border bg-background px-3 py-2.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        />
        <Button
          type="submit"
          size="icon"
          aria-label="Enviar"
          disabled={sendMutation.isPending || !input.trim()}
        >
          {sendMutation.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Send className="size-4" />
          )}
        </Button>
      </form>
    </div>
  );
}

function MemoryBubble({ message }: { message: CopilotConversationMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground"
            : "border bg-muted/40 text-foreground",
        )}
      >
        {message.content}
      </div>
    </div>
  );
}
