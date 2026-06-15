"use client";

/**
 * /admin/compliance/monitor · FULKRO Self-Monitoring System dashboard
 * (MB-9.bis atom 9.bis.6).
 *
 * Sections:
 * - Status cards (overall semaphore + counts green/yellow/red/unknown +
 *   open alerts + last run / last report timestamps)
 * - Checks table (17 named checks · filter by status · manual trigger)
 * - Alerts table (latest 100 · filter open/resolved · manual resolve)
 * - Reports list (recent weekly/monthly artifacts · download link)
 *
 * Polling: status + alerts refresh every 60s (passive). Manual `Sync
 * registry` button upserts CHECK_REGISTRY rows after backend code change.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  Download,
  Loader2,
  PlayCircle,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";

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
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  getMonitorStatus,
  listAlerts,
  listChecks,
  listReports,
  resolveAlert,
  runCheck,
  syncRegistry,
} from "@/lib/admin-compliance-monitor/api";
import type {
  CheckStatus,
  ComplianceAlert,
  ComplianceCheck,
} from "@/lib/admin-compliance-monitor/schemas";
import { cn } from "@/lib/utils";

const STATUS_LABEL: Record<CheckStatus, string> = {
  green: "OK",
  yellow: "Atención",
  red: "Crítico",
  unknown: "Sin datos",
};

const STATUS_CHIP: Record<CheckStatus, string> = {
  green: "bg-emerald-100 text-emerald-800 border-emerald-200",
  yellow: "bg-amber-100 text-amber-800 border-amber-200",
  red: "bg-red-100 text-red-800 border-red-200",
  unknown: "bg-fulkro-ink-100 text-fulkro-ink-700 border-fulkro-ink-200",
};

function StatusChip({ status }: { status: CheckStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium",
        STATUS_CHIP[status],
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}

function formatTs(ts: string | null): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

export default function ComplianceMonitorPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<CheckStatus | "all">("all");
  const [alertFilter, setAlertFilter] = useState<"open" | "resolved" | "all">("open");
  // J#3 · resolver alerta vía Dialog (sustituye window.prompt · a11y + marca)
  const [resolveTarget, setResolveTarget] = useState<string | null>(null);
  const [resolveNote, setResolveNote] = useState("");

  const statusQuery = useQuery({
    queryKey: ["compliance", "status"],
    queryFn: getMonitorStatus,
    refetchInterval: 60_000,
  });
  const checksQuery = useQuery({
    queryKey: ["compliance", "checks", statusFilter],
    queryFn: () =>
      listChecks(
        statusFilter !== "all" ? { status: statusFilter } : undefined,
      ),
    refetchInterval: 60_000,
  });
  const alertsQuery = useQuery({
    queryKey: ["compliance", "alerts", alertFilter],
    queryFn: () =>
      listAlerts(
        alertFilter !== "all" ? { status: alertFilter, limit: 100 } : { limit: 100 },
      ),
    refetchInterval: 60_000,
  });
  const reportsQuery = useQuery({
    queryKey: ["compliance", "reports"],
    queryFn: () => listReports(10),
  });

  const triggerMutation = useMutation({
    mutationFn: runCheck,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance"] });
    },
  });
  const resolveMutation = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) =>
      resolveAlert(id, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance"] });
      setResolveTarget(null);
      setResolveNote("");
    },
  });
  const syncMutation = useMutation({
    mutationFn: syncRegistry,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance"] });
    },
  });

  const s = statusQuery.data;
  const checks = checksQuery.data ?? [];
  const alerts = alertsQuery.data ?? [];
  const reports = reportsQuery.data ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <ShieldCheck className="h-6 w-6" />
            Compliance Monitor
          </h1>
          <p className="mt-1 text-sm text-fulkro-ink-600">
            Verificación automática RGPD · LOPDGDD · LSSI-CE · NIS2 · ISO
            27001 — 17 checks en cadencias diaria/semanal/mensual/trimestral.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          <RefreshCw
            className={cn(
              "mr-2 h-4 w-4",
              syncMutation.isPending && "animate-spin",
            )}
          />
          Sync registry
        </Button>
      </header>

      {/* Status cards */}
      <section className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
        {statusQuery.isLoading || !s ? (
          [...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))
        ) : (
          <>
            <StatusCard label="Estado global" value={STATUS_LABEL[s.overall]} status={s.overall} />
            <StatusCard label="OK" value={String(s.green)} status="green" />
            <StatusCard label="Atención" value={String(s.yellow)} status="yellow" />
            <StatusCard label="Crítico" value={String(s.red)} status="red" />
            <StatusCard label="Sin datos" value={String(s.unknown)} status="unknown" />
            <StatusCard label="Alertas abiertas" value={String(s.open_alerts)} status={s.open_alerts > 0 ? "yellow" : "green"} />
          </>
        )}
      </section>

      <section className="text-xs text-fulkro-ink-500">
        Último run: {formatTs(s?.last_run_at ?? null)} ·
        Último reporte: {formatTs(s?.last_report_at ?? null)}
      </section>

      {/* Checks table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-lg">Checks ({checks.length})</CardTitle>
          <div className="flex gap-2">
            {(["all", "green", "yellow", "red", "unknown"] as const).map((f) => (
              <Button
                key={f}
                size="sm"
                variant={statusFilter === f ? "primary" : "outline"}
                onClick={() => setStatusFilter(f)}
              >
                {f === "all" ? "Todos" : STATUS_LABEL[f]}
              </Button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {checksQuery.isLoading ? (
            <div className="p-6">
              <Skeleton className="h-32 w-full" />
            </div>
          ) : (
            <ChecksTable
              checks={checks}
              onTrigger={(name) => triggerMutation.mutate(name)}
              triggeringName={triggerMutation.isPending ? triggerMutation.variables : null}
            />
          )}
        </CardContent>
      </Card>

      {/* Alerts */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-lg">
            Alertas ({alerts.length})
          </CardTitle>
          <div className="flex gap-2">
            {(["open", "resolved", "all"] as const).map((f) => (
              <Button
                key={f}
                size="sm"
                variant={alertFilter === f ? "primary" : "outline"}
                onClick={() => setAlertFilter(f)}
              >
                {f === "open" ? "Abiertas" : f === "resolved" ? "Resueltas" : "Todas"}
              </Button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {alertsQuery.isLoading ? (
            <div className="p-6">
              <Skeleton className="h-32 w-full" />
            </div>
          ) : alerts.length === 0 ? (
            <div className="flex items-center gap-2 p-6 text-sm text-emerald-700">
              <CheckCircle2 className="h-4 w-4" />
              Sin alertas {alertFilter === "open" ? "abiertas" : "del filtro"}.
            </div>
          ) : (
            <AlertsTable
              alerts={alerts}
              onResolve={(id) => {
                setResolveNote("");
                setResolveTarget(id);
              }}
              resolvingId={
                resolveMutation.isPending ? resolveMutation.variables?.id ?? null : null
              }
            />
          )}
        </CardContent>
      </Card>

      {/* Reports */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            Reportes recientes ({reports.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {reports.length === 0 ? (
            <p className="text-sm text-fulkro-ink-500">
              Aún sin reportes generados. El primer reporte semanal se genera
              el próximo lunes 08:00.
            </p>
          ) : (
            <ul className="divide-y">
              {reports.map((r) => (
                <li
                  key={r.id}
                  className="flex items-center justify-between py-2 text-sm"
                >
                  <div>
                    <div className="font-medium">{r.report_type}</div>
                    <div className="text-xs text-fulkro-ink-500">
                      {formatTs(r.period_start)} → {formatTs(r.period_end)} ·
                      modo: <span className="font-mono">{r.storage_mode}</span>
                    </div>
                  </div>
                  {r.signed_url ? (
                    <a
                      className="inline-flex items-center gap-1 text-blue-600 hover:underline"
                      href={r.signed_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <Download className="h-4 w-4" />
                      Descargar
                    </a>
                  ) : r.storage_path ? (
                    <span className="font-mono text-xs text-fulkro-ink-500">
                      {r.storage_path}
                    </span>
                  ) : (
                    <span className="text-xs text-fulkro-ink-400">inline</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* J#3 · Dialog de resolución de alerta (sustituye window.prompt) */}
      <Dialog
        open={resolveTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setResolveTarget(null);
            setResolveNote("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resolver alerta de cumplimiento</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <label htmlFor="resolve-note" className="text-sm font-medium">
              Nota de resolución
            </label>
            <Textarea
              id="resolve-note"
              value={resolveNote}
              onChange={(e) => setResolveNote(e.target.value)}
              placeholder="Describe brevemente cómo se resolvió la alerta…"
              rows={4}
              aria-label="Nota de resolución de la alerta"
            />
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => {
                setResolveTarget(null);
                setResolveNote("");
              }}
            >
              Cancelar
            </Button>
            <Button
              disabled={!resolveNote.trim() || resolveMutation.isPending}
              onClick={() => {
                if (resolveTarget && resolveNote.trim()) {
                  resolveMutation.mutate({
                    id: resolveTarget,
                    note: resolveNote.trim(),
                  });
                }
              }}
            >
              {resolveMutation.isPending ? "Resolviendo…" : "Resolver"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatusCard({
  label,
  value,
  status,
}: {
  label: string;
  value: string;
  status: CheckStatus;
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="text-xs uppercase tracking-wide text-fulkro-ink-500">
          {label}
        </div>
        <div className="mt-1 flex items-baseline gap-2">
          <span className="text-2xl font-semibold">{value}</span>
          <StatusChip status={status} />
        </div>
      </CardContent>
    </Card>
  );
}

function ChecksTable({
  checks,
  onTrigger,
  triggeringName,
}: {
  checks: ComplianceCheck[];
  onTrigger: (name: string) => void;
  triggeringName: string | null;
}) {
  if (checks.length === 0) {
    return (
      <div className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
        <CircleHelp className="h-4 w-4" />
        Sin checks para el filtro actual. Pulsa “Sync registry” si has
        actualizado el código backend.
      </div>
    );
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-xs uppercase tracking-wide text-fulkro-ink-500">
          <th className="px-4 py-2">Check</th>
          <th className="px-4 py-2">Categoría</th>
          <th className="px-4 py-2">Cadencia</th>
          <th className="px-4 py-2">Estado</th>
          <th className="px-4 py-2">Último run</th>
          <th className="px-4 py-2">Mensaje</th>
          <th className="px-4 py-2"></th>
        </tr>
      </thead>
      <tbody>
        {checks.map((c) => (
          <tr key={c.id} className="border-b last:border-0">
            <td className="px-4 py-2 font-mono text-xs">{c.check_name}</td>
            <td className="px-4 py-2 text-xs">{c.category}</td>
            <td className="px-4 py-2 text-xs">{c.frequency}</td>
            <td className="px-4 py-2">
              <StatusChip status={c.status} />
            </td>
            <td className="px-4 py-2 text-xs text-fulkro-ink-600">
              {formatTs(c.last_run_at)}
            </td>
            <td className="max-w-md truncate px-4 py-2 text-xs text-fulkro-ink-600">
              {c.last_result?.message ?? c.description ?? "—"}
            </td>
            <td className="px-4 py-2">
              <Button
                size="sm"
                variant="ghost"
                disabled={triggeringName === c.check_name}
                onClick={() => onTrigger(c.check_name)}
              >
                {triggeringName === c.check_name ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <PlayCircle className="h-4 w-4" />
                )}
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function AlertsTable({
  alerts,
  onResolve,
  resolvingId,
}: {
  alerts: ComplianceAlert[];
  onResolve: (id: string) => void;
  resolvingId: string | null;
}) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-xs uppercase tracking-wide text-fulkro-ink-500">
          <th className="px-4 py-2">Check</th>
          <th className="px-4 py-2">Severidad</th>
          <th className="px-4 py-2">Estado</th>
          <th className="px-4 py-2">Activada</th>
          <th className="px-4 py-2">Mensaje</th>
          <th className="px-4 py-2"></th>
        </tr>
      </thead>
      <tbody>
        {alerts.map((a) => (
          <tr key={a.id} className="border-b last:border-0">
            <td className="px-4 py-2 font-mono text-xs">{a.check_name}</td>
            <td className="px-4 py-2">
              <Badge variant={a.severity === "high" ? "danger" : "outline"}>
                {a.severity}
              </Badge>
            </td>
            <td className="px-4 py-2">
              {a.status === "resolved" ? (
                <span className="inline-flex items-center gap-1 text-xs text-emerald-700">
                  <CheckCircle2 className="h-3 w-3" /> Resuelta
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs text-amber-700">
                  <AlertTriangle className="h-3 w-3" /> Abierta
                </span>
              )}
            </td>
            <td className="px-4 py-2 text-xs text-fulkro-ink-600">
              {formatTs(a.triggered_at)}
            </td>
            <td className="max-w-md truncate px-4 py-2 text-xs text-fulkro-ink-600">
              {a.message}
            </td>
            <td className="px-4 py-2">
              {a.status === "open" ? (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={resolvingId === a.id}
                  onClick={() => onResolve(a.id)}
                >
                  {resolvingId === a.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Resolver"
                  )}
                </Button>
              ) : null}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
