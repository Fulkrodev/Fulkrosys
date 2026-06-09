"use client";

/**
 * BillingHistory cliente · listado invoices propios + IBAN info-mode
 * (MB-18.5 ADR-040 cliente billing).
 *
 * Directiva Marcos cross-reference WhatsApp MB-16:
 * - IBAN como texto plano formateado <strong> · NO botón "Copiar IBAN"
 * - NO clipboard.writeText · NO onclick · NO target_blank
 * - Cliente selecciona y copia manualmente (cero automatización pushy)
 */
import { Download, Receipt } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import type { ClientInvoiceRow } from "@/lib/billing/schemas";

interface BillingHistoryProps {
  invoices: ClientInvoiceRow[];
  loading: boolean;
}

function statusLabel(status: string | null): string {
  if (!status) return "Pendiente";
  if (status.toLowerCase() === "paid") return "Pagada";
  return "Pendiente";
}

function statusVariant(
  status: string | null,
): "success" | "warning" {
  if (status && status.toLowerCase() === "paid") return "success";
  return "warning";
}

export function BillingHistory({ invoices, loading }: BillingHistoryProps) {
  if (loading) {
    return (
      <p
        className="text-sm text-fulkro-ink-500"
        data-testid="billing-loading"
      >
        Cargando facturas...
      </p>
    );
  }

  if (invoices.length === 0) {
    return (
      <Card data-testid="billing-empty">
        <CardContent className="py-8 text-center">
          <Receipt className="mx-auto h-10 w-10 text-fulkro-ink-300" />
          <p className="mt-2 text-sm text-fulkro-ink-500">
            Aún no hay facturas emitidas para este proyecto.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4" data-testid="billing-list">
      {invoices.map((inv) => (
        <Card
          key={inv.invoice_id}
          data-testid={`invoice-card-${inv.invoice_id}`}
        >
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle className="text-base">
                  {inv.invoice_number ?? "Factura"}
                </CardTitle>
                <p className="text-sm text-fulkro-ink-500 mt-1">
                  {inv.concepto ?? ""}
                </p>
              </div>
              <Badge variant={statusVariant(inv.estado_pago)}>
                {statusLabel(inv.estado_pago)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between gap-3 text-sm">
              <div>
                {inv.fecha_emision ? (
                  <p>
                    <span className="text-fulkro-ink-500">Emitida: </span>
                    {inv.fecha_emision}
                  </p>
                ) : null}
                {inv.fecha_vencimiento ? (
                  <p>
                    <span className="text-fulkro-ink-500">Vencimiento: </span>
                    {inv.fecha_vencimiento}
                  </p>
                ) : null}
              </div>
              {inv.total ? (
                <p
                  className="text-xl font-semibold"
                  data-testid={`invoice-total-${inv.invoice_id}`}
                >
                  {inv.total} €
                </p>
              ) : null}
            </div>

            {inv.bank_instructions_html ? (
              <div
                data-testid={`invoice-bank-${inv.invoice_id}`}
                dangerouslySetInnerHTML={{
                  __html: inv.bank_instructions_html,
                }}
              />
            ) : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
