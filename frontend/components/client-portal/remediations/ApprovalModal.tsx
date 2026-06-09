"use client";

/**
 * ApprovalModal · Cliente UI Bloque 3+5 v3.12.
 *
 * Modal para aprobar/rechazar una propuesta de remediation. R29 firmísimo:
 *   - Lenguaje friendly Spanish · NUNCA presión coercitiva
 *   - Botones approve/reject claros · no juicio si rechazas
 *   - Textarea notas opcional para feedback
 *   - Loading state · error friendly
 *   - Success feedback corto + close
 */
import { useEffect, useState } from "react";
import { CheckCircle2, ShieldCheck, XCircle } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  useApproveRemediation,
  useRejectRemediation,
} from "@/hooks/useClientCloudRemediations";
import {
  REMEDIATION_STATUS_LABELS,
  SEVERITY_LABELS,
  SEVERITY_VARIANTS,
  type RemediationGap,
  type RemediationSeverity,
} from "@/lib/api/client-cloud-remediations";

interface ApprovalModalProps {
  gap: RemediationGap | null;
  open: boolean;
  onClose: () => void;
}

export function ApprovalModal({ gap, open, onClose }: ApprovalModalProps) {
  const [notes, setNotes] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const approveMutation = useApproveRemediation();
  const rejectMutation = useRejectRemediation();

  // Reset state cuando el modal abre/cierra o cambia el gap
  useEffect(() => {
    if (open) {
      setNotes("");
      setFeedback(null);
      approveMutation.reset();
      rejectMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, gap?.id]);

  if (!gap) return null;

  const severity = gap.severity as RemediationSeverity;
  const severityLabel = SEVERITY_LABELS[severity] ?? gap.severity;
  const severityVariant = SEVERITY_VARIANTS[severity] ?? "outline";

  const isPending = approveMutation.isPending || rejectMutation.isPending;

  const handleApprove = async () => {
    try {
      const r = await approveMutation.mutateAsync({
        gapId: gap.id,
        notes: notes.trim() || undefined,
      });
      setFeedback(r.friendly_message ?? "¡Gracias! Marcos comenzará pronto.");
      window.setTimeout(onClose, 1500);
    } catch (e) {
      setFeedback(
        e instanceof Error
          ? e.message
          : "No pudimos guardar tu decisión · prueba de nuevo en un momento.",
      );
    }
  };

  const handleReject = async () => {
    try {
      const r = await rejectMutation.mutateAsync({
        gapId: gap.id,
        notes: notes.trim() || undefined,
      });
      setFeedback(r.friendly_message ?? "Entendido · Marcos lo tendrá en cuenta.");
      window.setTimeout(onClose, 1500);
    } catch (e) {
      setFeedback(
        e instanceof Error
          ? e.message
          : "No pudimos guardar tu decisión · prueba de nuevo en un momento.",
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        className="max-w-xl"
        data-testid="approval-modal"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-amber-600" />
            <span>{gap.title}</span>
          </DialogTitle>
          <DialogDescription>
            Marcos te propone aplicar esta mejora · puedes aprobar o
            rechazar. No hay prisa · si quieres comentamos antes.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <Badge variant={severityVariant}>{severityLabel}</Badge>
            <Badge variant="outline">
              {REMEDIATION_STATUS_LABELS[
                gap.approval_status as keyof typeof REMEDIATION_STATUS_LABELS
              ] ?? gap.approval_status}
            </Badge>
          </div>

          {gap.explanation_es && (
            <div>
              <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Por qué te lo proponemos
              </Label>
              <p
                className="text-sm mt-1 whitespace-pre-line"
                data-testid="modal-explanation"
              >
                {gap.explanation_es}
              </p>
            </div>
          )}

          {gap.suggested_action && (
            <div>
              <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Qué haría Marcos
              </Label>
              <p
                className="text-sm mt-1 whitespace-pre-line"
                data-testid="modal-suggested-action"
              >
                {gap.suggested_action}
              </p>
            </div>
          )}

          <div>
            <Label
              htmlFor="approval-notes"
              className="text-xs font-semibold text-muted-foreground uppercase tracking-wide"
            >
              Comentarios opcionales
            </Label>
            <Textarea
              id="approval-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Si quieres decir algo · escribe aquí"
              rows={3}
              maxLength={1500}
              disabled={isPending}
              data-testid="approval-notes"
            />
          </div>

          {feedback && (
            <Alert
              data-testid="modal-feedback"
              variant={
                approveMutation.isError || rejectMutation.isError
                  ? "danger"
                  : "default"
              }
            >
              <AlertDescription>{feedback}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="flex flex-col-reverse sm:flex-row gap-2">
          <Button
            variant="outline"
            onClick={handleReject}
            disabled={isPending}
            data-testid="reject-button"
          >
            <XCircle className="h-4 w-4 mr-1" />
            Rechazar
          </Button>
          <Button
            onClick={handleApprove}
            disabled={isPending}
            data-testid="approve-button"
          >
            <CheckCircle2 className="h-4 w-4 mr-1" />
            Aprobar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
