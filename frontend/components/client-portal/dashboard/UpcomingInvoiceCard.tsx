"use client";

/**
 * UpcomingInvoiceCard · zone 3 dashboard · optional.
 *
 * Hidden if no upcoming invoice (avoid empty noise).
 */
import Link from "next/link";
import { Receipt } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  invoice: Record<string, unknown> | null;
}

export function UpcomingInvoiceCard({ invoice }: Props) {
  if (!invoice) return null;

  const amount = typeof invoice.amount === "number"
    ? invoice.amount.toFixed(2)
    : null;
  const dueDate = typeof invoice.due_date === "string" ? invoice.due_date : null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Tu próxima factura</CardTitle>
        <Link
          href="/client-portal/billing"
          className="text-sm font-bold text-[color:var(--fulkro-accent)] hover:underline"
        >
          Ver detalle →
        </Link>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4">
          <Receipt className="h-8 w-8 text-[color:var(--fulkro-subtitle)]" />
          <div>
            <p className="text-3xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
              {amount ?? "—"} €
            </p>
            {dueDate && (
              <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                Vencimiento: {dueDate}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
