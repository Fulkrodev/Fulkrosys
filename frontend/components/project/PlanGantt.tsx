/**
 * PlanGantt · Timeline visual del proyecto (FASE 9.B / MB-4.C.3).
 *
 * Backend: GET /api/v1/projects/{project_id}/timeline (composer M17 + M27).
 * Render: SVG Gantt simple con barras horizontales por task + milestones
 * como diamantes verticales. Critical path resaltado borde rojo.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CalendarRange,
  Diamond,
  Loader2,
  TrendingUp,
} from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { api } from "@/lib/api";

// Sesión 3B-2B.8 Phase 1E · types exported para reuse cliente portal.
export interface TimelineTask {
  id: string;
  task_code: string;
  task_name: string;
  phase: string | null;
  start_date: string | null;
  end_date: string | null;
  status: string | null;
  progress_pct: number;
  is_critical_path: boolean;
  // Optional cliente-only field (Sub-atom 1E)
  responsible?: string | null;
}

export interface TimelineMilestone {
  name: string;
  date: string | null;
  type: "plan_milestone" | "conformity_expiration" | "objective" | "kickoff";
  status: string | null;
}

export interface TimelineResponse {
  plan_start: string | null;
  plan_end: string | null;
  tasks: TimelineTask[];
  milestones: TimelineMilestone[];
  plan_estado: string | null;
}

const STATUS_COLOR: Record<string, string> = {
  completed: "fill-emerald-500",
  in_progress: "fill-blue-500",
  pending: "fill-fulkro-ink-300",
  blocked: "fill-red-500",
};

const MILESTONE_COLOR: Record<string, string> = {
  plan_milestone: "text-fulkro-primary-700",
  conformity_expiration: "text-amber-600",
  objective: "text-emerald-600",
  kickoff: "text-blue-600",
};

export function PlanGantt({ projectId }: { projectId: string }) {
  const { data, isLoading, isError, error } = useQuery<TimelineResponse>({
    queryKey: ["project-composer", "timeline", projectId],
    queryFn: () =>
      api<TimelineResponse>(`/api/v1/projects/${projectId}/timeline`),
    enabled: Boolean(projectId),
    staleTime: 60_000,
    retry: false,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" /> cargando timeline…
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="danger">
            <AlertTitle>No se pudo cargar el timeline</AlertTitle>
            <AlertDescription>
              {error instanceof Error ? error.message : "Error desconocido"}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!data.plan_start || !data.plan_end) {
    return (
      <Card>
        <CardContent className="p-6">
          <EmptyState
            title="Sin plan definido"
            description="Cuando se cree el plan del proyecto (M17) aparecerá el Gantt aquí."
          />
        </CardContent>
      </Card>
    );
  }

  return <GanttView data={data} />;
}

/**
 * GanttView · Sub-component renderizando timeline data ya fetched.
 * Exportada Sesión 3B-2B.8 Phase 1E · cliente portal reusa con own data fetch.
 */
export function GanttView({ data }: { data: TimelineResponse }) {
  const planStart = new Date(data.plan_start!);
  const planEnd = new Date(data.plan_end!);
  const totalDays = Math.max(
    1,
    (planEnd.getTime() - planStart.getTime()) / (24 * 60 * 60 * 1000),
  );

  function pctFromDate(iso: string | null): number {
    if (!iso) return 0;
    const d = new Date(iso);
    const days = (d.getTime() - planStart.getTime()) / (24 * 60 * 60 * 1000);
    return Math.max(0, Math.min(100, (days / totalDays) * 100));
  }

  const monthMarkers = computeMonthMarkers(planStart, planEnd);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-2 text-base">
            <span className="flex items-center gap-2">
              <CalendarRange size={16} /> Plan de proyecto
            </span>
            {data.plan_estado ? (
              <Badge variant="secondary">{data.plan_estado}</Badge>
            ) : null}
          </CardTitle>
          <p className="mt-1 text-xs text-fulkro-ink-500">
            {planStart.toLocaleDateString()} → {planEnd.toLocaleDateString()} ·
            {" "}
            {Math.ceil(totalDays / 7)} semanas · {data.tasks.length} tareas ·{" "}
            {data.milestones.length} hitos
          </p>
        </CardHeader>
        <CardContent>
          {data.tasks.length === 0 && data.milestones.length === 0 ? (
            <EmptyState
              title="Plan vacío"
              description="No hay tareas ni hitos aún."
            />
          ) : (
            <div className="space-y-1">
              <MonthHeader markers={monthMarkers} />
              <div className="space-y-1.5">
                {data.tasks.map((t) => (
                  <TaskBar key={t.id} task={t} pctFromDate={pctFromDate} />
                ))}
              </div>
              <MilestoneRow
                milestones={data.milestones}
                pctFromDate={pctFromDate}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {data.milestones.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Diamond size={14} /> Hitos
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5 text-xs">
              {data.milestones.map((m, idx) => (
                <li
                  key={`${m.name}-${idx}`}
                  className="flex items-center justify-between gap-3 rounded-md border border-fulkro-ink-300/60 px-3 py-1.5"
                >
                  <span className="flex items-center gap-2 truncate">
                    <Diamond
                      size={10}
                      className={MILESTONE_COLOR[m.type] ?? ""}
                    />
                    <span className="truncate font-medium text-fulkro-ink-700">
                      {m.name}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-1.5">
                    {m.status ? (
                      <Badge variant="outline">{m.status}</Badge>
                    ) : null}
                    <span className="font-mono text-[11px] text-fulkro-ink-500">
                      {m.date ? new Date(m.date).toLocaleDateString() : "—"}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function MonthHeader({
  markers,
}: {
  markers: { label: string; pct: number }[];
}) {
  return (
    <div className="relative h-5 border-b border-fulkro-ink-300/60">
      {markers.map((m, i) => (
        <div
          key={`${m.label}-${i}`}
          className="absolute top-0 text-[9px] uppercase tracking-wider text-fulkro-ink-500"
          style={{ left: `${m.pct}%`, transform: "translateX(-50%)" }}
        >
          {m.label}
        </div>
      ))}
    </div>
  );
}

function TaskBar({
  task,
  pctFromDate,
}: {
  task: TimelineTask;
  pctFromDate: (iso: string | null) => number;
}) {
  const startPct = pctFromDate(task.start_date);
  const endPct = pctFromDate(task.end_date);
  const widthPct = Math.max(1, endPct - startPct);
  const fillClass =
    task.status && STATUS_COLOR[task.status]
      ? STATUS_COLOR[task.status]
      : "fill-fulkro-ink-300";

  return (
    <div className="grid grid-cols-12 items-center gap-2 text-[11px]">
      <div className="col-span-3 truncate" title={task.task_name}>
        <span className="font-mono text-[10px] text-fulkro-ink-500">
          {task.task_code}
        </span>
        <span className="ml-1 text-fulkro-ink-700">{task.task_name}</span>
      </div>
      <div className="relative col-span-9 h-5">
        <svg className="absolute inset-0 h-full w-full overflow-visible">
          <rect
            x={`${startPct}%`}
            width={`${widthPct}%`}
            y={3}
            height={14}
            rx={2}
            className={`${fillClass} ${
              task.is_critical_path ? "stroke-red-500" : ""
            }`}
            strokeWidth={task.is_critical_path ? 1.5 : 0}
          />
          {task.progress_pct > 0 && task.progress_pct < 100 ? (
            <rect
              x={`${startPct}%`}
              width={`${widthPct * (task.progress_pct / 100)}%`}
              y={3}
              height={14}
              rx={2}
              className="fill-emerald-600 opacity-50"
            />
          ) : null}
        </svg>
      </div>
    </div>
  );
}

function MilestoneRow({
  milestones,
  pctFromDate,
}: {
  milestones: TimelineMilestone[];
  pctFromDate: (iso: string | null) => number;
}) {
  return (
    <div className="grid grid-cols-12 items-center gap-2 pt-1">
      <div className="col-span-3 text-[10px] font-medium uppercase tracking-wider text-fulkro-ink-500">
        Hitos
      </div>
      <div className="relative col-span-9 h-6">
        <svg className="absolute inset-0 h-full w-full overflow-visible">
          {milestones
            .filter((m) => m.date)
            .map((m, i) => {
              const pct = pctFromDate(m.date);
              const colorClass = MILESTONE_COLOR[m.type] ?? "text-fulkro-ink-700";
              return (
                <g key={`${m.name}-${i}`}>
                  <polygon
                    points="0,-6 6,0 0,6 -6,0"
                    transform={`translate(${pct}%, 12)`}
                    className={`fill-current ${colorClass}`}
                  >
                    <title>{`${m.name} · ${m.date}`}</title>
                  </polygon>
                </g>
              );
            })}
        </svg>
      </div>
    </div>
  );
}

function computeMonthMarkers(start: Date, end: Date): { label: string; pct: number }[] {
  const totalMs = end.getTime() - start.getTime();
  if (totalMs <= 0) return [];
  const out: { label: string; pct: number }[] = [];
  const cur = new Date(start.getFullYear(), start.getMonth(), 1);
  while (cur <= end) {
    const pct = ((cur.getTime() - start.getTime()) / totalMs) * 100;
    if (pct >= 0 && pct <= 100) {
      out.push({
        label: cur.toLocaleDateString("es-ES", { month: "short" }),
        pct,
      });
    }
    cur.setMonth(cur.getMonth() + 1);
  }
  return out;
}
