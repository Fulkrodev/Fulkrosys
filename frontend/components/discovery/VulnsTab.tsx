"use client";

import * as React from "react";
import { AlertTriangle, Bug, Crosshair } from "lucide-react";
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
import { cn } from "@/lib/utils";

import {
  useDiscoveryVulns,
  useUpdateVulnerability,
  useVulnsSummary,
} from "@/hooks/useDiscovery";
import type { DiscoveryVulnerability, Severidad } from "@/lib/admin-discovery/api";

export interface VulnsTabProps {
  projectId: string;
}

const SEVERITY_VARIANT: Record<Severidad, "danger" | "warning" | "info" | "secondary"> = {
  critical: "danger",
  high: "danger",
  medium: "warning",
  low: "info",
  info: "secondary",
};

const SEVERITY_ORDER: Severidad[] = ["critical", "high", "medium", "low", "info"];
const ESTADO_ORDER = ["open", "mitigated", "accepted", "false_positive"] as const;

export function VulnsTab({ projectId }: VulnsTabProps) {
  const { data: vulns = [], isLoading } = useDiscoveryVulns(projectId);
  const { data: summary } = useVulnsSummary(projectId);
  const updateMutation = useUpdateVulnerability(projectId);
  const [detail, setDetail] = React.useState<DiscoveryVulnerability | null>(null);

  const heatmap = React.useMemo(() => {
    const grid: Record<string, Record<string, number>> = {};
    for (const sev of SEVERITY_ORDER) {
      grid[sev] = { open: 0, mitigated: 0, accepted: 0, false_positive: 0 };
    }
    for (const v of vulns) {
      const sev = v.cvss_severity ?? "info";
      grid[sev][v.estado] = (grid[sev][v.estado] ?? 0) + 1;
    }
    return grid;
  }, [vulns]);

  const triggerPentestDive = (assetId: string | null, cve: string | null) => {
    if (!assetId) {
      toast.warning("Vulnerabilidad sin activo asociado · no se puede lanzar pentest");
      return;
    }
    toast.info(
      `Pentest deep-dive iniciado · activo ${assetId.slice(0, 8)} · ${cve ?? "sin CVE"}`,
    );
  };

  const columns: ColumnDef<DiscoveryVulnerability>[] = [
    {
      accessorKey: "titulo",
      header: "Título",
      cell: ({ row }) => (
        <button
          type="button"
          onClick={() => setDetail(row.original)}
          className="text-left font-medium text-fulkro-primary-700 hover:underline"
        >
          {row.original.titulo}
        </button>
      ),
    },
    {
      accessorKey: "cve_id",
      header: () => (
        <span className="inline-flex items-center gap-1">
          CVE <TooltipENS term="CVE" />
        </span>
      ),
      cell: ({ row }) =>
        row.original.cve_id ? (
          <span className="font-mono text-xs">{row.original.cve_id}</span>
        ) : (
          <span className="text-fulkro-ink-300">—</span>
        ),
    },
    {
      accessorKey: "cvss_score",
      header: () => (
        <span className="inline-flex items-center gap-1">
          CVSS <TooltipENS term="CVSS" />
        </span>
      ),
      cell: ({ row }) =>
        row.original.cvss_score !== null ? (
          <span className="font-mono">{row.original.cvss_score.toFixed(1)}</span>
        ) : (
          "—"
        ),
    },
    {
      accessorKey: "cvss_severity",
      header: "Severidad",
      cell: ({ row }) => {
        const sev = row.original.cvss_severity;
        if (!sev) return <span className="text-fulkro-ink-300">—</span>;
        return <Badge variant={SEVERITY_VARIANT[sev]}>{sev}</Badge>;
      },
    },
    {
      accessorKey: "estado",
      header: "Estado",
      cell: ({ row }) => {
        const v = row.original;
        return (
          <select
            value={v.estado}
            onChange={(e) =>
              updateMutation.mutate({
                findingId: v.id,
                body: { estado: e.target.value as DiscoveryVulnerability["estado"] },
              })
            }
            className="rounded border border-fulkro-ink-200 bg-white px-2 py-1 text-xs"
            aria-label={`Cambiar estado de ${v.titulo}`}
          >
            {ESTADO_ORDER.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        );
      },
    },
    {
      accessorKey: "es_explotable",
      header: "Explotable",
      cell: ({ row }) =>
        row.original.es_explotable ? (
          <Badge variant="danger">
            <Crosshair className="mr-1 size-3" /> sí
          </Badge>
        ) : (
          <span className="text-fulkro-ink-300">—</span>
        ),
    },
    {
      id: "acciones",
      header: "Acciones",
      cell: ({ row }) => (
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => triggerPentestDive(row.original.asset_id, row.original.cve_id)}
        >
          <TooltipENS term="pentest">
            <span>Pentest</span>
          </TooltipENS>
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Bug size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Vulnerabilidades
            {summary ? (
              <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
                ({summary.total})
              </span>
            ) : null}
          </h3>
        </div>
        {summary && summary.explotables > 0 ? (
          <Badge variant="danger">
            <AlertTriangle className="mr-1 size-3" /> {summary.explotables} explotables
          </Badge>
        ) : null}
      </div>

      <div className="rounded-lg border border-fulkro-ink-100 bg-white p-3">
        <p className="mb-2 text-xs font-medium text-fulkro-ink-700">
          Heatmap severidad × estado
        </p>
        <div className="grid grid-cols-5 gap-2 text-xs">
          <div />
          {ESTADO_ORDER.map((e) => (
            <div key={e} className="text-center font-medium text-fulkro-ink-500">
              {e}
            </div>
          ))}
          {SEVERITY_ORDER.map((sev) => (
            <React.Fragment key={sev}>
              <div className="font-medium text-fulkro-ink-700">{sev}</div>
              {ESTADO_ORDER.map((e) => {
                const count = heatmap[sev][e] ?? 0;
                return (
                  <div
                    key={e}
                    className={cn(
                      "rounded text-center py-1",
                      count === 0 && "bg-fulkro-canvas text-fulkro-ink-300",
                      count > 0 && sev === "critical" && "bg-destructive/15 text-destructive",
                      count > 0 && sev === "high" && "bg-fulkro-warning/15 text-fulkro-warning",
                      count > 0 && sev === "medium" && "bg-fulkro-info/15 text-fulkro-info",
                      count > 0 && (sev === "low" || sev === "info") && "bg-fulkro-success/15 text-fulkro-success",
                    )}
                  >
                    {count}
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>

      <DataTable
        columns={columns}
        data={vulns}
        searchKey="titulo"
        searchPlaceholder="Buscar vulnerabilidades…"
        loading={isLoading}
        emptyState={
          <div className="flex flex-col items-center gap-2 py-10 text-fulkro-ink-500">
            <Bug className="size-8" />
            <p className="text-sm">Sin vulnerabilidades · ejecuta scan para importar</p>
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
                <SheetTitle>{detail.titulo}</SheetTitle>
                <SheetDescription>
                  {detail.cve_id ? `${detail.cve_id} · ` : ""}
                  CVSS {detail.cvss_score?.toFixed(1) ?? "—"}
                </SheetDescription>
              </SheetHeader>
              <dl className="mt-4 space-y-3 text-sm">
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Descripción</dt>
                  <dd>{detail.descripcion ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Remediación sugerida</dt>
                  <dd>{detail.remediacion_sugerida ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Activo afectado</dt>
                  <dd>{detail.asset_afectado ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">CVSS vector</dt>
                  <dd className="font-mono text-xs">{detail.cvss_vector ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">MITRE tactics</dt>
                  <dd className="flex flex-wrap gap-1">
                    {detail.mitre_tactics.length > 0 ? (
                      detail.mitre_tactics.map((t) => (
                        <Badge key={t} variant="outline">{t}</Badge>
                      ))
                    ) : (
                      <span className="text-fulkro-ink-300">—</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Medidas ENS</dt>
                  <dd className="flex flex-wrap gap-1">
                    {detail.medidas_ens_afectadas.length > 0 ? (
                      detail.medidas_ens_afectadas.map((m) => (
                        <Badge key={m} variant="info">{m}</Badge>
                      ))
                    ) : (
                      <span className="text-fulkro-ink-300">—</span>
                    )}
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
