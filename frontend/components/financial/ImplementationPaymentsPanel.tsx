"use client";

/**
 * #45 · Panel admin "Hitos y pagos" cruzado con fases del proyecto.
 *
 * Cruza el avance de implementación (projects.fase) con el estado de cobro de
 * cada ContractMilestone: para cada hito muestra su fase, importe, fecha
 * prevista y un estado derivado — pagado / pendiente (fase ya alcanzada) /
 * próximo (fase aún no llega) — más la marca de vencido. Cierra el hueco
 * "qué fase está pagada y cuál queda por cobrar" (Pasada 20 §5).
 *
 * Consume GET /api/v1/admin/finance/projects/{id}/implementation-payments.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import { getImplementationPaymentsAdmin } from "@/lib/billing/api";
import type {
  ImplementationPaymentRow,
  PaymentState,
} from "@/lib/billing/schemas";

function fmtEuro(value: string | null): string {
  if (value === null) return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
  }).format(n);
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-ES");
  } catch {
    return iso;
  }
}

const STATE_LABEL: Record<PaymentState, string> = {
  paid: "Pagado",
  due: "Pendiente",
  upcoming: "Próximo",
};

function stateBadge(row: ImplementationPaymentRow) {
  if (row.is_overdue) {
    return <Badge variant="danger">Vencido</Badge>;
  }
  const variant: "success" | "warning" | "secondary" =
    row.payment_state === "paid"
      ? "success"
      : row.payment_state === "due"
        ? "warning"
        : "secondary";
  return <Badge variant={variant}>{STATE_LABEL[row.payment_state]}</Badge>;
}

export function ImplementationPaymentsPanel({
  projectId,
}: {
  projectId: string;
}) {
  const query = useQuery({
    queryKey: ["implementation-payments", "admin", projectId],
    queryFn: () => getImplementationPaymentsAdmin(projectId),
    enabled: Boolean(projectId),
  });

  if (query.isLoading) {
    return <Skeleton className="h-64" data-testid="impl-payments-loading" />;
  }

  const view = query.data;
  if (!view || !view.found || view.milestones.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Hitos y pagos</CardTitle>
        </CardHeader>
        <CardContent className="py-6 text-center text-sm text-fulkro-ink-500">
          Aún no hay hitos de cobro generados para este proyecto.
        </CardContent>
      </Card>
    );
  }

  const t = view.totals;

  return (
    <Card data-testid="impl-payments-panel">
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle>Hitos y pagos · avance × cobro</CardTitle>
        <Badge variant="info">Fase actual: {view.current_phase_label}</Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Totals label="Total contrato" value={fmtEuro(t.total_eur)} />
          <Totals label="Cobrado" value={fmtEuro(t.paid_eur)} />
          <Totals label="Pendiente" value={fmtEuro(t.pending_eur)} />
          <Totals
            label="Vencidos"
            value={String(t.overdue_count)}
            accent={t.overdue_count > 0 ? "danger" : "default"}
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm" aria-label="Hitos y pagos por fase">
            <thead>
              <tr className="border-b text-left text-xs uppercase tracking-wide text-fulkro-ink-600">
                <th className="py-2 pr-3">Fase</th>
                <th className="py-2 pr-3">Concepto</th>
                <th className="py-2 pr-3 text-right">Importe (IVA inc.)</th>
                <th className="py-2 pr-3">Fecha prevista</th>
                <th className="py-2 pr-3">Estado</th>
              </tr>
            </thead>
            <tbody>
              {view.milestones.map((m) => (
                <tr
                  key={m.milestone_id}
                  className="border-b last:border-0"
                  data-testid="impl-payment-row"
                >
                  <td className="py-2 pr-3">{m.phase_label}</td>
                  <td className="py-2 pr-3 text-fulkro-ink-600">
                    {m.description ?? m.milestone_name}
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">
                    {fmtEuro(m.amount_with_vat_eur)}
                  </td>
                  <td className="py-2 pr-3 tabular-nums">
                    {fmtDate(m.scheduled_date)}
                  </td>
                  <td className="py-2 pr-3">{stateBadge(m)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function Totals({
  label,
  value,
  accent = "default",
}: {
  label: string;
  value: string;
  accent?: "default" | "danger";
}) {
  return (
    <div className="rounded-md border bg-white p-3">
      <div className="text-xs uppercase tracking-wide text-fulkro-ink-600">
        {label}
      </div>
      <div
        className={`text-lg font-bold tabular-nums ${
          accent === "danger" ? "text-fulkro-danger" : "text-fulkro-ink-700"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
