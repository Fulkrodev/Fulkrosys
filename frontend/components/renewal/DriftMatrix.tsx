"use client";

/**
 * DriftMatrix · 10 dimensiones × 4 severidades heatmap (SAN-E v3.MB-3.4).
 *
 * Wired al backend M28 mv_drift_summary_10x4 (commit MB-3.E 6daaae2).
 * Click cell con count > 0 abre Sheet drawer con items detected (futuro
 * endpoint detail · placeholder por ahora con mensaje).
 */
import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import {
  Activity,
  Building,
  ClipboardCheck,
  Cpu,
  Database,
  Key,
  LifeBuoy,
  Loader2,
  Lock,
  RefreshCw,
  Shield,
  Users,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import { useRenewalStatus } from "@/hooks/useRenewalStatus";
import {
  DRIFT_DIMENSIONS,
  DRIFT_SEVERITIES,
  listDriftEvents,
  type DriftDimension,
  type DriftSeverity,
} from "@/lib/admin-renewal/api";

// S28d FIX: dimensiones REALES de retainer_drift_events (antes auth/cifrado/...
// inexistentes en BD). Etiquetas legibles + icono por dimensión.
const DIMENSION_META: Record<DriftDimension, { label: string; icon: LucideIcon }> = {
  infraestructura: { label: "Infraestructura", icon: Cpu },
  identidad: { label: "Identidad", icon: Key },
  proveedores: { label: "Proveedores", icon: Building },
  normativa: { label: "Normativa", icon: ClipboardCheck },
  overlay: { label: "Overlay sectorial", icon: Shield },
  cpstic: { label: "Productos CPSTIC", icon: Lock },
  roles: { label: "Roles y funciones", icon: Users },
  continuidad: { label: "Continuidad", icon: LifeBuoy },
  evidencias: { label: "Evidencias", icon: Database },
  contratos: { label: "Contratos", icon: Activity },
};

const SEVERITY_META: Record<
  DriftSeverity,
  { label: string; bgClass: (count: number) => string; textClass: string }
> = {
  CRITICAL: {
    label: "Crítica",
    bgClass: (n: number) =>
      n === 0
        ? "bg-fulkro-ink-50"
        : n >= 5
        ? "bg-fulkro-danger/40"
        : n >= 2
        ? "bg-fulkro-danger/25"
        : "bg-fulkro-danger/15",
    textClass: "text-fulkro-danger",
  },
  HIGH: {
    label: "Alta",
    bgClass: (n: number) =>
      n === 0
        ? "bg-fulkro-ink-50"
        : n >= 5
        ? "bg-fulkro-warning/40"
        : n >= 2
        ? "bg-fulkro-warning/25"
        : "bg-fulkro-warning/15",
    textClass: "text-fulkro-warning",
  },
  MEDIUM: {
    label: "Media",
    bgClass: (n: number) =>
      n === 0
        ? "bg-fulkro-ink-50"
        : n >= 5
        ? "bg-fulkro-info/30"
        : "bg-fulkro-info/15",
    textClass: "text-fulkro-info",
  },
  LOW: {
    label: "Baja",
    bgClass: (n: number) =>
      n === 0 ? "bg-fulkro-ink-50" : "bg-fulkro-ink-100",
    textClass: "text-fulkro-ink-500",
  },
};

interface CellSelectionState {
  dimension: DriftDimension;
  severity: DriftSeverity;
  count: number;
  lastDetected: string | null;
}

interface DriftMatrixProps {
  projectId: string;
}

export function DriftMatrix({ projectId }: DriftMatrixProps) {
  const { drift } = useRenewalStatus(projectId);
  const [selected, setSelected] = React.useState<CellSelectionState | null>(
    null,
  );

  // Build matrix lookup: dimension → severity → count
  const cellLookup = React.useMemo(() => {
    const map = new Map<string, { count: number; lastDetected: string | null }>();
    if (drift.data) {
      for (const cell of drift.data.items) {
        const key = `${cell.dimension}|${cell.severidad}`;
        map.set(key, {
          count: cell.open_count,
          lastDetected: cell.last_detected,
        });
      }
    }
    return map;
  }, [drift.data]);

  const cellsWithDrift = drift.data?.items.filter((c) => c.open_count > 0).length ?? 0;
  const totalOpen = drift.data?.open_total ?? 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2 text-[color:var(--fulkro-title)]">
          Matriz de drift{" "}
          <TooltipENS
            text="Drift normativo: desviaciones detectadas entre lo que tu sistema HACE y lo que el ENS EXIGE. La matriz cruza 10 dimensiones (autenticación, cifrado, etc) por 4 severidades (crítica → baja). Click en una celda para ver los items específicos."
            iconSize={14}
          />
          <Badge variant={totalOpen > 0 ? "warning" : "success"} className="ml-auto">
            {totalOpen} {totalOpen === 1 ? "drift abierto" : "drifts abiertos"}
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void drift.refetch()}
            disabled={drift.isFetching}
            aria-label="Refrescar matriz"
          >
            <RefreshCw
              size={14}
              strokeWidth={2.4}
              className={drift.isFetching ? "animate-spin" : ""}
            />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Matrix grid */}
        <div className="overflow-x-auto">
          <table
            aria-label="Matriz de desviación (drift) de medidas"
            className="w-full border-separate border-spacing-1 text-sm"
          >
            <thead>
              <tr>
                <th className="w-[180px] text-left text-xs font-semibold uppercase tracking-wide text-fulkro-ink-600">
                  Dimensión
                </th>
                {DRIFT_SEVERITIES.map((sev) => (
                  <th
                    key={sev}
                    className={cn(
                      "px-2 py-1 text-center text-xs font-bold uppercase",
                      SEVERITY_META[sev].textClass,
                    )}
                  >
                    {SEVERITY_META[sev].label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {DRIFT_DIMENSIONS.map((dim) => {
                const meta = DIMENSION_META[dim];
                const Icon = meta.icon;
                return (
                  <tr key={dim}>
                    <td className="py-1 pr-2">
                      <div className="flex items-center gap-2">
                        <Icon
                          size={14}
                          strokeWidth={2.4}
                          className="text-fulkro-ink-500"
                        />
                        <span className="text-xs font-medium text-fulkro-ink-700">
                          {meta.label}
                        </span>
                      </div>
                    </td>
                    {DRIFT_SEVERITIES.map((sev) => {
                      const key = `${dim}|${sev}`;
                      const cell = cellLookup.get(key);
                      const count = cell?.count ?? 0;
                      const sevMeta = SEVERITY_META[sev];
                      return (
                        <td key={`${dim}-${sev}`} className="p-0.5">
                          <button
                            type="button"
                            disabled={count === 0}
                            onClick={() =>
                              setSelected({
                                dimension: dim,
                                severity: sev,
                                count,
                                lastDetected: cell?.lastDetected ?? null,
                              })
                            }
                            className={cn(
                              "flex h-12 w-full items-center justify-center rounded-md text-base font-bold tabular-nums transition-all",
                              sevMeta.bgClass(count),
                              count > 0
                                ? `${sevMeta.textClass} cursor-pointer hover:scale-105 hover:shadow-sm`
                                : "cursor-default text-fulkro-ink-300",
                            )}
                            title={
                              count > 0
                                ? `${count} ${
                                    count === 1 ? "drift abierto" : "drifts abiertos"
                                  } · ${
                                    cell?.lastDetected
                                      ? `último ${new Date(
                                          cell.lastDetected,
                                        ).toLocaleDateString("es-ES")}`
                                      : "sin fecha"
                                  }`
                                : "Sin drifts en esta combinación"
                            }
                          >
                            {count > 0 ? count : "—"}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Footer leyenda */}
        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-fulkro-ink-100 pt-3 text-[10px] text-fulkro-ink-500">
          <span className="font-bold uppercase tracking-wide">Leyenda</span>
          {DRIFT_SEVERITIES.map((sev) => (
            <span key={sev} className="flex items-center gap-1.5">
              <span
                className={cn(
                  "inline-block h-3 w-6 rounded-sm",
                  SEVERITY_META[sev].bgClass(3),
                )}
              />
              {SEVERITY_META[sev].label}
            </span>
          ))}
          <span className="ml-auto">
            {cellsWithDrift} / 40 celdas con drift
          </span>
        </div>
      </CardContent>

      {/* Drawer detail per cell */}
      <Sheet
        open={selected !== null}
        onOpenChange={(v) => {
          if (!v) setSelected(null);
        }}
      >
        <SheetContent className="w-full max-w-md overflow-y-auto">
          {selected ? (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2 text-[color:var(--fulkro-title)]">
                  {React.createElement(DIMENSION_META[selected.dimension].icon, {
                    size: 18,
                    strokeWidth: 2.4,
                  })}
                  {DIMENSION_META[selected.dimension].label} ·{" "}
                  {SEVERITY_META[selected.severity].label}
                </SheetTitle>
                <SheetDescription>
                  {selected.count}{" "}
                  {selected.count === 1
                    ? "drift abierto detectado"
                    : "drifts abiertos detectados"}
                  {selected.lastDetected
                    ? ` · último ${new Date(
                        selected.lastDetected,
                      ).toLocaleDateString("es-ES")}`
                    : ""}
                </SheetDescription>
              </SheetHeader>

              <DriftCellDetail
                projectId={projectId}
                dimension={selected.dimension}
                severity={selected.severity}
              />
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </Card>
  );
}

/**
 * S28d · drill-down real: lista los drift events abiertos de la celda
 * (dimension, severidad) seleccionada. Fetch on-open con tanstack-query.
 */
function DriftCellDetail({
  projectId,
  dimension,
  severity,
}: {
  projectId: string;
  dimension: DriftDimension;
  severity: DriftSeverity;
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["drift-events", projectId, dimension, severity],
    queryFn: () =>
      listDriftEvents(projectId, {
        dimension,
        severidad: severity,
        estado: "open",
      }),
  });

  if (isLoading) {
    return (
      <div className="mt-6 flex items-center gap-2 text-sm text-fulkro-ink-500">
        <Loader2 size={14} className="animate-spin" /> cargando items…
      </div>
    );
  }
  if (isError) {
    return (
      <div className="mt-6 rounded-md border border-fulkro-danger/30 bg-fulkro-danger/5 p-4 text-sm text-fulkro-danger">
        No se pudieron cargar los items de esta celda.
      </div>
    );
  }
  const items = data ?? [];
  if (items.length === 0) {
    return (
      <div className="mt-6 rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-4 text-sm text-fulkro-ink-500">
        Sin items abiertos en esta combinación.
      </div>
    );
  }
  return (
    <ul className="mt-6 space-y-2">
      {items.map((it) => (
        <li
          key={it.id}
          className="rounded-md border border-fulkro-ink-200 bg-white p-3 text-sm"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-fulkro-ink-800">
              {it.impacto ?? "drift"}
            </span>
            <span className="text-xs text-fulkro-ink-500">
              {it.created_at
                ? new Date(it.created_at).toLocaleDateString("es-ES")
                : "—"}
            </span>
          </div>
          {it.descripcion && (
            <p className="mt-1 text-xs text-fulkro-ink-600">{it.descripcion}</p>
          )}
        </li>
      ))}
    </ul>
  );
}
