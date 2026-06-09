"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Database, ExternalLink, Server, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import {
  useAssetsSummary,
  useDiscoveryAssets,
} from "@/hooks/useDiscovery";
import type { DiscoveryAsset } from "@/lib/admin-discovery/api";

export interface AssetsTabProps {
  projectId: string;
}

const CRITICIDAD_VARIANT: Record<string, "danger" | "warning" | "info" | "secondary"> = {
  critica: "danger",
  alta: "warning",
  media: "info",
  baja: "secondary",
};

export function AssetsTab({ projectId }: AssetsTabProps) {
  const router = useRouter();
  const { data: assets = [], isLoading } = useDiscoveryAssets(projectId);
  const { data: summary } = useAssetsSummary(projectId);

  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(new Set());
  const [detailAsset, setDetailAsset] = React.useState<DiscoveryAsset | null>(null);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleImportToMagerit = () => {
    if (selectedIds.size === 0) {
      toast.warning("Selecciona al menos un activo para importar");
      return;
    }
    toast.info(
      `${selectedIds.size} activos preseleccionados · abriendo MAGERIT…`,
    );
    router.push(`/admin/projects/${projectId}/magerit?import=${Array.from(selectedIds).join(",")}`);
  };

  const columns: ColumnDef<DiscoveryAsset>[] = [
    {
      id: "select",
      header: () => null,
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={selectedIds.has(row.original.id)}
          onChange={() => toggleSelect(row.original.id)}
          className="size-4 cursor-pointer rounded border-fulkro-ink-300"
          aria-label={`Seleccionar ${row.original.nombre}`}
        />
      ),
    },
    {
      accessorKey: "nombre",
      header: "Nombre",
      cell: ({ row }) => (
        <button
          type="button"
          onClick={() => setDetailAsset(row.original)}
          className="text-left font-medium text-fulkro-primary-700 hover:underline"
        >
          {row.original.nombre}
        </button>
      ),
    },
    {
      accessorKey: "tipo_magerit",
      header: () => (
        <span className="inline-flex items-center gap-1">
          Tipo MAGERIT <TooltipENS term="MAGERIT" />
        </span>
      ),
      cell: ({ row }) =>
        row.original.tipo_magerit ? (
          <Badge variant="outline">{row.original.tipo_magerit}</Badge>
        ) : (
          <span className="text-fulkro-ink-300">—</span>
        ),
    },
    {
      accessorKey: "criticidad_propuesta",
      header: "Criticidad",
      cell: ({ row }) => {
        const crit = row.original.criticidad_propuesta;
        if (!crit) return <span className="text-fulkro-ink-300">—</span>;
        const variant = CRITICIDAD_VARIANT[crit.toLowerCase()] ?? "secondary";
        return <Badge variant={variant}>{crit}</Badge>;
      },
    },
    {
      accessorKey: "fuente_conector",
      header: "Fuente",
      cell: ({ row }) =>
        row.original.fuente_conector ? (
          <span className="text-sm text-fulkro-ink-500">{row.original.fuente_conector}</span>
        ) : (
          <span className="text-fulkro-ink-300">—</span>
        ),
    },
    {
      accessorKey: "ubicacion",
      header: "Ubicación",
      cell: ({ row }) => row.original.ubicacion ?? "—",
    },
    {
      accessorKey: "propietario_inferido",
      header: "Propietario",
      cell: ({ row }) => row.original.propietario_inferido ?? "—",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Server size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Activos descubiertos
            {summary ? (
              <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
                ({summary.total})
              </span>
            ) : null}
          </h3>
          <TooltipENS term="MAGERIT" />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-fulkro-ink-500">
            {selectedIds.size > 0 ? `${selectedIds.size} seleccionado(s)` : null}
          </span>
          <Button
            type="button"
            variant="primary"
            disabled={selectedIds.size === 0}
            onClick={handleImportToMagerit}
          >
            <ExternalLink className="mr-2 size-4" />
            Importar a MAGERIT
          </Button>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={assets}
        searchKey="nombre"
        searchPlaceholder="Buscar activos…"
        loading={isLoading}
        emptyState={
          <div className="flex flex-col items-center gap-2 py-10 text-fulkro-ink-500">
            <Database className="size-8" />
            <p className="text-sm">Sin activos descubiertos · ejecuta un scan completo</p>
          </div>
        }
      />

      <Sheet
        open={detailAsset !== null}
        onOpenChange={(open) => {
          if (!open) setDetailAsset(null);
        }}
      >
        <SheetContent className="w-full sm:max-w-md">
          {detailAsset ? (
            <>
              <SheetHeader>
                <SheetTitle>{detailAsset.nombre}</SheetTitle>
                <SheetDescription>
                  {detailAsset.descripcion ?? "Sin descripción adicional."}
                </SheetDescription>
              </SheetHeader>
              <dl className="mt-4 space-y-3 text-sm">
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Tipo MAGERIT</dt>
                  <dd>{detailAsset.tipo_magerit ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Criticidad</dt>
                  <dd>{detailAsset.criticidad_propuesta ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Identificador</dt>
                  <dd className="font-mono text-xs">{detailAsset.identificador ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Ubicación</dt>
                  <dd>{detailAsset.ubicacion ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Fuente conector</dt>
                  <dd>{detailAsset.fuente_conector ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Metadata extra</dt>
                  <dd>
                    <pre className="mt-1 overflow-x-auto rounded bg-fulkro-canvas p-2 text-xs">
                      {JSON.stringify(detailAsset.metadata_extra, null, 2)}
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
