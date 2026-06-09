"use client";

/**
 * ClientTaskCard · render individual task con CTA + lifecycle actions
 * (ADR-038 SAN-D MB-14.4).
 *
 * Coherencia visual ADR-035 + TRAD-9 ADR-036:
 * - shadcn Card · Badge · Button composition
 * - fulkro palette (success/warning/danger/info)
 * - lucide-react icons
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  CheckCircle2,
  Circle,
  Clock,
  Loader2,
  PauseCircle,
  PlayCircle,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ClientTask,
  ClientTaskStatus,
  clientTasksApi,
} from "@/lib/api/client-portal-tasks";
import { cn } from "@/lib/utils";

interface Props {
  task: ClientTask;
}

const STATUS_VARIANT: Record<
  ClientTaskStatus,
  "success" | "info" | "warning" | "secondary"
> = {
  pending: "secondary",
  in_progress: "info",
  blocked: "warning",
  done: "success",
};

const STATUS_LABEL: Record<ClientTaskStatus, string> = {
  pending: "Pendiente",
  in_progress: "En curso",
  blocked: "Bloqueada",
  done: "Completada",
};

const STATUS_BORDER: Record<ClientTaskStatus, string> = {
  pending: "border-l-fulkro-ink-300",
  in_progress: "border-l-fulkro-info",
  blocked: "border-l-fulkro-warning",
  done: "border-l-fulkro-success",
};

export function ClientTaskCard({ task }: Props) {
  const queryClient = useQueryClient();
  const [blockReason, setBlockReason] = useState("");
  const [blockOpen, setBlockOpen] = useState(false);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["client-tasks"] });

  const startMutation = useMutation({
    mutationFn: () => clientTasksApi.start(task.id),
    onSuccess: invalidate,
  });
  const completeMutation = useMutation({
    mutationFn: () => clientTasksApi.complete(task.id),
    onSuccess: invalidate,
  });
  const blockMutation = useMutation({
    mutationFn: () => clientTasksApi.block(task.id, blockReason),
    onSuccess: () => {
      invalidate();
      setBlockOpen(false);
      setBlockReason("");
    },
  });
  // #27 Ola 6 · aprobación explícita del Plan de Adecuación (audit_log + SSE).
  const approveMutation = useMutation({
    mutationFn: () => clientTasksApi.approvePlan(task.id),
    onSuccess: invalidate,
  });

  // PHASE5_*_APPROVE_PDA → la "Completar" genérica se sustituye por "Aprobar
  // Plan" (acción discreta + traza ENAC). El resto de tareas no cambia.
  const isApprovePlan = (task.template_id ?? "").includes("APPROVE_PDA");

  const isBusy =
    startMutation.isPending ||
    completeMutation.isPending ||
    blockMutation.isPending ||
    approveMutation.isPending;

  return (
    <Card className={cn("border-l-4", STATUS_BORDER[task.status])}>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <CardTitle className="flex items-start gap-2 text-base">
            {task.status === "done" ? (
              <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-fulkro-success" strokeWidth={2.3} />
            ) : task.status === "in_progress" ? (
              <Clock className="mt-0.5 h-5 w-5 shrink-0 text-fulkro-info" strokeWidth={2.3} />
            ) : task.status === "blocked" ? (
              <PauseCircle className="mt-0.5 h-5 w-5 shrink-0 text-fulkro-warning" strokeWidth={2.3} />
            ) : (
              <Circle className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" strokeWidth={2.3} />
            )}
            {task.title}
          </CardTitle>
          <Badge variant={STATUS_VARIANT[task.status]}>
            {STATUS_LABEL[task.status]}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {task.description && (
          <p className="text-sm text-muted-foreground whitespace-pre-line">
            {task.description}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="outline" className="font-mono">
            {task.template_id}
          </Badge>
          <Badge variant="outline">Fase: {task.phase}</Badge>
          {task.due_date && (
            <span>
              Vence:{" "}
              <strong>{new Date(task.due_date).toLocaleDateString("es")}</strong>
            </span>
          )}
        </div>

        {task.blocked_reason && (
          <div className="rounded-md bg-fulkro-warning/10 p-2 text-xs text-fulkro-warning">
            <strong>Motivo bloqueo:</strong> {task.blocked_reason}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          {/* #25 Ola 6 · si la CTA apunta a /admin la tarea la opera Fulkro:
              NO pintamos un botón roto (el cliente no puede abrir /admin).
              Mantenemos la tarjeta visible (transparencia) con nota R29. */}
          {task.cta_url &&
            task.status !== "done" &&
            (task.cta_url.startsWith("/admin") ? (
              <span
                className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2.5 py-1 text-xs text-muted-foreground"
                data-testid="client-task-admin-managed"
              >
                <ShieldCheck className="h-3 w-3" strokeWidth={2.3} />
                Lo gestiona Fulkro
              </span>
            ) : (
              <Link
                href={task.cta_url}
                className={cn(
                  buttonVariants({ variant: "outline", size: "sm" }),
                )}
              >
                {task.cta_label || "Ir"}
                <ArrowRight className="ml-1 h-3 w-3" strokeWidth={2.3} />
              </Link>
            ))}

          {isApprovePlan ? (
            task.status !== "done" && (
              <Button
                size="sm"
                variant="primary"
                onClick={() => approveMutation.mutate()}
                disabled={isBusy}
                data-testid="client-task-approve-plan"
              >
                {approveMutation.isPending ? (
                  <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                ) : (
                  <ShieldCheck className="mr-1 h-3 w-3" strokeWidth={2.3} />
                )}
                Aprobar Plan
              </Button>
            )
          ) : (
            <>
              {task.status === "pending" && (
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => startMutation.mutate()}
                  disabled={isBusy}
                >
                  {startMutation.isPending ? (
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                  ) : (
                    <PlayCircle className="mr-1 h-3 w-3" strokeWidth={2.3} />
                  )}
                  Empezar
                </Button>
              )}

              {(task.status === "pending" ||
                task.status === "in_progress") && (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => completeMutation.mutate()}
                  disabled={isBusy}
                >
                  {completeMutation.isPending ? (
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                  ) : (
                    <CheckCircle2 className="mr-1 h-3 w-3" strokeWidth={2.3} />
                  )}
                  Completar
                </Button>
              )}
            </>
          )}

          {task.status !== "done" && task.status !== "blocked" && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setBlockOpen((v) => !v)}
              disabled={isBusy}
            >
              <PauseCircle className="mr-1 h-3 w-3" strokeWidth={2.3} />
              Bloquear
            </Button>
          )}
        </div>

        {blockOpen && (
          <div className="space-y-2 rounded-md border bg-muted p-2">
            <textarea
              value={blockReason}
              onChange={(e) => setBlockReason(e.target.value)}
              placeholder="Motivo del bloqueo..."
              className="w-full rounded border bg-card p-2 text-sm"
              rows={3}
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="primary"
                onClick={() => blockMutation.mutate()}
                disabled={!blockReason.trim() || blockMutation.isPending}
              >
                {blockMutation.isPending ? (
                  <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                ) : null}
                Confirmar bloqueo
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setBlockOpen(false)}
              >
                Cancelar
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
