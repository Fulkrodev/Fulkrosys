"use client";

import * as React from "react";
import { Cloud, Layers, Loader2, RefreshCw, Server } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { useConsolidatedDiscovery } from "@/hooks/useCloudConnectorsAdmin";
import {
  type ConsolidatedAsset,
  type ConsolidatedProvenance,
  PROVENANCE_LABEL,
  PROVENANCE_VARIANT,
} from "@/lib/api/cloud-connectors-admin";

export interface ConsolidatedTabProps {
  projectId: string;
}

const PROVENANCE_OPTIONS: { value: ConsolidatedProvenance | "all"; label: string }[] = [
  { value: "all", label: "Todos los orígenes" },
  { value: "manual", label: "Solo manual" },
  { value: "cloud", label: "Solo cloud detected" },
  { value: "both", label: "Consolidados (both)" },
];

function ProvenanceIcon({ provenance }: { provenance: ConsolidatedProvenance }) {
  if (provenance === "manual") {
    return <Server className="size-3.5 text-fulkro-ink-400" aria-hidden />;
  }
  if (provenance === "cloud") {
    return <Cloud className="size-3.5 text-fulkro-primary-600" aria-hidden />;
  }
  return <Layers className="size-3.5 text-fulkro-success-600" aria-hidden />;
}

export function ConsolidatedTab({ projectId }: ConsolidatedTabProps) {
  const { data, isLoading, isFetching, refetch } = useConsolidatedDiscovery(projectId);
  const [provFilter, setProvFilter] = React.useState<ConsolidatedProvenance | "all">("all");
  const [typeFilter, setTypeFilter] = React.useState<string>("all");

  const assets = data?.assets ?? [];
  const counts = data?.counts;

  const typeOptions = React.useMemo(() => {
    const types = new Set<string>();
    for (const a of assets) {
      if (a.resource_type_normalized) types.add(a.resource_type_normalized);
    }
    return Array.from(types).sort();
  }, [assets]);

  const filtered = React.useMemo(() => {
    return assets.filter((a) => {
      if (provFilter !== "all" && a.provenance !== provFilter) return false;
      if (typeFilter !== "all" && a.resource_type_normalized !== typeFilter) return false;
      return true;
    });
  }, [assets, provFilter, typeFilter]);

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center" data-testid="consolidated-loading">
        <Loader2 className="size-6 animate-spin text-fulkro-primary-500" />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const hasCloudConnectors = (counts?.cloud_only ?? 0) + (counts?.both ?? 0) > 0;

  return (
    <div className="space-y-4" data-testid="consolidated-tab">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-fulkro-ink-900">
            Inventario consolidado
          </h3>
          <p className="text-xs text-fulkro-ink-500">
            Unifica activos M22 manuales + recursos cloud detectados · resolver
            duplicados via match por nombre.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          data-testid="consolidated-refresh"
        >
          {isFetching ? (
            <>
              <Loader2 className="mr-2 size-4 animate-spin" />
              Re-consolidando…
            </>
          ) : (
            <>
              <RefreshCw className="mr-2 size-4" />
              Re-consolidar
            </>
          )}
        </Button>
      </div>

      {/* KPI summary cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4" data-testid="consolidated-counts">
        <div className="rounded-md border border-fulkro-ink-200 bg-white p-3">
          <p className="text-xs text-fulkro-ink-500">Total</p>
          <p className="mt-1 text-xl font-semibold">{counts?.total ?? 0}</p>
        </div>
        <div className="rounded-md border border-fulkro-ink-200 bg-white p-3">
          <p className="flex items-center gap-1 text-xs text-fulkro-ink-500">
            <Server className="size-3" /> Solo manual
          </p>
          <p className="mt-1 text-xl font-semibold">{counts?.manual_only ?? 0}</p>
        </div>
        <div className="rounded-md border border-fulkro-ink-200 bg-white p-3">
          <p className="flex items-center gap-1 text-xs text-fulkro-ink-500">
            <Cloud className="size-3" /> Solo cloud
          </p>
          <p className="mt-1 text-xl font-semibold">{counts?.cloud_only ?? 0}</p>
        </div>
        <div className="rounded-md border border-fulkro-ink-200 bg-white p-3">
          <p className="flex items-center gap-1 text-xs text-fulkro-ink-500">
            <Layers className="size-3" /> Consolidados
          </p>
          <p className="mt-1 text-xl font-semibold">{counts?.both ?? 0}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="min-w-[180px]">
          <Select
            value={provFilter}
            onValueChange={(v) => setProvFilter(v as ConsolidatedProvenance | "all")}
          >
            <SelectTrigger data-testid="consolidated-filter-provenance">
              <SelectValue placeholder="Origen" />
            </SelectTrigger>
            <SelectContent>
              {PROVENANCE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {typeOptions.length > 0 && (
          <div className="min-w-[180px]">
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger data-testid="consolidated-filter-type">
                <SelectValue placeholder="Tipo recurso" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los tipos</SelectItem>
                {typeOptions.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {/* Empty states */}
      {!hasCloudConnectors && (counts?.manual_only ?? 0) === 0 && (
        <div
          className="rounded-md border border-dashed border-fulkro-ink-200 bg-fulkro-ink-50 p-6 text-center"
          data-testid="consolidated-empty"
        >
          <p className="text-sm text-fulkro-ink-600">
            Sin activos manuales ni cloud detectados todavía.
          </p>
          <p className="mt-1 text-xs text-fulkro-ink-500">
            Lanza un scan de discovery o conecta un proveedor cloud para empezar.
          </p>
        </div>
      )}

      {!hasCloudConnectors && (counts?.manual_only ?? 0) > 0 && (
        <div
          className="rounded-md border border-fulkro-warning-200 bg-fulkro-warning-50 p-3 text-xs text-fulkro-warning-800"
          data-testid="consolidated-no-cloud-hint"
        >
          Sin conectores cloud activos · vista actual solo refleja activos manuales.
          Conectar un proveedor cloud habilita matching automático.
        </div>
      )}

      {/* Asset list */}
      {filtered.length > 0 && (
        <div
          className="overflow-x-auto rounded-md border border-fulkro-ink-200"
          data-testid="consolidated-list"
        >
          <table className="min-w-full divide-y divide-fulkro-ink-200 text-sm">
            <thead className="bg-fulkro-ink-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-fulkro-ink-700">
                  Nombre
                </th>
                <th className="px-3 py-2 text-left font-medium text-fulkro-ink-700">
                  Tipo
                </th>
                <th className="px-3 py-2 text-left font-medium text-fulkro-ink-700">
                  Origen
                </th>
                <th className="px-3 py-2 text-left font-medium text-fulkro-ink-700">
                  Provider
                </th>
                <th className="px-3 py-2 text-left font-medium text-fulkro-ink-700">
                  Criticidad
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-fulkro-ink-100 bg-white">
              {filtered.map((asset: ConsolidatedAsset, idx) => (
                <tr
                  key={`${asset.manual_asset_id ?? ""}-${asset.cloud_resource_id ?? ""}-${idx}`}
                  data-testid={`consolidated-row-${asset.provenance}`}
                >
                  <td className="px-3 py-2 font-medium text-fulkro-ink-900">
                    {asset.name}
                  </td>
                  <td className="px-3 py-2 text-fulkro-ink-600">
                    {asset.resource_type_normalized || "—"}
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant={PROVENANCE_VARIANT[asset.provenance]}>
                      <ProvenanceIcon provenance={asset.provenance} />
                      <span className="ml-1">{PROVENANCE_LABEL[asset.provenance]}</span>
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-fulkro-ink-600">
                    {asset.provider ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-fulkro-ink-600">
                    {asset.criticidad ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {filtered.length === 0 && (counts?.total ?? 0) > 0 && (
        <div
          className="rounded-md border border-dashed border-fulkro-ink-200 bg-white p-4 text-center text-sm text-fulkro-ink-500"
          data-testid="consolidated-filtered-empty"
        >
          Sin activos que coincidan con los filtros aplicados.
        </div>
      )}
    </div>
  );
}
