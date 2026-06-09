"use client";

/**
 * InvoicesList · DataTable facturas M15 (SAN-E v3.MB-3.2).
 *
 * Wired al backend M15 invoices CRUD + AAPP (Verifactu/Facturae/FACE).
 * 7 columnas + DropdownMenu acciones por row.
 */
import * as React from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { ChevronDown, ExternalLink, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Textarea } from "@/components/ui/textarea";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import { useFinancialSummary } from "@/hooks/useFinancialSummary";
import {
  type EstadoPago,
  type Invoice,
  getInvoicePdfUrl,
} from "@/lib/admin-financial/api";

const ESTADO_LABELS: Record<EstadoPago, string> = {
  pendiente: "Pendiente",
  vencida: "Vencida",
  pagada: "Pagada",
  anulada: "Anulada",
};

function EstadoPagoBadge({ estado }: { estado: EstadoPago | null }) {
  if (!estado) return <span className="text-xs text-fulkro-ink-600">—</span>;
  const variant: "success" | "warning" | "danger" | "outline" | "secondary" = (
    {
      pagada: "success",
      pendiente: "warning",
      vencida: "danger",
      anulada: "outline",
    } as const
  )[estado];
  return <Badge variant={variant}>{ESTADO_LABELS[estado]}</Badge>;
}

function VerifactuBadge({ invoice }: { invoice: Invoice }) {
  if (invoice.verifactu_enviado_at) {
    return (
      <Badge variant="success" className="text-[10px]">
        Enviada
      </Badge>
    );
  }
  if (invoice.verifactu_hash) {
    return (
      <Badge variant="info" className="text-[10px]">
        Firmada
      </Badge>
    );
  }
  return <span className="text-xs text-fulkro-ink-600">—</span>;
}

function fmtEuro(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
  }).format(n);
}

function fmtDate(s: string | null): string {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("es-ES");
}

interface CancelDialogState {
  open: boolean;
  invoiceId: string | null;
  numero: string;
  reason: string;
}

export function InvoicesList({ projectId }: { projectId: string }) {
  const fin = useFinancialSummary(projectId);
  const invoices = fin.invoices.data ?? [];

  const [cancelDialog, setCancelDialog] = React.useState<CancelDialogState>({
    open: false,
    invoiceId: null,
    numero: "",
    reason: "",
  });

  const onSend = async (inv: Invoice) => {
    try {
      await fin.send.mutateAsync(inv.id);
      toast.success(`Factura ${inv.numero_correlativo ?? inv.id.slice(0, 8)} enviada`);
    } catch {
      toast.error("Error al enviar factura");
    }
  };

  const onMarkPaid = async (inv: Invoice) => {
    try {
      await fin.markPaid.mutateAsync(inv.id);
      toast.success(`Factura ${inv.numero_correlativo ?? ""} marcada como pagada`);
    } catch {
      toast.error("Error al marcar pagada");
    }
  };

  const onCancelSubmit = async () => {
    if (!cancelDialog.invoiceId) return;
    try {
      await fin.cancel.mutateAsync({
        invoiceId: cancelDialog.invoiceId,
        reason: cancelDialog.reason.trim() || undefined,
      });
      toast.success(`Factura ${cancelDialog.numero} anulada`);
      setCancelDialog({ open: false, invoiceId: null, numero: "", reason: "" });
    } catch {
      toast.error("Error al anular factura");
    }
  };

  const columns: ColumnDef<Invoice>[] = [
    {
      accessorKey: "numero_correlativo",
      header: "Número",
      cell: ({ row }) => (
        <span className="font-mono text-xs">
          {row.original.numero_correlativo ?? row.original.id.slice(0, 8)}
        </span>
      ),
    },
    {
      accessorKey: "fecha_emision",
      header: "Fecha",
      cell: ({ row }) => (
        <span className="text-xs text-fulkro-ink-700">
          {fmtDate(row.original.fecha_emision)}
        </span>
      ),
    },
    {
      accessorKey: "total",
      header: () => <span className="block text-right">Importe</span>,
      cell: ({ row }) => (
        <span className="block text-right font-semibold tabular-nums">
          {fmtEuro(row.original.total)}
        </span>
      ),
    },
    {
      accessorKey: "estado_pago",
      header: "Estado",
      cell: ({ row }) => <EstadoPagoBadge estado={row.original.estado_pago} />,
    },
    {
      id: "verifactu",
      // WCAG nested-interactive: DataTable renderiza el header DENTRO del botón
      // de ordenación · un TooltipENS (botón) anidado ahí crea controles
      // interactivos anidados (mismo fix que AssetsTab discovery).
      header: "Verifactu",
      cell: ({ row }) => <VerifactuBadge invoice={row.original} />,
    },
    {
      id: "pdf",
      header: "PDF",
      cell: ({ row }) =>
        row.original.pdf_path ? (
          <a
            href={getInvoicePdfUrl(projectId, row.original.id)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs font-medium text-fulkro-info hover:underline"
          >
            Ver <ExternalLink size={11} strokeWidth={2.4} />
          </a>
        ) : (
          <span className="text-xs text-fulkro-ink-600">—</span>
        ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        const inv = row.original;
        const canSend = inv.estado_pago !== "anulada";
        const canPay =
          inv.estado_pago === "pendiente" || inv.estado_pago === "vencida";
        const canCancel = inv.estado_pago !== "anulada";
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                Acciones <ChevronDown size={14} strokeWidth={2.4} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {canSend ? (
                <DropdownMenuItem
                  onClick={() => void onSend(inv)}
                  disabled={fin.send.isPending}
                >
                  Reenviar al cliente
                </DropdownMenuItem>
              ) : null}
              {canPay ? (
                <DropdownMenuItem
                  onClick={() => void onMarkPaid(inv)}
                  disabled={fin.markPaid.isPending}
                >
                  Marcar pagada
                </DropdownMenuItem>
              ) : null}
              {canCancel ? (
                <DropdownMenuItem
                  className="text-fulkro-danger"
                  onClick={() =>
                    setCancelDialog({
                      open: true,
                      invoiceId: inv.id,
                      numero: inv.numero_correlativo ?? inv.id.slice(0, 8),
                      reason: "",
                    })
                  }
                >
                  Anular factura
                </DropdownMenuItem>
              ) : null}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  return (
    <>
      <DataTable
        columns={columns}
        data={invoices}
        loading={fin.invoices.isLoading}
        emptyState={
          <div className="flex flex-col items-center gap-1 py-6 text-center">
            <p className="text-sm font-bold text-[color:var(--fulkro-title)]">
              Sin facturas emitidas
            </p>
            <p className="text-xs text-fulkro-ink-500">
              Genera la primera factura desde un hito del contrato.
            </p>
          </div>
        }
      />

      {/* Cancel dialog */}
      <Dialog
        open={cancelDialog.open}
        onOpenChange={(v) => setCancelDialog((s) => ({ ...s, open: v }))}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Anular factura {cancelDialog.numero}</DialogTitle>
            <DialogDescription>
              La factura quedará marcada como anulada · acción auditable. Para
              <TooltipENS term="Verifactu" iconSize={12} /> se registrará evento
              de anulación.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={cancelDialog.reason}
            onChange={(e) =>
              setCancelDialog((s) => ({ ...s, reason: e.target.value }))
            }
            placeholder="Motivo de la anulación (recomendado)"
            rows={3}
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCancelDialog((s) => ({ ...s, open: false }))}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              onClick={onCancelSubmit}
              disabled={fin.cancel.isPending}
            >
              {fin.cancel.isPending ? (
                <Loader2 size={14} className="animate-spin" strokeWidth={2.4} />
              ) : null}
              Confirmar anulación
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
