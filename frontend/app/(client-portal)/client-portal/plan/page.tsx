"use client";

/**
 * /client-portal/plan · Sesión 3B-2B.8 Phase 1E · Plan adecuación cliente READ-ONLY.
 *
 * Cliente READ-ONLY view del plan ENS:
 *   - Reuses GanttView component (DRY OPS-026 · exported PlanGantt.tsx)
 *   - "Solo mis tareas" toggle filter responsible IN (cliente, mixto)
 *   - SSE subscribe m17.plan.updated → invalidate refetch + toast
 *   - R29 friendly Spanish + R30 inverso (NO admin lingo)
 *   - ADR-014 read-only (cliente NO modifica · backend NO PATCH endpoints)
 *
 * Pattern Phase 1A+1B+1C+1D sostained · ADR-013 doble pool + Sub-atom 5.A.
 */

import * as React from "react";
import { CalendarRange, Loader2, Map } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ImplementationPaymentsSummary } from "@/components/client-portal/ImplementationPaymentsSummary";
import { PageContainer } from "@/components/layout/PageContainer";
import { GanttView, type TimelineResponse } from "@/components/project/PlanGantt";
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
import { Switch } from "@/components/ui/switch";
import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import {
  fetchClientePlan,
  isClienteTask,
  type ClienteTimelineResponse,
} from "@/lib/api/plan-cliente";

const PLAN_QUERY_KEY = ["client-portal", "plan"] as const;

function adaptToGanttView(
  data: ClienteTimelineResponse,
  filterCliente: boolean,
): TimelineResponse {
  const tasks = filterCliente
    ? data.tasks.filter(isClienteTask)
    : data.tasks;
  return {
    plan_start: data.plan_start,
    plan_end: data.plan_end,
    tasks: tasks.map((t) => ({
      id: t.id,
      task_code: t.task_code,
      task_name: t.task_name,
      phase: t.phase,
      start_date: t.start_date,
      end_date: t.end_date,
      status: t.status,
      progress_pct: t.progress_pct,
      is_critical_path: t.is_critical_path,
      responsible: t.responsible,
    })),
    milestones: data.milestones.map((m) => ({
      name: m.name,
      date: m.date,
      type: m.type as
        | "plan_milestone"
        | "conformity_expiration"
        | "objective"
        | "kickoff",
      status: m.status,
    })),
    plan_estado: data.plan_estado,
  };
}

export default function ClientePlanPage() {
  const queryClient = useQueryClient();
  const [filterMisTareas, setFilterMisTareas] = React.useState(false);

  const planQuery = useQuery<ClienteTimelineResponse>({
    queryKey: PLAN_QUERY_KEY as unknown as string[],
    queryFn: fetchClientePlan,
    staleTime: 60_000,
  });

  // SSE subscribe · m17.plan.updated invalidate refetch + toast friendly.
  useClientProjectEvents(planQuery.data?.project_id ?? null, {
    invalidateQueries: [PLAN_QUERY_KEY as unknown as string[]],
    onM17PlanUpdated: (evt) => {
      const taskName = evt.data.task_name ?? "una tarea";
      toast.info(`Marcos actualizó "${taskName}" en tu plan.`);
    },
  });

  if (planQuery.isLoading) {
    return (
      <PageContainer variant="app">
        <div
          className="space-y-4"
          data-testid="cliente-plan-loading"
        >
          <Skeleton className="h-8 w-1/2" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      </PageContainer>
    );
  }

  if (planQuery.isError) {
    return (
      <PageContainer variant="app">
        <Alert variant="danger" data-testid="cliente-plan-error">
          <AlertTitle>No pudimos cargar tu plan</AlertTitle>
          <AlertDescription>
            Recarga la página. Si sigue pasando avisa a Marcos por chat.
          </AlertDescription>
        </Alert>
      </PageContainer>
    );
  }

  const data = planQuery.data;
  if (!data) {
    return (
      <PageContainer variant="app">
        <Card>
          <CardContent className="p-6">
            <EmptyState
              icon={<CalendarRange className="h-12 w-12" />}
              title="Sin plan todavía"
              description="Marcos te creará el plan cuando arranquemos la fase de adecuación."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  const totalTasks = data.tasks.length;
  const cliente_tasks_count = data.tasks.filter(isClienteTask).length;
  const ganttData = adaptToGanttView(data, filterMisTareas);

  return (
    <PageContainer variant="app">
      <div className="space-y-6" data-testid="cliente-plan-page">
        <header className="space-y-2">
        <h1 className="flex items-center gap-2 text-2xl font-semibold text-fulkro-primary-700">
          <Map className="size-6" />
          Mi plan ENS
        </h1>
        <p className="text-sm text-fulkro-ink-500">
          Cronograma de tu adecuación al Esquema Nacional de Seguridad ·
          {" "}
          {data.plan_estado ? (
            <Badge variant="secondary" className="ml-1">
              {data.plan_estado}
            </Badge>
          ) : (
            <span className="italic">sin plan aprobado todavía</span>
          )}
        </p>
      </header>

      {totalTasks === 0 ? (
        <Card>
          <CardContent className="p-6">
            <EmptyState
              icon={<CalendarRange className="h-12 w-12" />}
              title="Plan vacío"
              description="Cuando Marcos cargue tareas las verás aquí."
            />
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Toggle "Solo mis tareas" · filter responsible IN (cliente, mixto) */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Vista del plan</CardTitle>
              <CardDescription className="text-xs">
                {totalTasks} tareas en total · {cliente_tasks_count} con tu
                participación.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <label
                className="flex items-center gap-3 text-sm"
                htmlFor="cliente-plan-filter-mis-tareas"
              >
                <Switch
                  id="cliente-plan-filter-mis-tareas"
                  checked={filterMisTareas}
                  onCheckedChange={(v) => setFilterMisTareas(Boolean(v))}
                  data-testid="cliente-plan-filter-toggle"
                />
                <span className="font-medium">Solo mis tareas</span>
                <span className="text-xs text-fulkro-ink-500">
                  ({cliente_tasks_count})
                </span>
              </label>
            </CardContent>
          </Card>

          {/* Gantt cliente READ-ONLY · reuse GanttView (DRY OPS-026) */}
          <div data-testid="cliente-plan-gantt">
            {filterMisTareas && cliente_tasks_count === 0 ? (
              <Card>
                <CardContent className="p-6">
                  <EmptyState
                    title="Sin tareas asignadas a ti"
                    description="Marcos te avisará cuando tengas tareas pendientes. Sin prisa."
                  />
                </CardContent>
              </Card>
            ) : (
              <GanttView data={ganttData} />
            )}
          </div>
        </>
      )}

        {/* #45 · resumen amable de hitos y pagos (se autooculta si no hay hitos) */}
        <ImplementationPaymentsSummary />
      </div>
    </PageContainer>
  );
}
