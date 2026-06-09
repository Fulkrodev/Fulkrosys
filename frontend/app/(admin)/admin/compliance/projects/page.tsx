"use client";

/**
 * /admin/compliance/projects · Admin UI Bloque 4 Phase B v3.12.
 *
 * Sub-atom Sesión 3B-1 Phase B.2 · MOVE from /admin/cross-project-compliance
 * to consolidate under /admin/compliance/* hierarchy (Option B consolidation).
 *
 * Old route /admin/cross-project-compliance redirects to this canonical path.
 * Reuses CrossProjectComplianceTable component + useAdminCrossProjectCompliance
 * hook unchanged.
 *
 * Admin single pane of glass · TODOS projects cliente aggregated compliance
 * posture · reuse infrastructure existing cross-motor · NO new tables.
 *
 * R23 explicit exception · top-level admin multi-cliente legítimo (similar
 * /admin/clients, /admin/projects root listings).
 */
import { RefreshCw, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { CrossProjectComplianceTable } from "@/components/admin/CrossProjectComplianceTable";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminCrossProjectCompliance } from "@/hooks/useAdminCrossProjectCompliance";
import {
  ADMIN_HEALTH_LABELS,
  ADMIN_HEALTH_VARIANTS,
} from "@/lib/api/admin-cross-project-compliance";

export default function ComplianceProjectsPage() {
  const query = useAdminCrossProjectCompliance();
  const data = query.data;

  return (
    <div className="container mx-auto py-6 space-y-6 max-w-7xl">
      <header className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold flex items-center gap-2 text-fulkro-primary-700">
            <ShieldCheck className="h-6 w-6 text-emerald-600" />
            Compliance multi-cliente
          </h1>
          <Link
            href="/admin/compliance"
            className="text-xs font-medium text-fulkro-info hover:underline"
          >
            ← Volver al centro de cumplimiento
          </Link>
        </div>
        <p className="text-sm text-fulkro-ink-700">
          Vista agregada de la salud de cumplimiento de todos los proyectos
          activos · cross-motor (M27 conformidad · cloud remediations · tareas ·
          evidencias · gaps críticos M04).
        </p>
      </header>

      {/* KPI summary cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="kpi-cards">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                Total
              </CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-bold">
              {data.total_projects}
            </CardContent>
          </Card>
          {(["critical", "warning", "ok", "unknown"] as const).map((k) => (
            <Card key={k}>
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                  {ADMIN_HEALTH_LABELS[k]}
                </CardTitle>
                <Badge variant={ADMIN_HEALTH_VARIANTS[k]} className="text-[10px]">
                  {ADMIN_HEALTH_LABELS[k]}
                </Badge>
              </CardHeader>
              <CardContent className="text-2xl font-bold">
                {data.counts_by_health[k] ?? 0}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Table */}
      {query.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : query.isError ? (
        <Alert variant="danger" className="flex flex-col gap-3">
          <div>
            <AlertTitle>Error cargando datos</AlertTitle>
            <AlertDescription>
              {(query.error as Error)?.message ?? "Error desconocido."}
            </AlertDescription>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
            className="self-start"
            data-testid="compliance-projects-retry"
          >
            <RefreshCw
              size={14}
              className={query.isFetching ? "animate-spin" : ""}
            />
            Reintentar
          </Button>
        </Alert>
      ) : data ? (
        <CrossProjectComplianceTable
          rows={data.projects}
          isRefetching={query.isFetching && !query.isLoading}
          onRefresh={() => query.refetch()}
        />
      ) : null}

      {data && (
        <p className="text-xs text-muted-foreground text-right">
          Actualizado · {new Date(data.generated_at).toLocaleString("es-ES")}
        </p>
      )}
    </div>
  );
}
