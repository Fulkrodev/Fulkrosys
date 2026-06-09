"use client";

/**
 * ReconciliationManualPanel · admin marca pagos manualmente (MB-18.5 ADR-040).
 *
 * Workflow Marcos:
 * 1. Ver listado pending payments
 * 2. Cuando ve transferencia en extracto banco · click "Marcar pagado"
 * 3. Dialog · introducir payment_reference + payment_notes
 * 4. Confirmar · workflow advances next phase si blocking
 */
import {
  CheckCircle2,
  Clock,
  Inbox,
  RefreshCw,
} from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

import type {
  MarkPaidResponse,
  PendingPaymentRow,
} from "@/lib/billing/schemas";

interface ReconciliationManualPanelProps {
  rows: PendingPaymentRow[];
  loading: boolean;
  onMarkPaid: (
    milestoneId: string,
    reference: string,
    notes: string,
  ) => Promise<MarkPaidResponse>;
  onRefresh: () => void;
}

export function ReconciliationManualPanel({
  rows,
  loading,
  onMarkPaid,
  onRefresh,
}: ReconciliationManualPanelProps) {
  return (
    <Card data-testid="reconciliation-panel">
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-fulkro-warning-700" />
              Pagos pendientes
              <Badge variant="warning">{rows.length}</Badge>
            </CardTitle>
            <CardDescription>
              Cuando veas la transferencia en el extracto, márcala como
              pagada para desbloquear la siguiente fase del proyecto.
            </CardDescription>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onRefresh}
            data-testid="btn-refresh-pending"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Recargar
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p
            className="text-sm text-fulkro-ink-500"
            data-testid="pending-loading"
          >
            Cargando pagos pendientes...
          </p>
        ) : rows.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center gap-2 py-8 text-center"
            data-testid="pending-empty"
          >
            <Inbox className="h-10 w-10 text-fulkro-ink-300" />
            <p className="text-sm text-fulkro-ink-500">
              Sin pagos pendientes · todo al día.
            </p>
          </div>
        ) : (
          <div className="space-y-3" data-testid="pending-list">
            {rows.map((row) => (
              <PendingRow
                key={row.milestone_id}
                row={row}
                onMarkPaid={onMarkPaid}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface PendingRowProps {
  row: PendingPaymentRow;
  onMarkPaid: ReconciliationManualPanelProps["onMarkPaid"];
}

function PendingRow({ row, onMarkPaid }: PendingRowProps) {
  const [open, setOpen] = useState(false);
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  async function confirm() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await onMarkPaid(row.milestone_id, reference, notes);
      const target = res.workflow_advanced_to_phase;
      setFeedback(
        target !== null
          ? `Pago confirmado · siguiente fase desbloqueada (fase ${target}).`
          : "Pago confirmado.",
      );
      setOpen(false);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No se pudo marcar como pagado",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const ageVariant: "warning" | "danger" | "info" =
    row.days_pending > 30 ? "danger" : row.days_pending > 7 ? "warning" : "info";

  return (
    <div
      className="rounded-md border border-fulkro-ink-100 p-3"
      data-testid={`pending-row-${row.milestone_id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-fulkro-ink-900">
            {row.project_name}
          </p>
          <p className="text-sm text-fulkro-ink-500">
            {row.milestone_name}
            {row.invoice_number ? ` · ${row.invoice_number}` : ""}
          </p>
          <div className="mt-2 flex items-center gap-2">
            <span className="font-semibold">{row.amount_eur} €</span>
            <Badge variant={ageVariant}>
              Pendiente {row.days_pending} días
            </Badge>
          </div>
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button
              type="button"
              size="sm"
              data-testid={`btn-mark-paid-${row.milestone_id}`}
            >
              <CheckCircle2 className="mr-2 h-4 w-4" />
              Marcar pagado
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirmar pago recibido</DialogTitle>
              <DialogDescription>
                {row.project_name} · {row.amount_eur} €
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor={`reference-${row.milestone_id}`}>
                  Referencia transferencia (opcional)
                </Label>
                <Input
                  id={`reference-${row.milestone_id}`}
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  placeholder="Ej: ID transferencia banco"
                  data-testid={`input-reference-${row.milestone_id}`}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor={`notes-${row.milestone_id}`}>
                  Notas (opcional)
                </Label>
                <Textarea
                  id={`notes-${row.milestone_id}`}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Cualquier detalle relevante"
                  data-testid={`input-notes-${row.milestone_id}`}
                />
              </div>
              {error ? (
                <p
                  className="text-sm text-fulkro-danger-700"
                  data-testid={`error-${row.milestone_id}`}
                >
                  {error}
                </p>
              ) : null}
            </div>
            <DialogFooter>
              <Button
                type="button"
                onClick={confirm}
                disabled={submitting}
                data-testid={`btn-confirm-${row.milestone_id}`}
              >
                {submitting
                  ? "Confirmando..."
                  : "Confirmar pago + desbloquear fase"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      {feedback ? (
        <p
          className="mt-2 text-sm text-fulkro-success-700"
          data-testid={`feedback-${row.milestone_id}`}
        >
          {feedback}
        </p>
      ) : null}
    </div>
  );
}
