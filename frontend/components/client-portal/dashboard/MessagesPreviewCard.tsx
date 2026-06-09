"use client";

/**
 * MessagesPreviewCard · zone 3 dashboard.
 *
 * Last 3 chat messages preview · link to /inbox full thread.
 */
import Link from "next/link";
import { MessageSquareDot, MessageSquare } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RecentMessage } from "@/lib/api/dashboard";

interface Props {
  messages: RecentMessage[];
  unread: number;
}

function formatTime(iso: string | null): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleString("es-ES", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function MessagesPreviewCard({ messages, unread }: Props) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          Mensajes
          {unread > 0 && (
            <span className="rounded-full bg-rose-500 px-2 py-0.5 text-xs font-bold text-white">
              {unread}
            </span>
          )}
        </CardTitle>
        <Link
          href="/client-portal/inbox"
          className="text-sm font-bold text-[color:var(--fulkro-accent)] hover:underline"
        >
          Ver todos →
        </Link>
      </CardHeader>
      <CardContent>
        {messages.length === 0 ? (
          <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--fulkro-muted)]">
            <MessageSquare className="h-4 w-4" />
            Sin mensajes recientes.
          </div>
        ) : (
          <ul className="space-y-3" data-testid="messages-preview">
            {messages.map((msg) => (
              <li
                key={msg.id}
                className="rounded-lg border border-fulkro-surface-glass-border bg-fulkro-surface-glass-strong px-3 py-2"
              >
                <div className="flex items-start gap-2">
                  <MessageSquareDot className="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--fulkro-subtitle)]" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2 text-xs font-medium text-[color:var(--fulkro-muted)]">
                      <span className="font-bold">
                        {msg.sender_type === "admin"
                          ? "Marcos"
                          : msg.sender_type === "cliente"
                          ? "Tú"
                          : "Sistema"}
                      </span>
                      <span>{formatTime(msg.created_at)}</span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-sm text-[color:var(--fulkro-body)]">
                      {msg.preview}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
