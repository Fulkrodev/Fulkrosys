"use client";

/**
 * PostMeetingActions — 4 botones cross-motor post-completion
 * (sub-bloque 7.B.7 FASE 7).
 *
 * Visible solo si meeting.status === 'completed'.
 *
 * 4 acciones (handlers en backend/app/motors/m_meetings/actions.py):
 *   1. propuesta → A19 RedactorPropuestasAgent → P-001 DOCX draft
 *   2. create_project → ORM Project insert + linkea meeting.project_id
 *   3. k6_signature → M12 magic link FIRMA_DOCUMENTO
 *   4. email_summary → EmailSender consolidado con render meeting
 *
 * Payload UX:
 *   - propuesta: sin payload (defaults A19)
 *   - create_project: form con nombre + categoria_objetivo + fase
 *   - k6_signature: signatory_contact_id picker (M30) + recipient_email opt
 *   - email_summary: to_email opt + extra_message opt
 */
import { FileText, FolderPlus, Mail, PenTool } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type {
  MeetingDetail,
  MeetingPostActionRequest,
  MeetingPostActionResponse,
  PostActionType,
} from "@/lib/admin-meetings/schemas";

import { ContactQuickPicker } from "@/app/(admin)/admin/clients/[id]/_components/contacts/ContactQuickPicker";

interface PostMeetingActionsProps {
  meeting: MeetingDetail;
  onAction: (
    payload: MeetingPostActionRequest,
  ) => Promise<MeetingPostActionResponse>;
}

type DialogMode = "create_project" | "k6_signature" | "email_summary" | null;

export function PostMeetingActions({
  meeting,
  onAction,
}: PostMeetingActionsProps) {
  const [busy, setBusy] = React.useState<PostActionType | null>(null);
  const [dialogMode, setDialogMode] = React.useState<DialogMode>(null);

  // Form state per dialog
  const [projectName, setProjectName] = React.useState(meeting.title || "");
  const [projectCategoria, setProjectCategoria] = React.useState("");
  const [projectFase, setProjectFase] = React.useState("");

  const [signatoryContactId, setSignatoryContactId] = React.useState<
    string | null
  >(meeting.interlocutor_contact_id ?? null);
  const [signatoryEmail, setSignatoryEmail] = React.useState("");

  const [emailTo, setEmailTo] = React.useState("");
  const [emailExtraMessage, setEmailExtraMessage] = React.useState("");

  function closeDialog() {
    setDialogMode(null);
  }

  async function executeAction(
    actionType: PostActionType,
    payload: Record<string, unknown> = {},
  ) {
    setBusy(actionType);
    try {
      const response = await onAction({ action_type: actionType, payload });
      if (response.success) {
        const summary = describeSuccess(actionType, response);
        toast.success(summary);
        closeDialog();
      } else {
        toast.error(response.error_message || "Acción fallida.");
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error invocando acción.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rounded-md border border-fulkro-primary-200 bg-fulkro-primary-50 p-4">
      <h3 className="text-sm font-semibold text-fulkro-primary-700">
        Acciones post-reunión
      </h3>
      <p className="mb-3 text-xs text-fulkro-ink-500">
        4 acciones cross-motor disponibles tras completar reunión.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          onClick={() => executeAction("propuesta")}
          disabled={busy !== null || !meeting.project_id}
          title={
            !meeting.project_id
              ? "Requiere proyecto asignado (Crear proyecto primero)"
              : undefined
          }
        >
          <FileText size={14} className="mr-1" />
          Generar P-001 (A19)
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => setDialogMode("create_project")}
          disabled={busy !== null || !!meeting.project_id}
          title={
            meeting.project_id
              ? "Reunión ya tiene proyecto asignado"
              : undefined
          }
        >
          <FolderPlus size={14} className="mr-1" />
          Crear proyecto
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => setDialogMode("k6_signature")}
          disabled={busy !== null || !meeting.project_id}
          title={
            !meeting.project_id
              ? "Requiere proyecto asignado"
              : undefined
          }
        >
          <PenTool size={14} className="mr-1" />
          Enviar firma K.6
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => setDialogMode("email_summary")}
          disabled={busy !== null}
        >
          <Mail size={14} className="mr-1" />
          Email resumen
        </Button>
      </div>

      {meeting.proposal_generated_id && (
        <p className="mt-3 text-xs text-fulkro-ink-500">
          Propuesta generada:{" "}
          <span className="font-mono">{meeting.proposal_generated_id}</span>
        </p>
      )}

      {/* Dialog create_project */}
      <Dialog
        open={dialogMode === "create_project"}
        onOpenChange={(o) => !o && closeDialog()}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Crear proyecto desde reunión</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label htmlFor="proj-name">Nombre proyecto</Label>
              <Input
                id="proj-name"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                maxLength={255}
              />
            </div>
            <div>
              <Label htmlFor="proj-categoria">Categoría objetivo</Label>
              <select
                id="proj-categoria"
                value={projectCategoria}
                onChange={(e) => setProjectCategoria(e.target.value)}
                className="mt-1 w-full rounded-md border border-fulkro-ink-300 px-2 py-1.5 text-sm"
              >
                <option value="">— elegir —</option>
                <option value="BASICA">BÁSICA</option>
                <option value="MEDIA">MEDIA</option>
                <option value="ALTA">ALTA</option>
              </select>
            </div>
            <div>
              <Label htmlFor="proj-fase">Fase inicial (opcional)</Label>
              <Input
                id="proj-fase"
                value={projectFase}
                onChange={(e) => setProjectFase(e.target.value)}
                placeholder="kickoff"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog}>
              Cancelar
            </Button>
            <Button
              onClick={() =>
                executeAction("create_project", {
                  nombre: projectName.trim() || meeting.title,
                  categoria_objetivo: projectCategoria || undefined,
                  fase: projectFase.trim() || undefined,
                })
              }
              disabled={!projectName.trim() || busy !== null}
            >
              Crear proyecto
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog k6_signature */}
      <Dialog
        open={dialogMode === "k6_signature"}
        onOpenChange={(o) => !o && closeDialog()}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Generar magic link FIRMA_DOCUMENTO K.6</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Contacto firmante (M30)</Label>
              <ContactQuickPicker
                clientId={meeting.client_id}
                value={signatoryContactId}
                onChange={setSignatoryContactId}
                filterBySignatory
                placeholder="Selecciona contacto firmante…"
              />
            </div>
            <div>
              <Label htmlFor="sig-email">
                Email destinatario (opcional, override contacto)
              </Label>
              <Input
                id="sig-email"
                type="email"
                value={signatoryEmail}
                onChange={(e) => setSignatoryEmail(e.target.value)}
                placeholder="firmante@cliente.com"
              />
            </div>
            <p className="text-xs text-fulkro-ink-500">
              Si no especificas email explícito, se usará el del contacto
              M30 seleccionado.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog}>
              Cancelar
            </Button>
            <Button
              onClick={() =>
                executeAction("k6_signature", {
                  signatory_contact_id: signatoryContactId ?? undefined,
                  recipient_email: signatoryEmail.trim() || undefined,
                })
              }
              disabled={
                (!signatoryContactId && !signatoryEmail.trim()) || busy !== null
              }
            >
              Generar magic link
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog email_summary */}
      <Dialog
        open={dialogMode === "email_summary"}
        onOpenChange={(o) => !o && closeDialog()}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Email resumen de reunión</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label htmlFor="email-to">Destinatario (opcional)</Label>
              <Input
                id="email-to"
                type="email"
                value={emailTo}
                onChange={(e) => setEmailTo(e.target.value)}
                placeholder={
                  meeting.interlocutor?.email ?? "destinatario@cliente.com"
                }
              />
              <p className="mt-1 text-xs text-fulkro-ink-500">
                Por defecto se usa el email del interlocutor M30 si presente.
              </p>
            </div>
            <div>
              <Label htmlFor="email-msg">
                Mensaje extra del admin (opcional)
              </Label>
              <Textarea
                id="email-msg"
                value={emailExtraMessage}
                onChange={(e) => setEmailExtraMessage(e.target.value)}
                rows={3}
                placeholder="Gracias por la sesión, adjunto resumen…"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog}>
              Cancelar
            </Button>
            <Button
              onClick={() =>
                executeAction("email_summary", {
                  to_email: emailTo.trim() || undefined,
                  extra_message: emailExtraMessage.trim() || undefined,
                })
              }
              disabled={busy !== null}
            >
              Enviar email
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function describeSuccess(
  type: PostActionType,
  response: MeetingPostActionResponse,
): string {
  const result = response.result ?? {};
  if (type === "propuesta") {
    const proposalId = result.proposal_id;
    return proposalId
      ? `Propuesta P-001 generada (${proposalId}).`
      : "Propuesta P-001 generada.";
  }
  if (type === "create_project") {
    const projectId = result.project_id;
    return projectId
      ? `Proyecto creado (${projectId}) y vinculado a la reunión.`
      : "Proyecto creado.";
  }
  if (type === "k6_signature") {
    const url = result.url;
    if (typeof url === "string") {
      // Copy to clipboard best-effort
      if (navigator.clipboard) {
        void navigator.clipboard.writeText(url).catch(() => {});
      }
      return "Magic link generado y copiado al portapapeles.";
    }
    return "Magic link generado.";
  }
  if (type === "email_summary") {
    const to = result.to;
    return typeof to === "string" ? `Email enviado a ${to}.` : "Email enviado.";
  }
  return "Acción ejecutada.";
}
