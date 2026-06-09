"use client";

/**
 * RemediationProposeButton · admin polish Bloque 3+5 v3.12.
 *
 * Botón "Proponer al cliente" per CloudGap row · admin UI cloud-connectors.
 * Solo visible cuando approval_status === 'detected'.
 *
 * Click → confirmation Dialog con preview:
 *   - Title gap + suggested_action
 *   - Severity + ENS measure code
 *   - Notas opcionales para Marcos justificar
 *
 * Submit → POST /api/v1/admin/projects/{pid}/cloud-gaps/{gid}/propose-to-cliente
 * Success → close + invalidate queries.
 */
import { useState } from "react";
import { Send } from "lucide-react";

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
import { useProposeToCliente } from "@/hooks/useAdminCloudRemediations";

interface RemediationProposeButtonProps {
  projectId: string;
  gapId: string;
  gapTitle: string;
  gapSeverity: string;
  gapMeasureCode: string;
  suggestedAction: string | null;
  approvalStatus: string;
}

export function RemediationProposeButton({
  projectId,
  gapId,
  gapTitle,
  gapSeverity,
  gapMeasureCode,
  suggestedAction,
  approvalStatus,
}: RemediationProposeButtonProps) {
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const mutation = useProposeToCliente(projectId);

  // Solo render si gap está en estado 'detected' (ready propose)
  if (approvalStatus !== "detected") {
    return null;
  }

  const handleSubmit = async () => {
    try {
      await mutation.mutateAsync({
        gapId,
        notes: notes.trim() || undefined,
      });
      setOpen(false);
      setNotes("");
    } catch {
      // Error displayed inline via mutation.isError
    }
  };

  return (
    <>
      <Button
        size="sm"
        variant="outline"
        onClick={() => setOpen(true)}
        data-testid="propose-to-cliente-button"
      >
        <Send className="h-4 w-4 mr-1" />
        Proponer al cliente
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          className="max-w-lg"
          data-testid="propose-modal"
        >
          <DialogHeader>
            <DialogTitle>Proponer al cliente</DialogTitle>
            <DialogDescription>
              Cliente recibirá notificación en su portal · decidirá aprobar o
              rechazar.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Gap
              </Label>
              <p className="text-sm font-medium mt-1">{gapTitle}</p>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant="outline" className="text-xs">
                  {gapMeasureCode}
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  {gapSeverity}
                </Badge>
              </div>
            </div>

            {suggestedAction && (
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Acción sugerida
                </Label>
                <p className="text-sm mt-1 whitespace-pre-line">
                  {suggestedAction}
                </p>
              </div>
            )}

            <div>
              <Label
                htmlFor="propose-notes"
                className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
              >
                Notas para audit trail (opcional)
              </Label>
              <Textarea
                id="propose-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Justificación · urgencia · etc"
                rows={3}
                maxLength={2000}
                disabled={mutation.isPending}
                data-testid="propose-notes"
              />
            </div>

            {mutation.isError && (
              <Alert variant="danger">
                <AlertDescription>
                  {mutation.error instanceof Error
                    ? mutation.error.message
                    : "Error desconocido"}
                </AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={mutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={mutation.isPending}
              data-testid="propose-submit-button"
            >
              <Send className="h-4 w-4 mr-1" />
              {mutation.isPending ? "Enviando..." : "Enviar al cliente"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
