"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { ApiError } from "@/lib/api";
import { suspendClient } from "@/lib/admin-clients/api";

/**
 * Suspend cliente con confirmación type-to-confirm.
 *
 * Plan v4.2 tarea 5.20: confirm modal type-to-confirm. Pattern:
 * usuario debe escribir literal la razón social del cliente para
 * habilitar el botón "Suspender". Defensa contra suspend accidental
 * (clic perdido) — coherente con patterns "type repository name to
 * delete" de GitHub etc.
 *
 * Resume es action directa (no destructive) — no requiere confirm.
 */
export function SuspendDialog({
  clientId,
  clientName,
  onSuspended,
}: {
  clientId: string;
  clientName: string;
  onSuspended: () => Promise<void> | void;
}) {
  const [open, setOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const expected = clientName.trim().toLowerCase();
  const matches = confirmText.trim().toLowerCase() === expected;

  const reset = () => {
    setConfirmText("");
    setSubmitting(false);
  };

  const handleSuspend = async () => {
    setSubmitting(true);
    try {
      await suspendClient(clientId);
      toast.success("Cliente suspendido");
      setOpen(false);
      reset();
      await onSuspended();
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al suspender",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        setOpen(isOpen);
        if (!isOpen) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline">Suspender</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Suspender cliente</DialogTitle>
          <DialogDescription>
            Esta acción ocultará el cliente del listado. Sus datos se
            preservan y puedes reactivarlo más tarde.
            <br />
            <br />
            Para confirmar, escribe la razón social literal:{" "}
            <span className="font-mono font-bold text-[color:var(--fulkro-title)]">
              {clientName}
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label htmlFor="suspend-confirm-input">Razón social</Label>
          <Input
            id="suspend-confirm-input"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder={clientName}
            autoComplete="off"
            spellCheck={false}
          />
          {confirmText && !matches && (
            <p className="text-xs text-fulkro-danger">
              No coincide con la razón social del cliente.
            </p>
          )}
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="ghost" type="button">
              Cancelar
            </Button>
          </DialogClose>
          <Button
            type="button"
            variant="danger"
            disabled={!matches || submitting}
            onClick={() => void handleSuspend()}
          >
            {submitting ? "Suspendiendo..." : "Suspender cliente"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
