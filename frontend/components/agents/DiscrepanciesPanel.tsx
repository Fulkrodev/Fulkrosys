/**
 * DiscrepanciesPanel · A21 Detector vista cliente (MB-8.A.3).
 *
 * Backend: /api/v1/projects/{id}/a21/* (4 endpoints).
 * Vista combina scan trigger + lista de discrepancias + resolve flow.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  agent21Api,
  type DiscrepancyOut,
  type DiscrepancySeverity,
  type ResolutionStatus,
  type ScanRunOut,
} from "@/lib/api/agent-21";

const SEVERITY_TONE: Record<DiscrepancySeverity, string> = {
  critical: "bg-red-100 text-red-900 border-red-300",
  high: "bg-orange-100 text-orange-900 border-orange-300",
  medium: "bg-amber-100 text-amber-900 border-amber-300",
  low: "bg-fulkro-ink-100 text-fulkro-ink-700 border-fulkro-ink-300",
};

const STATUS_TONE: Record<ResolutionStatus, string> = {
  open: "bg-amber-100 text-amber-900 border-amber-300",
  acknowledged: "bg-blue-100 text-blue-900 border-blue-300",
  resolved: "bg-emerald-100 text-emerald-900 border-emerald-300",
  dismissed: "bg-fulkro-ink-100 text-fulkro-ink-700 border-fulkro-ink-300",
};

export function DiscrepanciesPanel({ projectId }: { projectId: string }) {
  const qc = useQueryClient();

  const lastScans = useQuery<ScanRunOut[]>({
    queryKey: ["a21", "scans", projectId],
    queryFn: () => agent21Api.listScans(projectId, 5),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const discrepancies = useQuery<DiscrepancyOut[]>({
    queryKey: ["a21", "discrepancies", projectId],
    queryFn: () => agent21Api.listDiscrepancies(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const scanMutation = useMutation({
    mutationFn: () => agent21Api.triggerScan(projectId),
    onSuccess: (run) => {
      toast.success(
        `Scan ${run.run_status} · ${run.discrepancies_found} discrepancias detectadas`,
      );
      void qc.invalidateQueries({ queryKey: ["a21", "scans", projectId] });
      void qc.invalidateQueries({
        queryKey: ["a21", "discrepancies", projectId],
      });
    },
    onError: (err) => {
      toast.error("Scan falló", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const lastRun = lastScans.data?.[0] ?? null;
  const openCount = (discrepancies.data ?? []).filter(
    (d) => d.resolution_status === "open",
  ).length;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-2 text-base">
            <span className="flex items-center gap-2">
              <ShieldAlert size={16} /> Detector de discrepancias (A21)
            </span>
            <Button
              size="sm"
              onClick={() => scanMutation.mutate()}
              disabled={scanMutation.isPending}
            >
              {scanMutation.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <RefreshCw size={14} />
              )}
              Escanear ahora
            </Button>
          </CardTitle>
          <p className="mt-1 text-xs text-fulkro-ink-500">
            Detector cross-motor (M02 ↔ M03 ↔ M07) · NC potenciales para
            auditoría ENS
          </p>
        </CardHeader>
        <CardContent>
          <LastScanBlock run={lastRun} pending={scanMutation.isPending} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-2 text-sm">
            <span>Discrepancias detectadas</span>
            <Badge variant={openCount > 0 ? "warning" : "secondary"}>
              {openCount} abiertas
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {discrepancies.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : discrepancies.isError ? (
            <Alert variant="danger">
              <AlertTitle>No se pudo cargar</AlertTitle>
              <AlertDescription>
                {discrepancies.error instanceof Error
                  ? discrepancies.error.message
                  : "Error desconocido"}
              </AlertDescription>
            </Alert>
          ) : !discrepancies.data || discrepancies.data.length === 0 ? (
            <EmptyState
              title="Sin discrepancias detectadas"
              description="Ejecuta un escaneo para detectar incoherencias cross-motor."
            />
          ) : (
            <ul className="space-y-2">
              {discrepancies.data.map((d) => (
                <DiscrepancyRow
                  key={d.id}
                  discrepancy={d}
                  projectId={projectId}
                />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function LastScanBlock({
  run,
  pending,
}: {
  run: ScanRunOut | null;
  pending: boolean;
}) {
  if (pending) {
    return (
      <div className="flex items-center gap-2 text-sm text-fulkro-ink-500">
        <Loader2 size={14} className="animate-spin" /> escaneando…
      </div>
    );
  }
  if (!run) {
    return (
      <p className="text-xs text-fulkro-ink-500">
        Sin scans previos. Ejecuta el primer escaneo.
      </p>
    );
  }
  const statusColor =
    run.run_status === "completed"
      ? "text-emerald-700"
      : run.run_status === "running"
      ? "text-blue-700"
      : run.run_status === "failed"
      ? "text-red-700"
      : "text-fulkro-ink-700";
  return (
    <div className="grid grid-cols-2 gap-y-1 text-xs sm:grid-cols-4">
      <span className="text-fulkro-ink-500">Último scan</span>
      <span className={`font-medium ${statusColor}`}>{run.run_status}</span>
      <span className="text-fulkro-ink-500">Discrepancias</span>
      <span className="font-mono">{run.discrepancies_found}</span>
      <span className="text-fulkro-ink-500">Motors</span>
      <span className="font-mono text-[11px]">
        {run.motors_scanned.join(", ") || "—"}
      </span>
      <span className="text-fulkro-ink-500">Completado</span>
      <span>
        {run.completed_at
          ? new Date(run.completed_at).toLocaleString()
          : "—"}
      </span>
    </div>
  );
}

function DiscrepancyRow({
  discrepancy,
  projectId,
}: {
  discrepancy: DiscrepancyOut;
  projectId: string;
}) {
  const [resolveOpen, setResolveOpen] = React.useState(false);
  const [pendingStatus, setPendingStatus] = React.useState<ResolutionStatus | null>(
    null,
  );
  const [notes, setNotes] = React.useState("");
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      agent21Api.resolve(projectId, discrepancy.id, {
        new_status: pendingStatus ?? "acknowledged",
        notes: notes.trim() || null,
      }),
    onSuccess: (updated) => {
      toast.success(`Discrepancia ${updated.resolution_status}`);
      setResolveOpen(false);
      setNotes("");
      void qc.invalidateQueries({
        queryKey: ["a21", "discrepancies", projectId],
      });
    },
    onError: (err) => {
      toast.error("No se pudo actualizar", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  function startResolve(status: ResolutionStatus) {
    setPendingStatus(status);
    setResolveOpen(true);
  }

  return (
    <li className="rounded-md border border-fulkro-ink-300/60 bg-white p-3 text-xs">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <Badge
              variant="outline"
              className={`font-mono ${SEVERITY_TONE[discrepancy.severity]}`}
            >
              {discrepancy.severity}
            </Badge>
            <Badge
              variant="outline"
              className={STATUS_TONE[discrepancy.resolution_status]}
            >
              {discrepancy.resolution_status}
            </Badge>
            <span className="font-mono text-[10px] text-fulkro-ink-500">
              {discrepancy.motor_a} ↔ {discrepancy.motor_b}
            </span>
          </div>
          <p className="mt-1.5 text-sm text-fulkro-ink-700">
            {discrepancy.description}
          </p>
          {discrepancy.resolution_notes ? (
            <p className="mt-1 text-[11px] italic text-fulkro-ink-500">
              Resolución: {discrepancy.resolution_notes}
            </p>
          ) : null}
        </div>
      </div>
      {discrepancy.resolution_status === "open" ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Button
            size="sm"
            variant="outline"
            onClick={() => startResolve("acknowledged")}
          >
            <AlertTriangle size={12} /> Acknowledge
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => startResolve("resolved")}
          >
            <CheckCircle2 size={12} /> Resuelta
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => startResolve("dismissed")}
          >
            <XCircle size={12} /> Dismiss (no aplica)
          </Button>
        </div>
      ) : null}

      <Dialog open={resolveOpen} onOpenChange={setResolveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Cambiar estado a {pendingStatus ?? ""}
            </DialogTitle>
            <DialogDescription>
              Añade nota explicativa (opcional pero recomendada para audit log).
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="Ej: revisado en reunión 2026-05-08 con RSEG · acción XYZ ejecutada"
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setResolveOpen(false)}
              disabled={mutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
            >
              {mutation.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : null}
              Confirmar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </li>
  );
}
