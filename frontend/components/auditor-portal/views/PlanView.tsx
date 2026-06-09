"use client";

/**
 * PlanView · Phase 5.4 auditor portal · plan adecuación read-only.
 *
 * Display:
 * - Plan header (versión + estado + categoría + fechas + esfuerzo)
 * - WBS tasks list ordenado por task_code · phase + dependencies +
 *   responsable + deliverable_e_code + critical path flag visible
 * - Phase grouping (collapse-friendly · client-side)
 */
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Loader2, Map } from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  getAuditorPortalPlan,
  type AuditorPortalPlan,
  type AuditorPortalPlanTask,
} from "@/lib/api/auditor-portal";

interface Props {
  token: string;
}

function fmtDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString();
}

function TaskRow({ task }: { task: AuditorPortalPlanTask }) {
  return (
    <div
      className="rounded-md border border-fulkro-ink-300/60 bg-white p-3"
      data-testid={`auditor-plan-task-${task.task_code}`}
    >
      <div className="mb-1 flex flex-wrap items-baseline gap-2">
        <span className="font-mono text-xs font-semibold text-fulkro-ink-900">
          {task.task_code}
        </span>
        <span className="text-sm font-medium text-fulkro-ink-900">
          {task.task_name}
        </span>
        {task.is_critical_path ? (
          <Badge variant="warning" data-testid="auditor-plan-critical-flag">
            Camino crítico
          </Badge>
        ) : null}
        {task.deliverable_e_code ? (
          <Badge variant="outline">{task.deliverable_e_code}</Badge>
        ) : null}
        {task.status ? (
          <Badge variant="secondary">{task.status}</Badge>
        ) : null}
      </div>
      <div className="grid grid-cols-2 gap-1 text-[12px] text-fulkro-ink-500 sm:grid-cols-4">
        <span>Inicio: {fmtDate(task.start_date)}</span>
        <span>Fin: {fmtDate(task.end_date)}</span>
        <span>
          Esfuerzo:{" "}
          {task.effort_marcos_hours !== null
            ? `${task.effort_marcos_hours}h`
            : "—"}
        </span>
        <span>Progreso: {task.progress_pct}%</span>
      </div>
      {task.responsible ? (
        <p className="mt-1 text-[12px] text-fulkro-ink-700">
          Responsable: {task.responsible}
        </p>
      ) : null}
    </div>
  );
}

export function PlanView({ token }: Props) {
  const [phaseFilter, setPhaseFilter] = React.useState<string>("all");

  const data = useQuery<AuditorPortalPlan>({
    queryKey: ["auditor-portal", "plan", token],
    queryFn: () => getAuditorPortalPlan(token),
    enabled: Boolean(token),
    staleTime: 60_000,
    retry: false,
  });

  const phases = React.useMemo(() => {
    if (!data.data) return [];
    const set = new Set<string>();
    for (const t of data.data.tasks) {
      if (t.phase) set.add(t.phase);
    }
    return Array.from(set).sort();
  }, [data.data]);

  const filtered = React.useMemo(() => {
    if (!data.data) return [];
    if (phaseFilter === "all") return data.data.tasks;
    return data.data.tasks.filter((t) => t.phase === phaseFilter);
  }, [data.data, phaseFilter]);

  if (data.isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-fulkro-ink-500"
        data-testid="auditor-plan-loading"
      >
        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
        Cargando plan de adecuación…
      </div>
    );
  }

  if (data.isError || !data.data) {
    return (
      <Alert variant="danger" data-testid="auditor-plan-error">
        <AlertCircle size={14} aria-hidden="true" />
        <AlertTitle>No se pudo cargar el plan</AlertTitle>
        <AlertDescription>
          Reintenta más tarde o solicita un enlace nuevo al consultor responsable.
        </AlertDescription>
      </Alert>
    );
  }

  const { plan, tasks } = data.data;

  if (!plan) {
    return (
      <Alert data-testid="auditor-plan-empty">
        <AlertTitle>Sin plan registrado</AlertTitle>
        <AlertDescription>
          Este proyecto aún no dispone de plan de adecuación aprobado.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4" data-testid="auditor-plan-view">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Map
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Plan de adecuación · versión {plan.version}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-3">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Estado
            </p>
            <p className="font-medium text-fulkro-ink-900">
              {plan.estado ?? "—"}
            </p>
            {plan.aprobado_at ? (
              <p className="text-[11px] text-fulkro-success-700">
                Aprobado el {fmtDate(plan.aprobado_at)}
              </p>
            ) : null}
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Cronograma
            </p>
            <p className="font-medium text-fulkro-ink-900">
              {fmtDate(plan.start_date)} → {fmtDate(plan.end_date_estimated)}
            </p>
            {plan.total_duration_weeks ? (
              <p className="text-[11px] text-fulkro-ink-500">
                {plan.total_duration_weeks} semanas
              </p>
            ) : null}
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Esfuerzo Marcos
            </p>
            <p className="font-medium text-fulkro-ink-900">
              {plan.total_effort_marcos_hours !== null
                ? `${plan.total_effort_marcos_hours}h`
                : "—"}
            </p>
            {plan.critical_path_length_weeks ? (
              <p className="text-[11px] text-fulkro-ink-500">
                Camino crítico: {plan.critical_path_length_weeks} semanas
              </p>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Tareas WBS · {tasks.length} totales
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {phases.length > 1 ? (
            <div className="flex flex-wrap gap-1" role="group" aria-label="Filtrar por fase">
              <button
                type="button"
                onClick={() => setPhaseFilter("all")}
                className={
                  "rounded-full border px-3 py-1 text-[11px] " +
                  (phaseFilter === "all"
                    ? "border-fulkro-primary-700 bg-fulkro-primary-700/10 text-fulkro-primary-700"
                    : "border-fulkro-ink-300 text-fulkro-ink-700 hover:bg-fulkro-ink-100")
                }
                data-testid="auditor-plan-phase-all"
              >
                Todas
              </button>
              {phases.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPhaseFilter(p)}
                  className={
                    "rounded-full border px-3 py-1 text-[11px] " +
                    (phaseFilter === p
                      ? "border-fulkro-primary-700 bg-fulkro-primary-700/10 text-fulkro-primary-700"
                      : "border-fulkro-ink-300 text-fulkro-ink-700 hover:bg-fulkro-ink-100")
                  }
                  data-testid={`auditor-plan-phase-${p}`}
                >
                  {p}
                </button>
              ))}
            </div>
          ) : null}

          {filtered.length === 0 ? (
            <Alert>
              <AlertTitle>Sin tareas</AlertTitle>
              <AlertDescription>
                No hay tareas que coincidan con el filtro de fase.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="space-y-2">
              {filtered.map((t) => (
                <TaskRow key={t.id} task={t} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
