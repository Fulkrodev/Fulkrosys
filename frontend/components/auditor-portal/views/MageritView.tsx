"use client";

/**
 * MageritView · Phase 5.3 auditor portal · MAGERIT analysis read-only.
 *
 * Displays:
 * - Analysis header (name + status + frozen state)
 * - Assets list (code + name + asset_type + DICAT valuation +
 *   accumulated values + cliente review status)
 * - Filter by asset_type_code (client-side)
 * - Risks total counter (detail per-risk deferred Phase 6 if architect approves)
 */
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Loader2, ShieldAlert } from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  getAuditorPortalMagerit,
  type AuditorPortalMagerit,
  type AuditorPortalMageritAsset,
} from "@/lib/api/auditor-portal";
import { AnnotationPanel } from "@/components/auditor-portal/annotations/AnnotationPanel";

interface Props {
  token: string;
}

function fmt(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return String(value);
}

function fmtAcc(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return value.toFixed(2);
}

function AssetCard({
  asset,
  token,
}: {
  asset: AuditorPortalMageritAsset;
  token: string;
}) {
  const reviewVariant =
    asset.client_review_status === "revisada_ok"
      ? "success"
      : asset.client_review_status
        ? "warning"
        : "outline";

  return (
    <div
      className="rounded-md border border-fulkro-ink-300/60 bg-white p-3"
      data-testid={`auditor-magerit-asset-${asset.code}`}
    >
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-xs font-semibold text-fulkro-ink-900">
            {asset.code}
          </span>
          <span className="text-sm font-medium text-fulkro-ink-900">
            {asset.name}
          </span>
          <Badge variant="outline" data-testid="auditor-magerit-asset-type">
            {asset.asset_type_code}
          </Badge>
        </div>
        <Badge variant={reviewVariant as "success" | "warning" | "outline"}>
          {asset.client_review_status ?? "sin revisión"}
        </Badge>
      </div>
      {asset.owner ? (
        <p className="text-[12px] text-fulkro-ink-500">Propietario: {asset.owner}</p>
      ) : null}
      <div className="mt-2 grid grid-cols-2 gap-1 sm:grid-cols-3 md:grid-cols-5 text-[11px]">
        <div className="rounded bg-fulkro-ink-50 px-1.5 py-1 text-center">
          <p className="text-fulkro-ink-500">D</p>
          <p className="font-semibold text-fulkro-ink-900">
            {fmt(asset.valuation.d)}
          </p>
        </div>
        <div className="rounded bg-fulkro-ink-50 px-1.5 py-1 text-center">
          <p className="text-fulkro-ink-500">I</p>
          <p className="font-semibold text-fulkro-ink-900">
            {fmt(asset.valuation.i)}
          </p>
        </div>
        <div className="rounded bg-fulkro-ink-50 px-1.5 py-1 text-center">
          <p className="text-fulkro-ink-500">C</p>
          <p className="font-semibold text-fulkro-ink-900">
            {fmt(asset.valuation.c)}
          </p>
        </div>
        <div className="rounded bg-fulkro-ink-50 px-1.5 py-1 text-center">
          <p className="text-fulkro-ink-500">A</p>
          <p className="font-semibold text-fulkro-ink-900">
            {fmt(asset.valuation.a)}
          </p>
        </div>
        <div className="rounded bg-fulkro-ink-50 px-1.5 py-1 text-center">
          <p className="text-fulkro-ink-500">T</p>
          <p className="font-semibold text-fulkro-ink-900">
            {fmt(asset.valuation.t)}
          </p>
        </div>
      </div>
      <div className="mt-1 grid grid-cols-2 gap-1 sm:grid-cols-3 md:grid-cols-5 text-[10px] text-fulkro-ink-500">
        <span className="text-center">acum D: {fmtAcc(asset.accumulated.d)}</span>
        <span className="text-center">acum I: {fmtAcc(asset.accumulated.i)}</span>
        <span className="text-center">acum C: {fmtAcc(asset.accumulated.c)}</span>
        <span className="text-center">acum A: {fmtAcc(asset.accumulated.a)}</span>
        <span className="text-center">acum T: {fmtAcc(asset.accumulated.t)}</span>
      </div>
      <div className="mt-2">
        <AnnotationPanel
          token={token}
          targetType="magerit_asset"
          targetId={asset.id}
          targetLabel={`Activo ${asset.code} · ${asset.name}`}
          compact
        />
      </div>
    </div>
  );
}

export function MageritView({ token }: Props) {
  const [typeFilter, setTypeFilter] = React.useState<string>("");
  const data = useQuery<AuditorPortalMagerit>({
    queryKey: ["auditor-portal", "magerit", token],
    queryFn: () => getAuditorPortalMagerit(token),
    enabled: Boolean(token),
    staleTime: 60_000,
    retry: false,
  });

  const filtered = React.useMemo(() => {
    if (!data.data) return [];
    if (!typeFilter.trim()) return data.data.assets;
    const lower = typeFilter.trim().toLowerCase();
    return data.data.assets.filter((a) =>
      a.asset_type_code.toLowerCase().includes(lower),
    );
  }, [data.data, typeFilter]);

  if (data.isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-fulkro-ink-500"
        data-testid="auditor-magerit-loading"
      >
        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
        Cargando análisis MAGERIT…
      </div>
    );
  }

  if (data.isError || !data.data) {
    return (
      <Alert variant="danger" data-testid="auditor-magerit-error">
        <AlertCircle size={14} aria-hidden="true" />
        <AlertTitle>No se pudo cargar MAGERIT</AlertTitle>
        <AlertDescription>
          Reintenta más tarde o solicita un enlace nuevo al consultor responsable.
        </AlertDescription>
      </Alert>
    );
  }

  const { analysis, assets, risks_total } = data.data;

  if (!analysis) {
    return (
      <Alert data-testid="auditor-magerit-empty">
        <AlertTitle>No hay análisis MAGERIT registrado</AlertTitle>
        <AlertDescription>
          Este proyecto aún no dispone de análisis de riesgos MAGERIT firmado.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4" data-testid="auditor-magerit-view">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldAlert
              size={16}
              className="text-fulkro-warning-700"
              aria-hidden="true"
            />
            Análisis MAGERIT · {analysis.name}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-3">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Estado
            </p>
            <p className="font-medium text-fulkro-ink-900">{analysis.status}</p>
            {analysis.frozen_at ? (
              <p className="text-[11px] text-fulkro-success-700">
                Congelado{" "}
                {new Date(analysis.frozen_at).toLocaleDateString()}
              </p>
            ) : null}
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Activos inventariados
            </p>
            <p
              className="text-xl font-semibold text-fulkro-ink-900"
              data-testid="auditor-magerit-assets-total"
            >
              {assets.length}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Análisis amenazas
            </p>
            <p
              className="text-xl font-semibold text-fulkro-ink-900"
              data-testid="auditor-magerit-risks-total"
            >
              {risks_total}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Activos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label
              htmlFor="auditor-magerit-type-filter"
              className="text-[11px] uppercase tracking-wider text-fulkro-ink-500"
            >
              Filtrar por tipo (código exacto o parcial)
            </label>
            <Input
              id="auditor-magerit-type-filter"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              placeholder="ej.: HW · SW · K · D"
              aria-label="Filtrar activos por tipo"
              data-testid="auditor-magerit-type-filter"
              className="h-9"
            />
          </div>
          {filtered.length === 0 ? (
            <Alert>
              <AlertTitle>Sin activos</AlertTitle>
              <AlertDescription>
                No hay activos que coincidan con el filtro de tipo.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="space-y-2">
              {filtered.map((a) => (
                <AssetCard key={a.id} asset={a} token={token} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
