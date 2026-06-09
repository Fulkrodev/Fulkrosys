/**
 * AdminMessageThread — vista detalle thread admin (sub-bloque 6.B.2).
 *
 * - Mensajes cronológico ASC con SafeMarkdown body
 * - Attachments preview + download admin (presigned GET URL)
 * - Botones admin: mark-read all + delete moderation
 * - mark-read on view (effect dispara markAsRead mensajes cliente
 *   no leídos al montar)
 * - AdminMessageComposer reply inline al final
 */
"use client";

import { Download, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

import {
  deleteAdminMessage,
  getAdminAttachmentDownload,
  getThreadAdmin,
  markAdminAsRead,
} from "@/lib/admin-messages/api";
import type {
  AttachmentOut,
  MessageOut,
} from "@/lib/admin-messages/schemas";
import {
  formatFileSize,
  mimeIcon,
} from "@/lib/client-messages/attachments";
import { SafeMarkdown } from "@/lib/client-messages/markdown";

import { AdminMessageComposer } from "./AdminMessageComposer";

interface AdminMessageThreadProps {
  threadId: string;
  onChanged: () => void;
}

export function AdminMessageThread({
  threadId,
  onChanged,
}: AdminMessageThreadProps) {
  const [messages, setMessages] = useState<MessageOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      const data = await getThreadAdmin(threadId);
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

  // Mark-read on view: mensajes cliente no leídos por admin → marca read
  useEffect(() => {
    if (!messages) return;
    const unreadFromClient = messages.filter(
      (m) => m.from_role === "client" && !m.is_read_by_admin,
    );
    if (unreadFromClient.length === 0) return;
    void Promise.all(
      unreadFromClient.map((m) => markAdminAsRead(m.id)),
    ).catch(() => {
      /* silent: best-effort */
    });
  }, [messages]);

  async function downloadAttachment(messageId: string, att: AttachmentOut) {
    try {
      const out = await getAdminAttachmentDownload(messageId, att.id);
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

  async function handleDelete(messageId: string) {
    if (
      !window.confirm(
        "¿Borrar este mensaje? Acción de moderación, no se puede deshacer.",
      )
    ) {
      return;
    }
    try {
      await deleteAdminMessage(messageId);
      toast.success("Mensaje eliminado.");
      void refresh();
      onChanged();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error eliminando.";
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
          <p className="text-base font-medium text-[color:var(--fulkro-muted)]">Thread vacío.</p>
        ) : (
          messages.map((m) => {
            const isAdmin = m.from_role === "admin";
            const senderLabel = isAdmin ? "Marcos" : "Cliente";
            return (
              <article
                key={m.id}
                className={`rounded-md border p-3 ${
                  isAdmin
                    ? "border-fulkro-primary-200 bg-fulkro-primary-50"
                    : "border-fulkro-ink-200 bg-white"
                }`}
              >
                <header className="mb-2 flex items-center justify-between gap-2 text-sm font-medium text-[color:var(--fulkro-muted)]">
                  <span className="font-medium">{senderLabel}</span>
                  <div className="flex items-center gap-2">
                    <time dateTime={m.created_at}>
                      {new Date(m.created_at).toLocaleString("es-ES")}
                    </time>
                    <button
                      type="button"
                      onClick={() => handleDelete(m.id)}
                      aria-label="Borrar mensaje (moderación)"
                      className="text-fulkro-ink-600 hover:text-red-600"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
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
                          <span className="text-sm font-medium text-[color:var(--fulkro-muted)]">
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
        <AdminMessageComposer
          mode="reply"
          threadId={threadId}
          onSent={() => {
            void refresh();
            onChanged();
          }}
        />
      </div>
    </div>
  );
}
