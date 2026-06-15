"use client";

/**
 * /client-portal/billing · listado facturas + IBAN info-mode
 * (MB-18.5 ADR-040).
 *
 * IBAN info-mode: texto plano formateado · NO botón "Copiar IBAN" ·
 * cliente selecciona y copia manualmente (directiva Marcos
 * cross-reference WhatsApp MB-16).
 */
import { Receipt, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { BillingHistory } from "@/components/client-portal/BillingHistory";
import { listMyInvoices } from "@/lib/billing/api";
import type { ClientInvoiceRow } from "@/lib/billing/schemas";

export default function ClientBillingPage() {
  const [invoices, setInvoices] = useState<ClientInvoiceRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const loadInvoices = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listMyInvoices()
      .then((items) => {
        if (!cancelled) setInvoices(items);
      })
      .catch(() => {
        if (!cancelled) {
          // R29 firmísimo · friendly Spanish · NO technical leak backend
          setError(
            "Estamos teniendo problemas para mostrar tus facturas. Vuelve a intentarlo · si sigue pasando avisa a Marcos.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return loadInvoices();
  }, [loadInvoices, retryCount]);

  return (
    <div className="mx-auto max-w-4xl py-8 space-y-6">
      <div className="flex items-center gap-3">
        <Receipt className="h-6 w-6 text-fulkro-primary-500" />
        <div>
          <h1 className="text-2xl font-semibold text-fulkro-ink-900">
            Mis facturas
          </h1>
          <p className="text-sm text-fulkro-ink-500">
            Consulta tus facturas y los datos para el pago por
            transferencia bancaria.
          </p>
        </div>
      </div>

      {error ? (
        <div
          role="alert"
          className="rounded-md bg-fulkro-danger-50 px-3 py-3 text-sm text-fulkro-danger-700 flex flex-col gap-2"
          data-testid="billing-load-error"
        >
          <p>{error}</p>
          <button
            type="button"
            onClick={() => setRetryCount((n) => n + 1)}
            disabled={loading}
            className="self-start inline-flex items-center gap-1.5 rounded-md border border-fulkro-danger-300 bg-white px-3 py-1.5 text-sm font-medium text-fulkro-danger-700 hover:bg-fulkro-danger-50 disabled:opacity-50 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-danger-500"
            data-testid="billing-retry"
          >
            <RefreshCw
              size={14}
              className={loading ? "animate-spin" : ""}
            />
            Reintentar
          </button>
        </div>
      ) : null}

      <BillingHistory invoices={invoices} loading={loading} />
    </div>
  );
}
