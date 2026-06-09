/**
 * AdminMessageComposer — admin envía/responde con M30 picker (sub-bloque 6.B.2).
 *
 * Modes:
 *   - "new": clientId Select obligatorio + ContactQuickPicker M30 opcional +
 *     body + attachments
 *   - "reply": solo body + attachments + ContactQuickPicker opcional
 *
 * Cross-motor M29 ↔ M30 (ADR-023): ContactQuickPicker reusable
 * (component pre-anticipado en M30 — comentario fuente menciona M29).
 *
 * Flow attachments 3-step espejo cliente.
 */
"use client";

import { Eye, Paperclip, Send, X } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useClients } from "@/hooks/useClients";

import {
  formatFileSize,
  mimeIcon,
  validateAttachment,
} from "@/lib/client-messages/attachments";
import { SafeMarkdown } from "@/lib/client-messages/markdown";

import {
  completeAdminAttachmentUpload,
  putAdminToPresignedUrl,
  replyAsAdmin,
  requestAdminAttachmentUpload,
  sendAdminMessage,
} from "@/lib/admin-messages/api";

import { ContactQuickPicker } from "../../clients/[id]/_components/contacts/ContactQuickPicker";

interface AdminMessageComposerProps {
  mode: "new" | "reply";
  threadId?: string;
  /** En new mode pre-fills + lock cliente; en reply derived del thread. */
  presetClientId?: string;
  onSent: () => void;
  onCancel?: () => void;
}

interface AttachmentInProgress {
  file: File;
  status: "pending" | "uploading" | "uploaded" | "error";
  attachmentId?: string;
  error?: string;
}

export function AdminMessageComposer({
  mode,
  threadId,
  presetClientId,
  onSent,
  onCancel,
}: AdminMessageComposerProps) {
  const [body, setBody] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const [clientId, setClientId] = useState<string | "">(presetClientId ?? "");
  const [contactId, setContactId] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<AttachmentInProgress[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { data: clients } = useClients();

  function addFiles(files: FileList | null) {
    if (!files) return;
    const newOnes: AttachmentInProgress[] = [];
    for (const f of Array.from(files)) {
      const v = validateAttachment(f);
      if (!v.ok) {
        toast.error(`${f.name}: ${v.error}`);
        continue;
      }
      newOnes.push({ file: f, status: "pending" });
    }
    if (newOnes.length > 0) {
      setAttachments((prev) => [...prev, ...newOnes]);
    }
  }

  function removeAttachment(index: number) {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  }

  async function uploadOne(
    messageId: string,
    item: AttachmentInProgress,
    index: number,
  ): Promise<boolean> {
    setAttachments((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], status: "uploading" };
      return copy;
    });
    try {
      const presigned = await requestAdminAttachmentUpload(messageId, {
        filename: item.file.name,
        mime_type: item.file.type,
        size_bytes: item.file.size,
      });
      await putAdminToPresignedUrl(
        presigned.upload_url,
        item.file,
        presigned.upload_headers,
      );
      await completeAdminAttachmentUpload(messageId, presigned.attachment_id);
      setAttachments((prev) => {
        const copy = [...prev];
        copy[index] = {
          ...copy[index],
          status: "uploaded",
          attachmentId: presigned.attachment_id,
        };
        return copy;
      });
      return true;
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e);
      setAttachments((prev) => {
        const copy = [...prev];
        copy[index] = { ...copy[index], status: "error", error: errMsg };
        return copy;
      });
      toast.error(`Upload ${item.file.name}: ${errMsg}`);
      return false;
    }
  }

  async function handleSubmit() {
    if (body.trim().length === 0) {
      toast.error("Escribe un mensaje antes de enviar.");
      return;
    }
    if (mode === "new" && !clientId) {
      toast.error("Selecciona un cliente destinatario.");
      return;
    }
    if (mode === "reply" && !threadId) {
      toast.error("Thread inválido para responder.");
      return;
    }

    setSubmitting(true);
    try {
      const message =
        mode === "reply" && threadId
          ? await replyAsAdmin(threadId, body, contactId)
          : await sendAdminMessage({
              body_markdown: body,
              client_id: clientId,
              to_contact_id: contactId,
            });

      const uploads = attachments.map((a, i) => uploadOne(message.id, a, i));
      const results = await Promise.all(uploads);
      const failures = results.filter((r) => !r).length;

      if (failures > 0) {
        toast.warning(
          `Mensaje enviado, pero ${failures} adjunto(s) fallaron.`,
        );
      } else {
        toast.success("Mensaje enviado.");
      }
      setBody("");
      setAttachments([]);
      setContactId(null);
      setShowPreview(false);
      onSent();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error enviando mensaje.";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }

  const canPickContact = Boolean(clientId);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          {mode === "new" ? "Nuevo mensaje" : "Responder"}
        </span>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => setShowPreview((p) => !p)}
          aria-pressed={showPreview}
        >
          <Eye size={14} className="mr-1" />
          {showPreview ? "Editar" : "Vista previa"}
        </Button>
      </div>

      {mode === "new" && !presetClientId && (
        <div>
          <label
            htmlFor="composer-client"
            className="block text-xs font-bold text-[color:var(--fulkro-title)]"
          >
            Cliente
          </label>
          <select
            id="composer-client"
            value={clientId}
            onChange={(e) => {
              setClientId(e.target.value);
              setContactId(null);
            }}
            className="mt-1 w-full rounded-md border border-fulkro-ink-300 px-2 py-1.5 text-sm"
            disabled={submitting}
          >
            <option value="">Selecciona cliente…</option>
            {clients?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </div>
      )}

      <div>
        <label className="block text-xs font-bold text-[color:var(--fulkro-title)]">
          Contacto destinatario (opcional, M30)
        </label>
        <div className="mt-1">
          {canPickContact ? (
            <ContactQuickPicker
              clientId={clientId}
              value={contactId}
              onChange={setContactId}
              placeholder="Selecciona contacto del cliente…"
              disabled={submitting}
            />
          ) : (
            <p className="text-xs italic text-fulkro-ink-600">
              Selecciona un cliente primero para elegir contacto.
            </p>
          )}
        </div>
      </div>

      {showPreview ? (
        <div className="min-h-32 rounded-md border border-fulkro-ink-200 bg-white p-3">
          {body.trim() ? (
            <SafeMarkdown body={body} />
          ) : (
            <p className="text-sm text-fulkro-ink-600">
              (vacío — escribe algo en la pestaña Editar)
            </p>
          )}
        </div>
      ) : (
        <Textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Escribe el mensaje en markdown…"
          rows={6}
          className="min-h-32"
          aria-label="Cuerpo del mensaje"
          disabled={submitting}
        />
      )}

      <div
        className="rounded-md border-2 border-dashed border-fulkro-ink-200 p-3"
        onDragOver={(e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = "copy";
        }}
        onDrop={(e) => {
          e.preventDefault();
          addFiles(e.dataTransfer.files);
        }}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-[color:var(--fulkro-muted)]">
            Arrastra archivos aquí o
          </span>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={submitting}
          >
            <Paperclip size={14} className="mr-1" />
            Adjuntar archivo
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => addFiles(e.target.files)}
          />
        </div>
        {attachments.length > 0 && (
          <ul className="mt-3 space-y-1" aria-label="Adjuntos">
            {attachments.map((a, i) => (
              <li
                key={i}
                className="flex items-center justify-between rounded bg-fulkro-ink-50 px-2 py-1 text-xs"
              >
                <span className="truncate">
                  {mimeIcon(a.file.type)} {a.file.name}{" "}
                  <span className="text-fulkro-ink-600">
                    ({formatFileSize(a.file.size)})
                  </span>
                  {a.status === "uploading" && " ⏳"}
                  {a.status === "uploaded" && " ✓"}
                  {a.status === "error" && ` ✗ ${a.error}`}
                </span>
                <button
                  type="button"
                  onClick={() => removeAttachment(i)}
                  aria-label={`Quitar ${a.file.name}`}
                  className="text-fulkro-ink-600 hover:text-fulkro-ink-700"
                  disabled={submitting}
                >
                  <X size={12} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancelar
          </Button>
        )}
        <Button
          type="button"
          onClick={handleSubmit}
          disabled={
            submitting ||
            body.trim().length === 0 ||
            (mode === "new" && !clientId)
          }
        >
          <Send size={14} className="mr-1" />
          {submitting ? "Enviando…" : "Enviar"}
        </Button>
      </div>
    </div>
  );
}
