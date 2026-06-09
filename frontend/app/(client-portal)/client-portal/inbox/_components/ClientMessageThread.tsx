/**
 * ClientMessageThread — vista detalle thread cliente (sub-bloque 6.B.1).
 *
 * - Mensajes cronológico ASC con SafeMarkdown body
 * - Attachments chips con download (presigned GET URL)
 * - mark-read on view (effect dispara markAsRead de mensajes admin
 *   no leídos al montar)
 * - MessageComposer reply inline al final
 */
"use client";

import { Download } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

import {
  getAttachmentDownload,
  getThread,
  markAsRead,
} from "@/lib/client-messages/api";
import {
  formatFileSize,
  mimeIcon,
} from "@/lib/client-messages/attachments";
import { SafeMarkdown } from "@/lib/client-messages/markdown";
import type {
  AttachmentOut,
  MessageOut,
} from "@/lib/client-messages/schemas";

import { MessageComposer } from "./MessageComposer";

interface ClientMessageThreadProps {
  threadId: string;
  onSent: () => void;
}

export function ClientMessageThread({
  threadId,
  onSent,
}: ClientMessageThreadProps) {
  const [messages, setMessages] = useState<MessageOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      const data = await getThread(threadId);
      setMessages(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error cargando thread");
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);

  // Mark-read on view: cuando llega data, mark_read los mensajes admin
  // no leídos. Idempotente backend-side.
  useEffect(() => {
    if (!messages) return;
    const unreadFromAdmin = messages.filter(
      (m) => m.from_role === "admin" && !m.is_read_by_client,
    );
    if (unreadFromAdmin.length === 0) return;
    void Promise.all(unreadFromAdmin.map((m) => markAsRead(m.id))).catch(
      () => {
        /* silent: mark-read es best-effort */
      },
    );
  }, [messages]);

  async function downloadAttachment(messageId: string, att: AttachmentOut) {
    try {
      const out = await getAttachmentDownload(messageId, att.id);
      if (out.download_url) {
        window.open(out.download_url, "_blank", "noopener,noreferrer");
      } else {
        toast.error("Adjunto no disponible (upload incompleto).");
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error descargando.";
      toast.error(msg);
    }
  }

  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (messages === null) {
    return (
      <div className="space-y-2">
        {[0, 1].map((i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex-1 space-y-3 overflow-y-auto" aria-label="Mensajes">
        {messages.length === 0 ? (
          <p className="text-sm text-fulkro-ink-500">
            Thread vacío.
          </p>
        ) : (
          messages.map((m) => {
            const isClient = m.from_role === "client";
            const senderLabel = isClient ? "Tú" : "Marcos";
            return (
              <article
                key={m.id}
                className={`rounded-md border p-3 ${
                  isClient
                    ? "border-fulkro-primary-200 bg-fulkro-primary-50"
                    : "border-fulkro-ink-200 bg-white"
                }`}
              >
                <header className="mb-2 flex items-center justify-between text-xs text-fulkro-ink-500">
                  <span className="font-medium">{senderLabel}</span>
                  <time dateTime={m.created_at}>
                    {new Date(m.created_at).toLocaleString("es-ES")}
                  </time>
                </header>
                <SafeMarkdown body={m.body_markdown} />
                {m.attachments.length > 0 && (
                  <ul className="mt-2 flex flex-wrap gap-2" aria-label="Adjuntos">
                    {m.attachments.map((att) => (
                      <li key={att.id}>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => downloadAttachment(m.id, att)}
                          className="gap-1"
                        >
                          <span aria-hidden>{mimeIcon(att.mime_type)}</span>
                          <span className="max-w-40 truncate">
                            {att.filename}
                          </span>
                          <span className="text-xs text-fulkro-ink-500">
                            ({formatFileSize(att.size_bytes)})
                          </span>
                          <Download size={12} />
                        </Button>
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            );
          })
        )}
      </div>

      <div className="border-t border-fulkro-ink-200 pt-3">
        <MessageComposer
          mode="reply"
          threadId={threadId}
          onSent={() => {
            void refresh();
            onSent();
          }}
        />
      </div>
    </div>
  );
}
