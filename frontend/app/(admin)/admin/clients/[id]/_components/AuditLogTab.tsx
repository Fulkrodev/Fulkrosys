"use client";

import { useEffect, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";

import { ApiError } from "@/lib/api";
import { getClientAuditLog } from "@/lib/admin-clients/api";
import type {
  AuditLogEntry,
  AuditLogPage,
} from "@/lib/admin-clients/schemas";

const PAGE_SIZE = 25;

export function AuditLogTab({ clientId }: { clientId: string }) {
  const [data, setData] = useState<AuditLogPage | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getClientAuditLog(clientId, page, PAGE_SIZE)
      .then(setData)
      .catch((err) => {
        setError(
          err instanceof ApiError
            ? `Error ${err.status}: ${err.message}`
            : "Error al cargar audit log",
        );
      })
      .finally(() => setLoading(false));
  }, [clientId, page]);

  const columns: ColumnDef<AuditLogEntry>[] = [
    {
      accessorKey: "timestamp",
      header: "Fecha",
      cell: ({ row }) =>
        new Date(row.original.timestamp).toLocaleString("es-ES"),
    },
    {
      accessorKey: "tabla",
      header: "Tabla",
      cell: ({ row }) => (
        <Badge variant="outline">{row.original.tabla}</Badge>
      ),
    },
    {
      accessorKey: "accion",
      header: "Acción",
      cell: ({ row }) => (
        <Badge variant="secondary">{row.original.accion}</Badge>
      ),
    },
    {
      accessorKey: "usuario",
      header: "Usuario",
      cell: ({ row }) =>
        row.original.usuario ? (
          row.original.usuario
        ) : (
          <span className="text-fulkro-ink-500 italic">— pre-wiring —</span>
        ),
    },
    {
      accessorKey: "hash_current",
      header: "Hash",
      cell: ({ row }) =>
        row.original.hash_current ? (
          <span className="font-mono text-sm font-medium text-[color:var(--fulkro-muted)]">
            {row.original.hash_current.substring(0, 8)}…
          </span>
        ) : (
          "—"
        ),
    },
  ];

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Audit log (inmutable, hash chain ENS)</CardTitle>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 rounded border border-fulkro-danger/40 bg-fulkro-danger/10 p-3 text-sm text-fulkro-danger">
            {error}
          </div>
        )}
        <DataTable
          columns={columns}
          data={data?.items ?? []}
          loading={loading}
          pageSize={PAGE_SIZE}
        />
        {data && totalPages > 1 && (
          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-fulkro-ink-500">
              Página {page} de {totalPages} · {data.total} total
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setPage((p) => Math.min(totalPages, p + 1))
                }
                disabled={page >= totalPages}
              >
                Siguiente
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
