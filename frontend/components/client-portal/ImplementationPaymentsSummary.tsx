"use client";

/**
 * #45 · Resumen amable "Hitos y pagos" para el portal cliente (R29).
 *
 * Cruza el avance del proyecto con el estado de cobro de cada hito y lo presenta
 * de forma factual y sin presión: qué está pagado, qué queda y la fecha prevista
 * del próximo pago. R29: sin jerga interna, sin rojo coercitivo · tono "ve tu
 * proyecto avanzar". Cliente READ-ONLY (ADR-014): solo consulta, no opera.
 *
 * Consume GET /api/v1/portal/billing/implementation-payments.
 */
import * as React from "react";
import { Wallet } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getMyImplementationPayments } from "@/lib/billing/api";
import type {
  ClientImplementationHito,
  PaymentState,
} from "@/lib/billing/schemas";

const CLIENT_PAYMENTS_QUERY_KEY = [
  "client-portal",
  "implementation-payments",
] as const;

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

// R29: sin variante danger (nada de rojo coercitivo en el portal cliente).
function estadoBadge(state: PaymentState, label: string) {
  const variant: "success" | "warning" | "secondary" =
    state === "paid" ? "success" : state === "due" ? "warning" : "secondary";
  return <Badge variant={variant}>{label}</Badge>;
}

export function ImplementationPaymentsSummary() {
  const query = useQuery({
    queryKey: CLIENT_PAYMENTS_QUERY_KEY as unknown as string[],
    queryFn: getMyImplementationPayments,
    staleTime: 60_000,
  });

  if (query.isLoading) {
    return (
      <Skeleton
        className="h-40 w-full"
        data-testid="cliente-impl-payments-loading"
      />
    );
  }

  // Sin contrato/hitos todavía o error → no estorbar (el plan ya se muestra).
  if (query.isError || !query.data || query.data.hitos.length === 0) {
    return null;
  }

  const data = query.data;

  return (
    <Card data-testid="cliente-impl-payments">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Wallet className="size-5" />
          Hitos y pagos
        </CardTitle>
        <CardDescription className="text-xs">
          Cómo se reparte la inversión a lo largo de tu proyecto. Sin prisa por tu
          parte · cada hito se factura cuando avanzamos su fase.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Metric label="Total" value={fmtEuro(data.total_eur)} />
          <Metric label="Pagado" value={fmtEuro(data.pagado_eur)} />
          <Metric label="Pendiente" value={fmtEuro(data.pendiente_eur)} />
        </div>
        {data.proximo_pago_previsto ? (
          <p className="text-xs text-fulkro-ink-500">
            Próximo pago previsto:{" "}
            <span className="font-medium">
              {fmtDate(data.proximo_pago_previsto)}
            </span>
          </p>
        ) : null}

        <ul className="divide-y" data-testid="cliente-impl-payments-list">
          {data.hitos.map((h: ClientImplementationHito, i: number) => (
            <li
              key={`${h.fase}-${i}`}
              className="flex items-center justify-between gap-3 py-2"
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-fulkro-ink-700">
                  {h.concepto}
                </div>
                <div className="text-xs text-fulkro-ink-500">
                  {h.fase}
                  {h.fecha_prevista
                    ? ` · prevista ${fmtDate(h.fecha_prevista)}`
                    : ""}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <span className="text-sm tabular-nums text-fulkro-ink-600">
                  {fmtEuro(h.importe_eur)}
                </span>
                {estadoBadge(h.payment_state, h.estado)}
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-white p-3">
      <div className="text-xs uppercase tracking-wide text-fulkro-ink-400">
        {label}
      </div>
      <div className="text-lg font-bold tabular-nums text-fulkro-ink-700">
        {value}
      </div>
    </div>
  );
}
