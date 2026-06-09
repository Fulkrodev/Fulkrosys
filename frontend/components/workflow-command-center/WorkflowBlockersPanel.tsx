/**
 * WorkflowBlockersPanel · admin blockers vista cross-actor (1.D.G.D v3.11).
 *
 * Agrupa steps por dependency_status + primary_actor:
 *   🟢 Available · puedes ejecutar AHORA
 *   🟡 Waiting cliente · "Esperando cliente firme E-012 · 1 día pendiente"
 *   ⚫ Blocked · prereqs pendientes (cascading)
 *   ✅ Done · completados (collapsed default · cuenta)
 *
 * Acciones:
 *   - "Recordar al cliente" botón → POST /admin/.../steps/{id}/remind
 *
 * R30 sostener · admin asume cero ENS · explica blocker primer-principios.
 */
"use client";

import * as React from "react";
import {
  AlertCircle,
  Bell,
  CheckCircle2,
  Clock,
  Loader2,
  Pause,
} from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import {
  remindClientStep,
  type EnrichedStepState,
} from "@/lib/api/workflow-command-center";

export interface WorkflowBlockersPanelProps {
  projectId: string;
  steps: EnrichedStepState[];
  onOpenDetail?: (step: EnrichedStepState) => void;
}

type GroupKey = "available" | "waiting_cliente" | "blocked" | "done";

interface Grouped {
  available: EnrichedStepState[];
  waiting_cliente: EnrichedStepState[];
  blocked: EnrichedStepState[];
  done: EnrichedStepState[];
}

function groupSteps(steps: EnrichedStepState[]): Grouped {
  const groups: Grouped = {
    available: [],
    waiting_cliente: [],
    blocked: [],
    done: [],
  };
  for (const step of steps) {
    const status = step.dependency_status ?? step.status;
    const actor = step.primary_actor ?? "admin";
    if (status === "done" || step.status === "completed") {
      groups.done.push(step);
      continue;
    }
    if (status === "in_progress" && actor === "cliente") {
      groups.waiting_cliente.push(step);
      continue;
    }
    if (status === "blocked") {
      groups.blocked.push(step);
      continue;
    }
    if (actor === "cliente" && status === "available") {
      groups.waiting_cliente.push(step);
      continue;
    }
    groups.available.push(step);
  }
  return groups;
}

export function WorkflowBlockersPanel({
  projectId,
  steps,
  onOpenDetail,
}: WorkflowBlockersPanelProps) {
  const groups = React.useMemo(() => groupSteps(steps), [steps]);

  return (
    <div className="space-y-4" data-testid="workflow-blockers-panel">
      <BlockersHeader groups={groups} />

      <BlockersSection
        groupKey="available"
        title="🟢 Puedes ejecutar ahora"
        steps={groups.available}
        onOpenDetail={onOpenDetail}
        projectId={projectId}
        emptyText="Sin pasos disponibles. Marcos espera turno del cliente o ya está al día."
      />

      <BlockersSection
        groupKey="waiting_cliente"
        title="🟡 Esperando cliente"
        steps={groups.waiting_cliente}
        onOpenDetail={onOpenDetail}
        projectId={projectId}
        emptyText="Sin pasos pendientes del cliente."
      />

      <BlockersSection
        groupKey="blocked"
        title="⚫ Bloqueados por prerequisitos"
        steps={groups.blocked}
        onOpenDetail={onOpenDetail}
        projectId={projectId}
        emptyText="Sin pasos bloqueados."
      />

      <BlockersSection
        groupKey="done"
        title="✅ Completados"
        steps={groups.done}
        onOpenDetail={onOpenDetail}
        projectId={projectId}
        defaultCollapsed
        emptyText="Sin completados aún."
      />
    </div>
  );
}

function BlockersHeader({ groups }: { groups: Grouped }) {
  return (
    <div
      className="grid grid-cols-2 sm:grid-cols-4 gap-3"
      data-testid="blockers-summary"
    >
      <KpiCard
        label="Puedes ejecutar"
        count={groups.available.length}
        Icon={CheckCircle2}
        tone="emerald"
      />
      <KpiCard
        label="Esperando cliente"
        count={groups.waiting_cliente.length}
        Icon={Clock}
        tone="amber"
        testid="kpi-waiting-cliente"
      />
      <KpiCard
        label="Bloqueados"
        count={groups.blocked.length}
        Icon={Pause}
        tone="slate"
        testid="kpi-blocked"
      />
      <KpiCard
        label="Completados"
        count={groups.done.length}
        Icon={CheckCircle2}
        tone="muted"
      />
    </div>
  );
}

function KpiCard({
  label,
  count,
  Icon,
  tone,
  testid,
}: {
  label: string;
  count: number;
  Icon: React.ElementType;
  tone: "emerald" | "amber" | "slate" | "muted";
  testid?: string;
}) {
  const toneClasses = {
    emerald: "text-emerald-700",
    amber: "text-amber-600",
    slate: "text-slate-600",
    muted: "text-muted-foreground",
  }[tone];
  return (
    <Card data-testid={testid}>
      <CardContent className="pt-4 pb-4 px-4 flex items-center gap-3">
        <Icon className={`size-5 ${toneClasses}`} />
        <div className="min-w-0">
          <div className="text-2xl font-bold leading-none">{count}</div>
          <div className="text-xs text-muted-foreground mt-1 truncate">
            {label}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface BlockersSectionProps {
  groupKey: GroupKey;
  title: string;
  steps: EnrichedStepState[];
  projectId: string;
  onOpenDetail?: (step: EnrichedStepState) => void;
  defaultCollapsed?: boolean;
  emptyText: string;
}

function BlockersSection({
  groupKey,
  title,
  steps,
  projectId,
  onOpenDetail,
  defaultCollapsed = false,
  emptyText,
}: BlockersSectionProps) {
  const [expanded, setExpanded] = React.useState(!defaultCollapsed);
  return (
    <Card data-testid={`blockers-section-${groupKey}`}>
      <CardHeader
        className="cursor-pointer pb-2"
        onClick={() => setExpanded((x) => !x)}
      >
        <CardTitle className="text-sm flex items-center justify-between">
          <span>{title}</span>
          <Badge variant="outline">{steps.length}</Badge>
        </CardTitle>
      </CardHeader>
      {expanded && (
        <CardContent className="space-y-2 pt-0">
          {steps.length === 0 ? (
            <p className="text-xs italic text-muted-foreground py-2">
              {emptyText}
            </p>
          ) : (
            steps.map((step) => (
              <BlockerCard
                key={step.template_id}
                step={step}
                projectId={projectId}
                groupKey={groupKey}
                onOpenDetail={onOpenDetail}
              />
            ))
          )}
        </CardContent>
      )}
    </Card>
  );
}

interface BlockerCardProps {
  step: EnrichedStepState;
  projectId: string;
  groupKey: GroupKey;
  onOpenDetail?: (step: EnrichedStepState) => void;
}

function BlockerCard({
  step,
  projectId,
  groupKey,
  onOpenDetail,
}: BlockerCardProps) {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = React.useState<string | null>(null);

  const remindMutation = useMutation({
    mutationFn: () => remindClientStep(projectId, step.template_id),
    onSuccess: (data) => {
      setFeedback(data.message);
      queryClient.invalidateQueries({
        queryKey: ["project-cronologica", projectId],
      });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al recordar";
      setFeedback(msg);
    },
  });

  const daysPending = computeDaysPending(step);
  const showRemind = groupKey === "waiting_cliente";

  return (
    <div
      className="rounded border p-3 hover:bg-muted/30 transition"
      data-testid={`blocker-card-${step.template_id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <button
            type="button"
            onClick={() => onOpenDetail?.(step)}
            className="text-left text-sm font-medium hover:underline"
            data-testid={`blocker-title-${step.template_id}`}
          >
            {step.title}
          </button>
          {step.blocked_reason && (
            <p
              className="text-xs text-muted-foreground mt-1 flex items-start gap-1"
              data-testid={`blocker-reason-${step.template_id}`}
            >
              <AlertCircle className="size-3 mt-0.5 flex-shrink-0" />
              {step.blocked_reason}
            </p>
          )}
          {daysPending !== null && (
            <p className="text-[11px] text-muted-foreground mt-1">
              {daysPending} día{daysPending === 1 ? "" : "s"} pendiente
            </p>
          )}
        </div>

        {showRemind && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => remindMutation.mutate()}
            disabled={remindMutation.isPending}
            data-testid={`remind-button-${step.template_id}`}
          >
            {remindMutation.isPending ? (
              <Loader2 className="size-3 animate-spin" />
            ) : (
              <Bell className="size-3 mr-1" />
            )}
            Recordar
          </Button>
        )}
      </div>
      {feedback && (
        <p
          className="text-xs text-emerald-700 mt-2"
          data-testid={`remind-feedback-${step.template_id}`}
        >
          {feedback}
        </p>
      )}
    </div>
  );
}

function computeDaysPending(step: EnrichedStepState): number | null {
  if (!step.started_at_iso) return null;
  const started = new Date(step.started_at_iso).getTime();
  const days = Math.floor((Date.now() - started) / (1000 * 60 * 60 * 24));
  return days >= 0 ? days : null;
}
