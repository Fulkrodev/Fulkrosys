/**
 * OperationsConsole · K.9 Admin global ops overview (MB-4.D.4).
 *
 * Backend: GET /api/v1/operations/overview composer M26 + M25 + M27.
 * Vista admin Marcos · NO project-scoped · ops cross-tenant.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Archive,
  CalendarClock,
  Database,
  HardDrive,
  Loader2,
  ShieldAlert,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { NotificationsDlqWidget } from "@/components/operations/NotificationsDlqWidget";
import { api } from "@/lib/api";

interface OperationsOverviewResponse {
  last_backup: {
    id: string;
    backup_type: string;
    started_at: string | null;
    completed_at: string | null;
    size_bytes: number | null;
    status: string;
  } | null;
  backup_counts_30d: {
    pending: number;
    running: number;
    completed: number;
    failed: number;
  };
  last_restore_test: {
    id: string;
    test_type: string;
    started_at: string | null;
    completed_at: string | null;
    status: string;
    rto_seconds: number | null;
  } | null;
  archivable_backups_count: number;
  archivable_total_size_bytes: number;
  grace_period_active_count: number;
  upcoming_renewals_90d: Array<{
    project_id: string;
    expiration_date: string;
    days_until: number;
    route_type: string | null;
  }>;
  generated_at: string;
}

const STATUS_TONE: Record<string, string> = {
  completed: "bg-emerald-100 text-emerald-900 border-emerald-300",
  running: "bg-blue-100 text-blue-900 border-blue-300",
  pending: "bg-fulkro-ink-100 text-fulkro-ink-700 border-fulkro-ink-300/60",
  failed: "bg-red-100 text-red-900 border-red-300",
};

export function OperationsConsole() {
  const { data, isLoading, isError, error } = useQuery<OperationsOverviewResponse>({
    queryKey: ["operations-overview"],
    queryFn: () =>
      api<OperationsOverviewResponse>("/api/v1/operations/overview"),
    staleTime: 60_000,
    retry: false,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" /> cargando operaciones…
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="danger">
            <AlertTitle>No se pudo cargar Operations</AlertTitle>
            <AlertDescription>
              {error instanceof Error ? error.message : "Error desconocido"}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Database size={16} /> Operaciones (Admin)
          </CardTitle>
          <p className="mt-1 text-xs text-fulkro-ink-500">
            M26 backups · M25 archivable · M27 renewals · vista cross-tenant
          </p>
        </CardHeader>
      </Card>

      <BackupHealthCard
        last={data.last_backup}
        counts={data.backup_counts_30d}
      />

      <RestoreTestCard last={data.last_restore_test} />

      <NotificationsDlqWidget />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Archive size={14} /> Archivos lifecycle (M25)
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-2 sm:grid-cols-2 text-xs">
          <Stat
            label="Backups archivados"
            value={String(data.archivable_backups_count)}
            meta={
              data.archivable_total_size_bytes > 0
                ? `${(data.archivable_total_size_bytes / (1024 * 1024)).toFixed(1)} MB`
                : null
            }
          />
          <Stat
            label="Grace period activa"
            value={String(data.grace_period_active_count)}
            tone={data.grace_period_active_count > 0 ? "warning" : "default"}
            meta="proyectos en cierre honesto"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <CalendarClock size={14} /> Renovaciones próximas (≤ 90 días)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data.upcoming_renewals_90d.length === 0 ? (
            <p className="text-xs text-fulkro-ink-500">
              Sin renewals próximas en los próximos 90 días.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {data.upcoming_renewals_90d.map((r) => (
                <li
                  key={`${r.project_id}-${r.expiration_date}`}
                  className="flex items-center justify-between gap-3 rounded-md border border-fulkro-ink-300/60 px-3 py-1.5 text-xs"
                >
                  <span className="flex flex-col gap-0.5">
                    <span className="font-mono text-[10px] text-fulkro-ink-500">
                      {r.project_id.slice(0, 8)}
                    </span>
                    {r.route_type ? (
                      <Badge variant="outline" className="w-fit text-[10px]">
                        {r.route_type}
                      </Badge>
                    ) : null}
                  </span>
                  <span className="flex flex-col items-end gap-0.5">
                    <span className="font-mono text-[11px] text-fulkro-ink-700">
                      {new Date(r.expiration_date).toLocaleDateString()}
                    </span>
                    <Badge
                      variant={r.days_until <= 30 ? "warning" : "secondary"}
                      className="text-[10px]"
                    >
                      {r.days_until} días
                    </Badge>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <p className="text-[10px] text-fulkro-ink-500">
        Datos generados {new Date(data.generated_at).toLocaleString()}
      </p>
    </div>
  );
}

function BackupHealthCard({
  last,
  counts,
}: {
  last: OperationsOverviewResponse["last_backup"];
  counts: OperationsOverviewResponse["backup_counts_30d"];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <HardDrive size={14} /> Backup health (M26)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {last ? (
          <div className="rounded-md border border-fulkro-ink-300/60 bg-white p-3 text-xs">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-fulkro-ink-700">
                Último backup · {last.backup_type}
              </span>
              <Badge
                variant="outline"
                className={STATUS_TONE[last.status] ?? ""}
              >
                {last.status}
              </Badge>
            </div>
            <p className="mt-1 font-mono text-[10px] text-fulkro-ink-500">
              {last.completed_at
                ? new Date(last.completed_at).toLocaleString()
                : last.started_at
                ? `iniciado ${new Date(last.started_at).toLocaleString()}`
                : "—"}
              {last.size_bytes
                ? ` · ${(last.size_bytes / (1024 * 1024)).toFixed(1)} MB`
                : ""}
            </p>
          </div>
        ) : (
          <p className="text-xs text-fulkro-ink-500">
            Sin backups registrados todavía.
          </p>
        )}
        <div className="grid grid-cols-2 gap-2 text-center sm:grid-cols-4 text-xs">
          <Stat label="Pending" value={String(counts.pending)} />
          <Stat label="Running" value={String(counts.running)} />
          <Stat
            label="Completed"
            value={String(counts.completed)}
            tone="success"
          />
          <Stat
            label="Failed"
            value={String(counts.failed)}
            tone={counts.failed > 0 ? "danger" : "default"}
          />
        </div>
        <p className="text-[10px] text-fulkro-ink-500">
          Counts últimos 30 días.
        </p>
      </CardContent>
    </Card>
  );
}

function RestoreTestCard({
  last,
}: {
  last: OperationsOverviewResponse["last_restore_test"];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <ShieldAlert size={14} /> Último restore test
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!last ? (
          <p className="text-xs text-fulkro-ink-500">
            Sin restore tests todavía.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 text-xs">
            <Stat label="Tipo" value={last.test_type} />
            <Stat
              label="Estado"
              value={last.status}
              tone={
                last.status === "completed"
                  ? "success"
                  : last.status === "failed"
                  ? "danger"
                  : "default"
              }
            />
            {last.completed_at ? (
              <Stat
                label="Completado"
                value={new Date(last.completed_at).toLocaleDateString()}
              />
            ) : null}
            {last.rto_seconds ? (
              <Stat label="RTO" value={`${last.rto_seconds} s`} />
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Stat({
  label,
  value,
  meta,
  tone = "default",
}: {
  label: string;
  value: string;
  meta?: string | null;
  tone?: "default" | "warning" | "danger" | "success";
}) {
  const toneCls =
    tone === "danger"
      ? "border-red-300 bg-red-50/50"
      : tone === "warning"
      ? "border-amber-300 bg-amber-50/50"
      : tone === "success"
      ? "border-emerald-300 bg-emerald-50/40"
      : "border-fulkro-ink-300/60 bg-white";
  return (
    <div className={`rounded-md border p-2.5 ${toneCls}`}>
      <p className="flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-fulkro-ink-500">
        {label}
      </p>
      <p className="mt-0.5 truncate text-sm font-semibold text-fulkro-ink-700">
        {value}
      </p>
      {meta ? (
        <p className="mt-0.5 truncate text-[10px] text-fulkro-ink-500">
          {meta}
        </p>
      ) : null}
    </div>
  );
}

