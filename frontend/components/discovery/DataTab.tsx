"use client";

import * as React from "react";
import { Database, FileWarning, Lock, ShieldCheck } from "lucide-react";
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
  useDataStoresSummary,
  useDiscoveryDataStores,
} from "@/hooks/useDiscovery";
import type { DiscoveryDataStore } from "@/lib/admin-discovery/api";

export interface DataTabProps {
  projectId: string;
}

const CLASIFICACION_VARIANT: Record<string, "danger" | "warning" | "info" | "secondary"> = {
  rgpd_art9: "danger",
  alta: "danger",
  pii: "warning",
  sensitive: "warning",
  media: "info",
  baja: "secondary",
  sin_clasificar: "secondary",
};

export function DataTab({ projectId }: DataTabProps) {
  const { data: stores = [], isLoading } = useDiscoveryDataStores(projectId);
  const { data: summary } = useDataStoresSummary(projectId);
  const [detail, setDetail] = React.useState<DiscoveryDataStore | null>(null);

  const columns: ColumnDef<DiscoveryDataStore>[] = [
    {
      accessorKey: "nombre",
      header: "Nombre",
      cell: ({ row }) => (
        <button
          type="button"
          onClick={() => setDetail(row.original)}
          className="text-left font-medium text-fulkro-primary-700 hover:underline"
        >
          {row.original.nombre}
        </button>
      ),
    },
    {
      accessorKey: "tipo",
      header: "Tipo",
      cell: ({ row }) => <Badge variant="outline">{row.original.tipo}</Badge>,
    },
    {
      accessorKey: "ubicacion",
      header: "Ubicación",
      cell: ({ row }) => (
        <span className="font-mono text-xs">{row.original.ubicacion}</span>
      ),
    },
    {
      accessorKey: "clasificacion_inicial",
      header: () => (
        <span className="inline-flex items-center gap-1">
          Clasificación <TooltipENS term="categoria_alta" />
        </span>
      ),
      cell: ({ row }) => {
        const v = row.original.clasificacion_inicial;
        const variant = CLASIFICACION_VARIANT[v] ?? "secondary";
        return <Badge variant={variant}>{v}</Badge>;
      },
    },
    {
      id: "categorias",
      header: "Categorías",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.tiene_datos_personales ? (
            <Badge variant="warning">PII</Badge>
          ) : null}
          {row.original.tiene_datos_salud ? (
            <Badge variant="danger">salud</Badge>
          ) : null}
          {row.original.tiene_datos_financieros ? (
            <Badge variant="info">financieros</Badge>
          ) : null}
          {!row.original.tiene_datos_personales &&
          !row.original.tiene_datos_salud &&
          !row.original.tiene_datos_financieros ? (
            <span className="text-xs text-fulkro-ink-300">—</span>
          ) : null}
        </div>
      ),
    },
    {
      id: "cifrado",
      header: "Cifrado",
      cell: ({ row }) => {
        const reposo = row.original.cifrado_en_reposo;
        const transito = row.original.cifrado_en_transito;
        if (reposo === null && transito === null)
          return <span className="text-fulkro-ink-300">—</span>;
        return (
          <div className="flex items-center gap-1 text-xs">
            <Lock size={12} className="text-fulkro-ink-500" />
            <span className={reposo ? "text-fulkro-success" : "text-fulkro-warning"}>
              reposo: {reposo ? "sí" : "no"}
            </span>
            <span>·</span>
            <span className={transito ? "text-fulkro-success" : "text-fulkro-warning"}>
              tránsito: {transito ? "sí" : "no"}
            </span>
          </div>
        );
      },
    },
    {
      accessorKey: "tiene_backup",
      header: "Backup",
      cell: ({ row }) => {
        if (row.original.tiene_backup === null)
          return <span className="text-fulkro-ink-300">—</span>;
        return row.original.tiene_backup ? (
          <Badge variant="success">
            <ShieldCheck className="mr-1 size-3" /> sí
          </Badge>
        ) : (
          <Badge variant="danger">
            <FileWarning className="mr-1 size-3" /> no
          </Badge>
        );
      },
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Database size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Almacenes de datos
            {summary ? (
              <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
                ({summary.total})
              </span>
            ) : null}
          </h3>
          <TooltipENS term="RGPD_Art_49" />
        </div>
        {summary ? (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {summary.con_datos_personales > 0 ? (
              <Badge variant="warning">{summary.con_datos_personales} con PII</Badge>
            ) : null}
            {summary.con_datos_salud > 0 ? (
              <Badge variant="danger">{summary.con_datos_salud} con datos de salud</Badge>
            ) : null}
          </div>
        ) : null}
      </div>

      <DataTable
        columns={columns}
        data={stores}
        searchKey="nombre"
        searchPlaceholder="Buscar almacenes…"
        loading={isLoading}
        emptyState={
          <div className="flex flex-col items-center gap-2 py-10 text-fulkro-ink-500">
            <Database className="size-8" />
            <p className="text-sm">Sin almacenes de datos descubiertos</p>
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
                <SheetTitle>{detail.nombre}</SheetTitle>
              </SheetHeader>
              <dl className="mt-4 space-y-3 text-sm">
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Volumen estimado</dt>
                  <dd>
                    {detail.volumen_estimado_gb !== null
                      ? `${detail.volumen_estimado_gb.toLocaleString("es-ES")} GB`
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Patrones detectados</dt>
                  <dd className="flex flex-wrap gap-1">
                    {detail.patrones_detectados.length > 0 ? (
                      detail.patrones_detectados.map((p) => (
                        <Badge key={p} variant="outline">{p}</Badge>
                      ))
                    ) : (
                      <span className="text-fulkro-ink-300">ninguno</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Control de acceso</dt>
                  <dd>{detail.control_acceso ?? "—"}</dd>
                </div>
              </dl>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}
