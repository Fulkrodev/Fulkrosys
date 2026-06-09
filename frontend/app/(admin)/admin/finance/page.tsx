"use client";

/**
 * /admin/finance · dashboard finanzas + reconciliación manual
 * (MB-18.5 ADR-040).
 *
 * Marcos workflow:
 * 1. Ver KPIs cards · billed/paid month + pending + overdue
 * 2. ReconciliationManualPanel listado pending payments
 * 3. Click "Marcar pagado" tras ver transferencia en extracto banco
 */
import { Banknote } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { FinanceKpis } from "@/components/admin/finance/FinanceKpis";
import { ReconciliationManualPanel } from "@/components/admin/finance/ReconciliationManualPanel";
import {
  getFinanceKpisAdmin,
  listPendingPaymentsAdmin,
  markMilestonePaidAdmin,
} from "@/lib/billing/api";
import type {
  FinanceKpis as KpisData,
  PendingPaymentRow,
} from "@/lib/billing/schemas";

export default function AdminFinancePage() {
  const [kpis, setKpis] = useState<KpisData | null>(null);
  const [pending, setPending] = useState<PendingPaymentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const [kpisRes, pendingRes] = await Promise.all([
        getFinanceKpisAdmin(),
        listPendingPaymentsAdmin(),
      ]);
      setKpis(kpisRes);
      setPending(pendingRes);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No se pudieron cargar los datos de finanzas",
      );
    } finally {
      if (showLoading) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll(true);
  }, [fetchAll]);

  return (
    <div className="container py-8 space-y-6">
      <div className="flex items-center gap-3">
        <Banknote className="h-6 w-6 text-fulkro-primary-500" />
        <div>
          <h1 className="text-2xl font-semibold text-fulkro-ink-900">
            Finanzas
          </h1>
          <p className="text-sm text-fulkro-ink-500">
            Dashboard ingresos · pagos pendientes · reconciliación manual.
          </p>
        </div>
      </div>

      {error ? (
        <div
          role="alert"
          className="rounded-md bg-fulkro-danger-50 px-3 py-2 text-sm text-fulkro-danger-700"
          data-testid="finance-load-error"
        >
          {error}
        </div>
      ) : null}

      <FinanceKpis kpis={kpis} loading={loading} />

      <ReconciliationManualPanel
        rows={pending}
        loading={loading}
        onRefresh={() => fetchAll(true)}
        onMarkPaid={async (milestoneId, reference, notes) => {
          const res = await markMilestonePaidAdmin(milestoneId, {
            payment_reference: reference || undefined,
            payment_notes: notes || undefined,
          });
          // Refresh in background sin unmount listado (preserva
          // feedback row local).
          void fetchAll(false);
          return res;
        }}
      />
    </div>
  );
}
