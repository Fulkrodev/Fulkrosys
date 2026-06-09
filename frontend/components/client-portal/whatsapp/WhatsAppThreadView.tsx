"use client";

/**
 * WhatsAppThreadView · MB-8 atom 8.3 Q7.C.
 *
 * Bidirectional thread cliente↔Marcos · reused both portal cliente UI
 * y admin · pure display component (parent feeds messages).
 */
import { CheckCheck, Loader2 } from "lucide-react";

import type { WhatsAppMessage } from "@/lib/api/whatsapp";


interface Props {
  messages: WhatsAppMessage[];
  loading?: boolean;
}


function formatTs(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("es-ES", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}


export function WhatsAppThreadView({ messages, loading }: Props) {
  if (loading) {
    return (
      <div className="grid place-items-center py-8 text-[color:var(--fulkro-muted)]">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }
  if (!messages.length) {
    return (
      <p className="py-8 text-center text-sm text-[color:var(--fulkro-muted)]">
        Aún no hay mensajes en este hilo.
      </p>
    );
  }
  return (
    <ul
      className="space-y-3 px-4 py-4"
      data-testid="whatsapp-thread-messages"
    >
      {messages.map((m) => {
        const isOutbound = m.direction === "outbound";
        return (
          <li
            key={m.id}
            className={`flex ${isOutbound ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
                isOutbound
                  ? "bg-emerald-500/15 text-emerald-900"
                  : "bg-fulkro-surface-glass-strong text-[color:var(--fulkro-body)]"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              <div className="mt-1 flex items-center justify-end gap-1 text-[11px] text-[color:var(--fulkro-muted)]">
                <span>{formatTs(m.sent_at)}</span>
                {isOutbound && m.read_at && (
                  <CheckCheck className="h-3 w-3 text-emerald-600" aria-label="leído" />
                )}
                {isOutbound && !m.read_at && m.delivered_at && (
                  <CheckCheck className="h-3 w-3" aria-label="entregado" />
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
