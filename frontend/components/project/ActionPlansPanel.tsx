/**
 * ActionPlansPanel · Dashboard K.3 admin cross-motor findings consolidados.
 *
 * Sub-atom 1.D.C.B v3.11 · materializa Anexo K dim 3 · cierra GAP 10 audit v4.
 *
 * Aggregator endpoint /api/v1/projects/{id}/action-plans combines:
 *   - M04 gap findings (severidad crítica/alta + estado abierto/en_curso)
 *   - M09 audit_prep checklist items (priority critical/high)
 *   - A21 discrepancies open critical/high (1.D.A v3.10)
 */
"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowUpRight,
  ClipboardCheck,
  ListChecks,
  Loader2,
  ShieldAlert,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  actionPlansApi,
  type ActionPlanItem,
  type ActionPlanSeverity,
  type ActionPlanSource,
  type ActionPlansResponse,
} from "@/lib/api/action-plans";

const SEVERITY_VARIANT: Record<
  ActionPlanSeverity,
  "danger" | "warning" | "info" | "secondary"
> = {
  critica: "danger",
  alta: "warning",
  media: "info",
  baja: "secondary",
};

const SOURCE_LABEL: Record<ActionPlanSource, string> = {
  m04_gap: "Gap (M04)",
  m09_audit_prep: "Audit prep (M09)",
  m19_incident: "Incidente (M19)",
  a21_discrepancy: "Discrepancia (A21)",
};

const SOURCE_ICON: Record<ActionPlanSource, React.ReactNode> = {
  m04_gap: <ListChecks size={12} />,
  m09_audit_prep: <ClipboardCheck size={12} />,
  m19_incident: <AlertTriangle size={12} />,
  a21_discrepancy: <ShieldAlert size={12} />,
};

const FAMILIA_LABEL: Record<string, string> = {
  org: "Organizativa",
  op: "Operacional",
  mp: "Protección",
  cross: "Cross-motor",
};

export function ActionPlansPanel({ projectId }: { projectId: string }) {
  const [severityFilter, setSeverityFilter] = React.useState<
    ActionPlanSeverity[]
  >([]);
  const [sourceFilter, setSourceFilter] = React.useState<ActionPlanSource[]>(
    [],
  );

  const query = useQuery<ActionPlansResponse>({
    queryKey: ["action-plans", projectId, severityFilter, sourceFilter],
    queryFn: () =>
      actionPlansApi.list(projectId, {
        limit: 10,
        severity: severityFilter.length > 0 ? severityFilter : undefined,
        source: sourceFilter.length > 0 ? sourceFilter : undefined,
      }),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  return (
    <div className="space-y-4" data-testid="action-plans-panel">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ListChecks size={16} /> Planes de acción · Dashboard K.3
          </CardTitle>
          <CardDescription>
            Top findings consolidados cross-motor · M04 gap · M09 audit_prep ·
            A21 discrepancias. Cierre GAP 10 audit ENAC.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="font-medium text-foreground/60">Severidad:</span>
            {(["critica", "alta", "media", "baja"] as ActionPlanSeverity[]).map(
              (s) => {
                const active = severityFilter.includes(s);
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => {
                      setSeverityFilter((prev) =>
                        prev.includes(s)
                          ? prev.filter((x) => x !== s)
                          : [...prev, s],
                      );
                    }}
                    className={`rounded-full border px-2 py-0.5 capitalize transition-colors ${
                      active
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-input bg-background text-foreground/60 hover:bg-muted"
                    }`}
                    data-testid={`action-plans-filter-severity-${s}`}
                  >
                    {s}
                  </button>
                );
              },
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="font-medium text-foreground/60">Origen:</span>
            {(
              ["m04_gap", "m09_audit_prep", "a21_discrepancy"] as ActionPlanSource[]
            ).map((s) => {
              const active = sourceFilter.includes(s);
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() => {
                    setSourceFilter((prev) =>
                      prev.includes(s)
                        ? prev.filter((x) => x !== s)
                        : [...prev, s],
                    );
                  }}
                  className={`flex items-center gap-1 rounded-full border px-2 py-0.5 transition-colors ${
                    active
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-input bg-background text-foreground/60 hover:bg-muted"
                  }`}
                  data-testid={`action-plans-filter-source-${s}`}
                >
                  {SOURCE_ICON[s]}
                  {SOURCE_LABEL[s]}
                </button>
              );
            })}
          </div>

          {/* Counts summary */}
          {query.data && query.data.total_count > 0 && (
            <div
              className="flex flex-wrap items-center gap-3 rounded-md border bg-muted/30 px-3 py-2 text-xs"
              data-testid="action-plans-counts"
            >
              <span className="font-semibold text-foreground/70">
                Total: {query.data.total_count}
              </span>
              {Object.entries(query.data.counts_by_severity).map(
                ([sev, count]) => (
                  <span key={sev} className="capitalize text-foreground/60">
                    {sev}: <strong>{count}</strong>
                  </span>
                ),
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">
            Top {query.data?.items.length ?? 10} findings prioritarios
          </CardTitle>
        </CardHeader>
        <CardContent>
          {query.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : query.isError ? (
            <Alert variant="danger">
              <AlertTitle>Error cargando planes de acción</AlertTitle>
              <AlertDescription>
                {query.error instanceof Error
                  ? query.error.message
                  : "Error desconocido"}
              </AlertDescription>
            </Alert>
          ) : !query.data || query.data.items.length === 0 ? (
            <EmptyState
              icon={<ListChecks size={32} />}
              title="Sin findings prioritarios"
              description={
                query.isFetching
                  ? "Cargando..."
                  : "El cliente no tiene findings críticos/altos abiertos · estado conformidad correcto"
              }
            />
          ) : (
            <ul
              className="divide-y divide-border"
              data-testid="action-plans-list"
            >
              {query.data.items.map((item) => (
                <ActionPlanRow key={`${item.source}-${item.id}`} item={item} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ActionPlanRow({ item }: { item: ActionPlanItem }) {
  return (
    <li
      className="flex items-start justify-between gap-3 py-3"
      data-testid={`action-plans-row-${item.source}`}
    >
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2 text-xs">
          <Badge
            variant={SEVERITY_VARIANT[item.severity]}
            className="capitalize"
            data-testid={`action-plans-severity-${item.severity}`}
          >
            {item.severity}
          </Badge>
          <Badge variant="outline" className="flex items-center gap-1">
            {SOURCE_ICON[item.source]}
            {SOURCE_LABEL[item.source]}
          </Badge>
          {item.familia !== "cross" && (
            <Badge variant="secondary" className="text-[10px]">
              {FAMILIA_LABEL[item.familia] ?? item.familia}
            </Badge>
          )}
          {item.medida_afectada && (
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">
              {item.medida_afectada}
            </code>
          )}
        </div>
        <p className="text-sm text-foreground/85">{item.description}</p>
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-foreground/55">
          {item.responsable && (
            <span>Responsable: {item.responsable}</span>
          )}
          {item.fecha_objetivo && (
            <span>
              Deadline: {new Date(item.fecha_objetivo).toLocaleDateString("es-ES")}
            </span>
          )}
          <span className="capitalize">Estado: {item.estado}</span>
        </div>
      </div>
      {item.motor_link && (
        <Link
          href={item.motor_link}
          className="flex shrink-0 items-center gap-1 rounded-md border border-input bg-background px-2.5 py-1.5 text-xs font-semibold text-foreground/70 transition-colors hover:bg-muted"
          data-testid="action-plans-drilldown"
        >
          Drill-down
          <ArrowUpRight size={12} />
        </Link>
      )}
    </li>
  );
}
