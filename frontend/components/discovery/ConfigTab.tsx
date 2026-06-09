"use client";

import * as React from "react";
import { CheckCircle2, Settings, XCircle } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import {
  useConfigsSummary,
  useDiscoveryConfigs,
} from "@/hooks/useDiscovery";
import type { DiscoveryConfig } from "@/lib/admin-discovery/api";

export interface ConfigTabProps {
  projectId: string;
}

export function ConfigTab({ projectId }: ConfigTabProps) {
  const { data: configs = [], isLoading } = useDiscoveryConfigs(projectId);
  const { data: summary } = useConfigsSummary(projectId);
  const [detail, setDetail] = React.useState<DiscoveryConfig | null>(null);

  const columns: ColumnDef<DiscoveryConfig>[] = [
    {
      accessorKey: "sistema",
      header: "Sistema",
      cell: ({ row }) => (
        <button
          type="button"
          onClick={() => setDetail(row.original)}
          className="text-left font-medium text-fulkro-primary-700 hover:underline"
        >
          {row.original.sistema}
        </button>
      ),
    },
    {
      accessorKey: "control_id",
      header: () => (
        <span className="inline-flex items-center gap-1">
          Control <TooltipENS term="cis_benchmark" />
        </span>
      ),
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="font-mono text-xs">{row.original.control_id}</span>
          {row.original.control_description ? (
            <span className="text-xs text-fulkro-ink-500">
              {row.original.control_description}
            </span>
          ) : null}
        </div>
      ),
    },
    {
      accessorKey: "estado",
      header: "Estado",
      cell: ({ row }) => {
        const e = row.original.estado;
        if (e === "pass")
          return (
            <Badge variant="success">
              <CheckCircle2 className="mr-1 size-3" /> pass
            </Badge>
          );
        if (e === "fail")
          return (
            <Badge variant="danger">
              <XCircle className="mr-1 size-3" /> fail
            </Badge>
          );
        if (e === "warn") return <Badge variant="warning">warn</Badge>;
        return <Badge variant="secondary">{e}</Badge>;
      },
    },
    {
      accessorKey: "gap_severidad",
      header: "Gap",
      cell: ({ row }) =>
        row.original.gap_severidad ? (
          <Badge
            variant={
              row.original.gap_severidad === "critical" ||
              row.original.gap_severidad === "high"
                ? "danger"
                : row.original.gap_severidad === "medium"
                  ? "warning"
                  : "info"
            }
          >
            {row.original.gap_severidad}
          </Badge>
        ) : (
          <span className="text-fulkro-ink-300">—</span>
        ),
    },
    {
      accessorKey: "fuente_conector",
      header: "Fuente",
      cell: ({ row }) => (
        <span className="text-sm text-fulkro-ink-500">{row.original.fuente_conector}</span>
      ),
    },
    {
      id: "medidas",
      header: "ENS",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.medidas_ens_afectadas.slice(0, 3).map((m) => (
            <Badge key={m} variant="info" className="text-xs">{m}</Badge>
          ))}
          {row.original.medidas_ens_afectadas.length > 3 ? (
            <span className="text-xs text-fulkro-ink-500">
              +{row.original.medidas_ens_afectadas.length - 3}
            </span>
          ) : null}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Settings size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Checks de configuración
            {summary ? (
              <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
                ({summary.total})
              </span>
            ) : null}
          </h3>
        </div>
        {summary ? (
          <div className="flex items-center gap-2 text-xs">
            <Badge variant="success">{summary.pass} pass</Badge>
            <Badge variant="danger">{summary.fail} fail</Badge>
            {summary.warn > 0 ? <Badge variant="warning">{summary.warn} warn</Badge> : null}
          </div>
        ) : null}
      </div>

      <DataTable
        columns={columns}
        data={configs}
        searchKey="sistema"
        searchPlaceholder="Buscar checks…"
        loading={isLoading}
        emptyState={
          <div className="flex flex-col items-center gap-2 py-10 text-fulkro-ink-500">
            <Settings className="size-8" />
            <p className="text-sm">Sin checks de configuración</p>
          </div>
        }
      />

      <Sheet
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null);
        }}
      >
        <SheetContent className="w-full sm:max-w-md">
          {detail ? (
            <>
              <SheetHeader>
                <SheetTitle>{detail.control_id}</SheetTitle>
              </SheetHeader>
              <dl className="mt-4 space-y-3 text-sm">
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Sistema</dt>
                  <dd>{detail.sistema}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Descripción control</dt>
                  <dd>{detail.control_description ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Valor esperado</dt>
                  <dd className="font-mono text-xs">{detail.valor_esperado ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Valor actual</dt>
                  <dd className="font-mono text-xs">{detail.valor_actual ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Herramienta detección</dt>
                  <dd>{detail.herramienta_deteccion}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Raw output</dt>
                  <dd>
                    <pre className="mt-1 max-h-40 overflow-auto rounded bg-fulkro-canvas p-2 text-xs">
                      {JSON.stringify(detail.raw_output, null, 2)}
                    </pre>
                  </dd>
                </div>
              </dl>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}
