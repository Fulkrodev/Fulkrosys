"use client";

import { useEffect, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";

import { ApiError } from "@/lib/api";
import { listClientInvoices } from "@/lib/admin-clients/api";
import type { ClientInvoiceAggregated } from "@/lib/admin-clients/schemas";

export function FacturasTab({ clientId }: { clientId: string }) {
  const [invoices, setInvoices] = useState<ClientInvoiceAggregated[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listClientInvoices(clientId)
      .then(setInvoices)
      .catch((err) => {
        setError(
          err instanceof ApiError
            ? `Error ${err.status}: ${err.message}`
            : "Error al cargar facturas",
        );
      })
      .finally(() => setLoading(false));
  }, [clientId]);

  const columns: ColumnDef<ClientInvoiceAggregated>[] = [
    { accessorKey: "numero_correlativo", header: "Nº" },
    {
      accessorKey: "project_name",
      header: "Proyecto",
      cell: ({ row }) =>
        row.original.project_name ?? (
          <span className="text-fulkro-ink-500">—</span>
        ),
    },
    {
      accessorKey: "tipo",
      header: "Tipo",
      cell: ({ row }) => row.original.tipo ?? "—",
    },
    {
      accessorKey: "total",
      header: "Total",
      cell: ({ row }) =>
        row.original.total !== null
          ? row.original.total.toLocaleString("es-ES", {
              style: "currency",
              currency: "EUR",
            })
          : "—",
    },
    {
      accessorKey: "estado_pago",
      header: "Estado",
      cell: ({ row }) =>
        row.original.estado_pago ? (
          <Badge variant="secondary">{row.original.estado_pago}</Badge>
        ) : (
          "—"
        ),
    },
    {
      accessorKey: "fecha_emision",
      header: "Emisión",
      cell: ({ row }) =>
        row.original.fecha_emision
          ? new Date(row.original.fecha_emision).toLocaleDateString("es-ES")
          : "—",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Facturas</CardTitle>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 rounded border border-fulkro-danger/40 bg-fulkro-danger/10 p-3 text-sm text-fulkro-danger">
            {error}
          </div>
        )}
        <DataTable
          columns={columns}
          data={invoices}
          loading={loading}
          pageSize={25}
        />
      </CardContent>
    </Card>
  );
}
