"use client";

import { Loader2, Send, Sparkles, X } from "lucide-react";
import * as React from "react";

import { ActionChip } from "@/components/agents/ActionChip";
import { AgentCitation } from "@/components/agents/AgentCitation";
import { Button } from "@/components/ui/button";
import { useCopilot } from "@/hooks/useCopilot";
import type { CopilotMessage } from "@/lib/sprint4-types";
import { cn } from "@/lib/utils";

interface CopilotChatProps {
  /** Extra context the UI can display below the title (project name, etc.). */
  subtitle?: string;
  /** Compact mode for the floating side panel; full mode for the /copilot page. */
  variant?: "panel" | "fullscreen";
  /** Close handler for the side-panel variant. */
  onClose?: () => void;
}

const SUGGESTED_PROMPTS = [
  "¿Qué evidencias me faltan para op.acc.6?",
  "Estado del dossier de auditoría",
  "Próximos hitos del proyecto",
];

export function CopilotChat({
  subtitle,
  variant = "panel",
  onClose,
}: CopilotChatProps) {
  const { messages, isStreaming, sendMessage, clear } = useCopilot();
  const [input, setInput] = React.useState("");
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput("");
    await sendMessage(text);
  }

  const full = variant === "fullscreen";

  return (
    <div
      className={cn(
        "flex flex-col",
        full
          ? "h-[calc(100dvh-10rem)] rounded-xl border border-[color:var(--fulkro-surface-glass-border)] shadow-md"
          : "h-full",
      )}
      style={
        full
          ? { backgroundColor: "var(--fulkro-surface-glass)", backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" }
          : undefined
      }
    >
      <header
        className="flex items-start justify-between gap-2 border-b p-4"
        style={{
          borderColor: "var(--fulkro-surface-glass-border)",
          backgroundColor: "var(--fulkro-surface-glass-strong)",
        }}
      >
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-base font-bold text-[color:var(--fulkro-title)]">
            <Sparkles size={18} strokeWidth={2.4} />
            Copiloto FULKRO
          </p>
          <p className="truncate text-sm font-medium text-[color:var(--fulkro-muted)]">
            {subtitle ?? "Agente 14 · Conversacional"}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={clear}
            disabled={isStreaming}
            className="text-sm font-semibold"
          >
            Limpiar
          </Button>
          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              aria-label="Cerrar copiloto"
            >
              <X size={16} strokeWidth={2.4} />
            </Button>
          )}
        </div>
      </header>

      <div ref={scrollRef} className="scrollbar-fulkro-light flex-1 space-y-4 overflow-y-auto p-4">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {messages.length <= 1 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {SUGGESTED_PROMPTS.map((p) => (
              <button
                key={p}
                type="button"
                style={{
                  backgroundColor: "var(--fulkro-surface-glass)",
                  borderColor: "var(--fulkro-surface-glass-border)",
                }}
                className="rounded-full border px-3.5 py-1.5 text-sm font-medium text-[color:var(--fulkro-subtitle)] transition-colors hover:bg-[color:var(--fulkro-surface-glass-strong)]"
                onClick={() => sendMessage(p)}
                disabled={isStreaming}
              >
                {p}
              </button>
            ))}
          </div>
        )}
      </div>

      <form
        onSubmit={submit}
        className="flex items-center gap-2 border-t p-3"
        style={{
          borderColor: "var(--fulkro-surface-glass-border)",
          backgroundColor: "var(--fulkro-surface-glass-strong)",
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe a tu copiloto…"
          disabled={isStreaming}
          style={{
            backgroundColor: "rgba(255, 255, 255, 0.65)",
            borderColor: "var(--fulkro-surface-glass-border)",
          }}
          className="flex-1 rounded-md border px-3 py-2.5 text-base font-medium text-[color:var(--fulkro-body)] placeholder:text-[color:var(--fulkro-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700"
        />
        <Button
          type="submit"
          size="icon"
          aria-label="Enviar"
          disabled={isStreaming || !input.trim()}
        >
          {isStreaming ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Send size={16} strokeWidth={2.4} />
          )}
        </Button>
      </form>
    </div>
  );
}

function MessageBubble({ message }: { message: CopilotMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        style={
          isUser
            ? { background: "var(--fulkro-sidebar-gradient)" }
            : {
                backgroundColor: "var(--fulkro-surface-glass-strong)",
                borderColor: "var(--fulkro-surface-glass-border)",
              }
        }
        className={cn(
          "max-w-[85%] space-y-2 rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed",
          isUser
            ? "text-white shadow-sm"
            : "border text-[color:var(--fulkro-body)]",
        )}
      >
        <p className="whitespace-pre-wrap font-medium">
          {message.content}
          {message.streaming && (
            <span
              className={cn(
                "ml-1 inline-block h-3.5 w-1 translate-y-0.5 animate-pulse rounded-sm",
                isUser ? "bg-white/70" : "bg-[color:var(--fulkro-subtitle)]",
              )}
            />
          )}
        </p>

        {message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {message.citations.map((c) => (
              <AgentCitation key={c.id} citation={c} />
            ))}
          </div>
        )}

        {message.actions && message.actions.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {message.actions.map((a) => (
              <ActionChip key={a.id} action={a} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
