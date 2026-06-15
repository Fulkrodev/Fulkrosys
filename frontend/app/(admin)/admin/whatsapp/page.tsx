"use client";

/**
 * /admin/whatsapp · MB-8 atom 8.3 Q7.C.
 *
 * Threads cross-cliente list (izquierda) + selected thread view (derecha)
 * + reply composer.
 */
import { Loader2, MessageCircle, Send } from "lucide-react";
import { useEffect, useState } from "react";

import { WhatsAppThreadView } from "@/components/client-portal/whatsapp/WhatsAppThreadView";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useInboundWhatsAppSSE } from "@/hooks/useInboundWhatsAppSSE";
import {
  type AdminThread,
  adminListThreads,
  adminSendReply,
  adminThreadMessages,
} from "@/lib/api/admin-whatsapp";
import type { WhatsAppMessage } from "@/lib/api/whatsapp";


function formatTs(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}


export default function AdminWhatsAppPage() {
  const [threads, setThreads] = useState<AdminThread[]>([]);
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<WhatsAppMessage[]>([]);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    adminListThreads()
      .then((d) => {
        if (cancelled) return;
        setThreads(d.threads);
        if (d.threads.length && !selectedId) setSelectedId(d.threads[0].id);
      })
      .finally(() => {
        if (!cancelled) setLoadingThreads(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setLoadingMsgs(true);
    adminThreadMessages(selectedId)
      .then((d) => {
        if (!cancelled) setMessages(d.messages);
      })
      .catch(() => {
        if (!cancelled) setMessages([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingMsgs(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  // SSE realtime inbound · Sprint Polish 2.D (extracted to useInboundWhatsAppSSE).
  const { latestMessage } = useInboundWhatsAppSSE({
    threadId: selectedId,
    mode: "admin",
  });
  useEffect(() => {
    if (!latestMessage) return;
    setMessages((prev) => {
      if (prev.some((p) => p.id === latestMessage.id)) return prev;
      return [...prev, latestMessage];
    });
  }, [latestMessage]);

  const onSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId || !reply.trim()) return;
    setSending(true);
    try {
      const m = await adminSendReply(selectedId, reply);
      setMessages((prev) => [...prev, m]);
      setReply("");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mx-auto flex h-full max-w-6xl gap-4">
      <aside className="w-72 shrink-0 overflow-y-auto" data-testid="admin-wa-threads-list">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <MessageCircle className="h-5 w-5" /> Threads
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loadingThreads ? (
              <div className="grid place-items-center py-8 text-[color:var(--fulkro-muted)]">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : threads.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-[color:var(--fulkro-muted)]">
                Sin threads activos.
              </p>
            ) : (
              <ul>
                {threads.map((t) => (
                  <li key={t.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(t.id)}
                      className={`block w-full border-b border-fulkro-surface-glass-border px-4 py-3 text-left text-sm hover:bg-fulkro-surface-glass-strong ${
                        selectedId === t.id ? "bg-fulkro-surface-glass-strong" : ""
                      }`}
                    >
                      <div className="font-bold text-[color:var(--fulkro-title)]">
                        {t.client_user_id?.slice(0, 8) ?? "—"}…
                      </div>
                      <div className="mt-0.5 truncate text-xs text-[color:var(--fulkro-muted)]">
                        {t.last_message_preview ?? "(sin mensajes)"}
                      </div>
                      <div className="mt-0.5 text-[11px] text-[color:var(--fulkro-muted)]">
                        in: {formatTs(t.last_inbound_at)} · out: {formatTs(t.last_outbound_at)}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <Card className="flex flex-1 flex-col">
          <CardHeader>
            <CardTitle className="text-base">
              {selectedId
                ? `Thread · ${selectedId.slice(0, 8)}…`
                : "Selecciona un thread"}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col p-0">
            <div className="flex-1 overflow-y-auto">
              {selectedId ? (
                <WhatsAppThreadView messages={messages} loading={loadingMsgs} />
              ) : (
                <p className="py-12 text-center text-sm text-[color:var(--fulkro-muted)]">
                  Selecciona un thread a la izquierda.
                </p>
              )}
            </div>
            {selectedId && (
              <form
                onSubmit={onSend}
                className="border-t border-fulkro-surface-glass-border p-3"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    placeholder="Escribe respuesta…"
                    disabled={sending}
                    className="flex-1 rounded-md border px-3 py-2 text-sm"
                    data-testid="admin-wa-reply-input"
                  />
                  <Button
                    type="submit"
                    variant="primary"
                    size="md"
                    disabled={sending || !reply.trim()}
                  >
                    {sending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
