"use client";

/**
 * CrossProjectComplianceTable · Admin UI Bloque 4 Phase B v3.12.
 *
 * Tabla aggregated multi-project compliance posture admin single pane of glass.
 *
 * Cols:
 *   - Cliente / Proyecto
 *   - Categoría · BÁSICA/MEDIA/ALTA
 *   - Overall health badge
 *   - Conformidad
 *   - Remediations pending
 *   - Tasks pending
 *   - Evidences missing
 *   - Gaps críticos
 *   - Última actividad
 *   - Ver detalles → drill-down `/admin/projects/{id}/compliance` (TBD route)
 */
import { useMemo, useState } from "react";
import Link from "next/link";
import { ChevronRight, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ADMIN_HEALTH_LABELS,
  ADMIN_HEALTH_VARIANTS,
  type AdminHealthIndicator,
  type ProjectComplianceRow,
} from "@/lib/api/admin-cross-project-compliance";

interface CrossProjectComplianceTableProps {
  rows: ProjectComplianceRow[];
  isRefetching: boolean;
  onRefresh: () => void;
}

type SortKey = "overall" | "client" | "remediations" | "tasks" | "gaps";

const HEALTH_RANK: Record<AdminHealthIndicator, number> = {
  critical: 0,
  warning: 1,
  unknown: 2,
  ok: 3,
};

function formatDateShort(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-ES", {
      month: "short",
      day: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function CrossProjectComplianceTable({
  rows,
  isRefetching,
  onRefresh,
}: CrossProjectComplianceTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("overall");
  const [filterHealth, setFilterHealth] = useState<AdminHealthIndicator | "all">(
    "all",
  );

  const filtered = useMemo(() => {
    if (filterHealth === "all") return rows;
    return rows.filter((r) => r.overall_health === filterHealth);
  }, [rows, filterHealth]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    if (sortKey === "overall") {
      copy.sort(
        (a, b) =>
          HEALTH_RANK[a.overall_health] - HEALTH_RANK[b.overall_health],
      );
    } else if (sortKey === "client") {
      copy.sort((a, b) => a.client_name.localeCompare(b.client_name));
    } else if (sortKey === "remediations") {
      copy.sort((a, b) => b.remediations_pending - a.remediations_pending);
    } else if (sortKey === "tasks") {
      copy.sort((a, b) => b.tasks_pending - a.tasks_pending);
    } else if (sortKey === "gaps") {
      copy.sort((a, b) => b.gaps_critical_open - a.gaps_critical_open);
    }
    return copy;
  }, [filtered, sortKey]);

  return (
    <div className="space-y-3" data-testid="cross-project-table">
      {/* Filter + refresh */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Filtrar:
          </span>
          {(["all", "critical", "warning", "ok", "unknown"] as const).map(
            (k) => (
              <Button
                key={k}
                size="sm"
                variant={filterHealth === k ? "primary" : "outline"}
                onClick={() => setFilterHealth(k)}
                data-testid={`filter-${k}`}
              >
                {k === "all" ? "Todos" : ADMIN_HEALTH_LABELS[k]}
              </Button>
            ),
          )}
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={onRefresh}
          disabled={isRefetching}
          data-testid="refresh-button"
        >
          <RefreshCw
            className={`h-3 w-3 mr-1 ${isRefetching ? "animate-spin" : ""}`}
          />
          Actualizar
        </Button>
      </div>

      <div className="rounded-md border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead
                onClick={() => setSortKey("client")}
                className="cursor-pointer"
              >
                Cliente / Proyecto
              </TableHead>
              <TableHead>Categoría</TableHead>
              <TableHead
                onClick={() => setSortKey("overall")}
                className="cursor-pointer"
              >
                Estado
              </TableHead>
              <TableHead>Conformidad</TableHead>
              <TableHead
                onClick={() => setSortKey("remediations")}
                className="text-right cursor-pointer"
              >
                Remediations
              </TableHead>
              <TableHead
                onClick={() => setSortKey("tasks")}
                className="text-right cursor-pointer"
              >
                Tareas
              </TableHead>
              <TableHead className="text-right">Evidencias</TableHead>
              <TableHead
                onClick={() => setSortKey("gaps")}
                className="text-right cursor-pointer"
              >
                Críticos
              </TableHead>
              <TableHead>Actividad</TableHead>
              <TableHead className="text-right">Ver</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={10}
                  className="text-center text-muted-foreground py-6"
                >
                  Sin proyectos con este filtro.
                </TableCell>
              </TableRow>
            ) : (
              sorted.map((r) => (
                <TableRow key={r.project_id} data-testid="project-row">
                  <TableCell>
                    <div className="font-medium">{r.client_name}</div>
                    <div className="text-xs text-muted-foreground">
                      {r.project_name}
                    </div>
                  </TableCell>
                  <TableCell>
                    {r.categoria_objetivo && (
                      <Badge variant="outline" className="text-[10px]">
                        {r.categoria_objetivo}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={ADMIN_HEALTH_VARIANTS[r.overall_health]}>
                      {ADMIN_HEALTH_LABELS[r.overall_health]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={ADMIN_HEALTH_VARIANTS[r.conformity_status]}
                      className="text-[10px]"
                    >
                      {ADMIN_HEALTH_LABELS[r.conformity_status]}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {r.remediations_pending}
                  </TableCell>
                  <TableCell className="text-right">{r.tasks_pending}</TableCell>
                  <TableCell className="text-right">
                    {r.evidences_missing}
                  </TableCell>
                  <TableCell className="text-right">
                    {r.gaps_critical_open}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDateShort(r.last_activity_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Link
                      href={`/admin/projects/${r.project_id}/conformity`}
                      className="text-primary hover:underline inline-flex items-center gap-1 text-xs"
                      data-testid={`drill-down-${r.project_id}`}
                    >
                      Ver
                      <ChevronRight className="h-3 w-3" />
                    </Link>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
