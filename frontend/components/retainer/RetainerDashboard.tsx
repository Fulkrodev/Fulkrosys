"use client";

import {
  AlertOctagon,
  Bell,
  Briefcase,
  Calendar,
  CheckCircle2,
  Clock,
  RefreshCw,
  Shield,
  Timer,
  type LucideIcon,
} from "lucide-react";

import { RAGDot } from "@/components/data/RAGBadge";
import { DevHint } from "@/components/dev/DevHint";
import {
  CapacityBar,
  DriftBadge,
  RetainerPlanBadge,
} from "@/components/retainer/RetainerBadges";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  useRenewalStatus,
  useRetainerActivities,
  useRetainerDrifts,
  useRetainerProject,
} from "@/hooks/useRetainer";
import type {
  RetainerActivityRecord,
  RetainerDriftRecord,
  RetainerSummary,
} from "@/lib/api/retainer";
import { cn, formatDate, formatDay } from "@/lib/utils";

// ─── UI labels ───────────────────────────────────────────────────────

const TIPO_LABEL: Record<string, string> = {
  comite_seguridad: "Comité de seguridad",
  reporte_trimestral: "Reporte trimestral",
  revision_privilegios: "Revisión de privilegios",
  vigilancia_vulnerabilidades: "Vigilancia vulnerabilidades",
  simulacro_phishing: "Simulacro phishing",
  prueba_continuidad: "Prueba continuidad",
  revision_ar_dda: "Revisión AR/DDA",
  formacion_anual: "Formación anual",
  auditoria_interna: "Auditoría interna",
  cambio_material: "Cambio material",
};

const ESTADO_STYLES: Record<RetainerActivityRecord["estado"], string> = {
  programada:
    "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-muted)]",
  en_curso: "bg-fulkro-primary-700/10 text-fulkro-primary-700",
  completada: "bg-fulkro-success/10 text-fulkro-success",
  cancelada: "bg-fulkro-danger/10 text-fulkro-danger",
};

const ESTADO_LABEL: Record<RetainerActivityRecord["estado"], string> = {
  programada: "Programada",
  en_curso: "En curso",
  completada: "Hecha",
  cancelada: "Cancelada",
};

// ─── Helpers ─────────────────────────────────────────────────────────

function tipoLabel(tipo: string | null): string {
  if (!tipo) return "Actividad";
  return TIPO_LABEL[tipo] ?? tipo;
}

function driftScoreFromDrifts(drifts: RetainerDriftRecord[]): number {
  // Score determinista: 0.5 por drift abierto + 1.0 extra si severidad alta.
  let score = 0;
  for (const d of drifts) {
    if (d.estado === "resuelto") continue;
    score += 0.5;
    if (d.severidad === "alta" || d.severidad === "critica") score += 1;
  }
  return Math.min(5, Math.round(score * 10) / 10);
}

function capacityPct(r: RetainerSummary): number {
  if (!r.horas_previstas_anual || r.horas_previstas_anual === 0) return 0;
  return Math.round(
    (r.horas_consumidas_total / r.horas_previstas_anual) * 100,
  );
}

function tMinusDays(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const target = new Date(dateStr).getTime();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target - today.getTime()) / (1000 * 60 * 60 * 24));
}

// ─── Component ───────────────────────────────────────────────────────

export function RetainerProjectDashboard({
  projectId,
}: {
  projectId: string;
}) {
  const retainerQ = useRetainerProject(projectId);
  // 404 en useRetainerProject -> data === null. Gateamos dependientes
  // para evitar 404 cascada en consola y peticiones inútiles.
  const hasRetainer = !!retainerQ.data;
  const activitiesQ = useRetainerActivities(projectId, {}, {
    enabled: hasRetainer,
  });
  const driftsQ = useRetainerDrifts(projectId, {}, { enabled: hasRetainer });
  const renewalQ = useRenewalStatus(projectId, { enabled: hasRetainer });

  if (retainerQ.isLoading) {
    return <SkeletonView />;
  }

  // Sub-atom Sesión 3B-2B Phase A.2 · error retry button + technical detail.
  if (retainerQ.isError) {
    return (
      <Alert variant="danger" className="flex flex-col gap-3">
        <div>
          <AlertTitle>Error cargando retainer</AlertTitle>
          <AlertDescription>
            {(retainerQ.error as Error)?.message ?? "Error desconocido"}
          </AlertDescription>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => void retainerQ.refetch()}
          disabled={retainerQ.isRefetching}
          className="self-start"
          data-testid="retainer-dashboard-retry"
        >
          <RefreshCw
            size={14}
            className={retainerQ.isRefetching ? "animate-spin" : ""}
          />
          Reintentar
        </Button>
      </Alert>
    );
  }

  const retainer = retainerQ.data;
  if (!retainer) {
    return (
      <Card className="border-[color:var(--fulkro-surface-glass-border)] bg-[color:var(--fulkro-surface-glass)]">
        <CardContent className="p-0">
          <EmptyState
            icon={<Briefcase className="h-8 w-8" strokeWidth={2.2} />}
            title="Aún no tienes retainer activo"
            description="Activa un retainer para mantener tu sistema ENS al día con vigilancia normativa, evidencias periódicas y auditorías programadas."
            action={{
              label: "Contratar retainer",
              onClick: () =>
                alert(
                  "Contratación de retainer · próximamente. TODO-FASE-X-RETAINER-CONTRATACION-001",
                ),
              variant: "primary",
            }}
          />
        </CardContent>
      </Card>
    );
  }

  const activities = activitiesQ.data?.activities ?? [];
  const drifts = driftsQ.data?.drifts ?? [];
  const renewal = renewalQ.data;
  const driftScore = driftScoreFromDrifts(drifts);
  const consumedPct = capacityPct(retainer);
  const renewalDays = tMinusDays(retainer.next_renewal_date);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-wrap items-start justify-between gap-4 p-5">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 rounded-md bg-fulkro-ink-100 p-2 text-fulkro-primary-700">
              <Shield size={22} strokeWidth={2.4} />
            </span>
            <div>
              <p className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                Retainer {retainer.estado === "active" ? "activo" : retainer.estado}{" "}
                <TooltipENS text="Mantenimiento ENS post-certificación · 4 perfiles (LITE 300-700€/mes · STD 700-1200€ · PLUS 1200€+ · CRITICAL personalizado) según tamaño y criticidad." />
              </p>
              <h2 className="text-xl font-bold text-[color:var(--fulkro-title)]">
                Consola post-certificación
              </h2>
              <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                {retainer.inicio
                  ? `Inicio ${formatDay(retainer.inicio)}`
                  : "Sin fecha de inicio"}
                {" · "}
                {retainer.next_renewal_date
                  ? `Renovación ${formatDay(retainer.next_renewal_date)}`
                  : "Sin renovación programada"}
                {renewal && renewal.renewal_status && (
                  <>
                    {" · estado "}
                    <span className="font-bold text-[color:var(--fulkro-title)]">
                      {renewal.renewal_status}
                    </span>
                  </>
                )}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <RetainerPlanBadge
              plan={retainer.perfil}
              feeEurMonth={retainer.precio_mensual ?? undefined}
            />
            <DriftBadge score={driftScore} />
          </div>
        </CardContent>
      </Card>

      <section className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <KpiTile
          icon={Timer}
          title="SLA respuesta"
          value={`${retainer.sla_respuesta_horas ?? 0} h`}
          sub="Compromiso de respuesta"
        />
        <KpiTile
          icon={CheckCircle2}
          title="Actividades"
          value={String(activities.length)}
          sub={`${activities.filter((a) => a.estado === "completada").length} completadas`}
          pct={
            activities.length === 0
              ? undefined
              : Math.round(
                  (activities.filter((a) => a.estado === "completada").length /
                    activities.length) *
                    100,
                )
          }
        />
        <KpiTile
          icon={Clock}
          title="Horas consumidas"
          value={`${retainer.horas_consumidas_total} h`}
          sub={`de ${retainer.horas_previstas_anual} h previstas`}
          pct={consumedPct}
        />
        <KpiTile
          icon={Calendar}
          title="Renovación"
          value={renewalDays !== null ? `T-${renewalDays} d` : "—"}
          sub="Hasta renovación cert."
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Capacidad consumida</CardTitle>
        </CardHeader>
        <CardContent>
          <CapacityBar consumedPct={consumedPct} />
          <p className="mt-2 text-sm font-medium text-[color:var(--fulkro-muted)]">
            Si supera el 100% durante 2 meses seguidos, considera escalar
            tier.
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <Card>
          <CardHeader>
            <CardTitle>Actividades del retainer</CardTitle>
          </CardHeader>
          <CardContent>
            {activitiesQ.isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : activities.length === 0 ? (
              <div className="flex flex-col items-center gap-2 rounded-md border border-[color:var(--fulkro-surface-glass-border)] bg-[color:var(--fulkro-surface-glass)] py-8 text-center">
                <Calendar
                  size={28}
                  strokeWidth={2.2}
                  className="text-[color:var(--fulkro-muted)]"
                />
                <p className="text-sm font-medium text-[color:var(--fulkro-body)]">
                  Sin actividades programadas todavía.
                </p>
              </div>
            ) : (
              <ul className="space-y-2">
                {activities.map((task) => (
                  <li
                    key={task.id}
                    className="flex items-start justify-between gap-3 rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-3 py-2 text-sm"
                  >
                    <div className="min-w-0">
                      <p className="font-bold text-[color:var(--fulkro-title)]">
                        {task.titulo ?? tipoLabel(task.tipo_actividad)}
                      </p>
                      <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                        {tipoLabel(task.tipo_actividad)}
                        {task.horas_estimadas
                          ? ` · ${task.horas_estimadas} h estimadas`
                          : ""}
                        {task.horas_consumidas
                          ? ` · ${task.horas_consumidas} h consumidas`
                          : ""}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1 text-right">
                      <span className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                        {task.fecha_programada
                          ? formatDate(task.fecha_programada)
                          : "—"}
                      </span>
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-xs font-bold",
                          ESTADO_STYLES[task.estado],
                        )}
                      >
                        {ESTADO_LABEL[task.estado]}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <aside className="flex flex-col gap-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2.5">
                <AlertOctagon size={22} strokeWidth={2.4} /> Drifts abiertos
              </CardTitle>
            </CardHeader>
            <CardContent>
              {driftsQ.isLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : drifts.filter((d) => d.estado !== "resuelto").length === 0 ? (
                <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                  Sin drifts pendientes.
                </p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {drifts
                    .filter((d) => d.estado !== "resuelto")
                    .map((d) => (
                      <li
                        key={d.id}
                        className="flex items-start gap-2 rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-3 py-2"
                      >
                        <RAGDot
                          status={
                            d.severidad === "alta" || d.severidad === "critica"
                              ? "red"
                              : d.severidad === "media"
                                ? "amber"
                                : "green"
                          }
                          className="mt-1 h-2 w-2"
                        />
                        <div className="min-w-0">
                          <p className="font-bold text-[color:var(--fulkro-title)]">
                            {d.dimension}
                          </p>
                          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                            {d.descripcion} · severidad {d.severidad} · impacto{" "}
                            {d.impacto}
                          </p>
                        </div>
                      </li>
                    ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2.5">
                <Bell size={22} strokeWidth={2.4} /> Renovación
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm font-medium text-[color:var(--fulkro-body)]">
                {retainer.next_renewal_date
                  ? `Próxima renovación: ${formatDay(retainer.next_renewal_date)}`
                  : "Sin renovación programada."}
              </p>
              <p className="mt-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
                Estado:{" "}
                <span className="font-bold text-[color:var(--fulkro-title)]">
                  {retainer.renewal_status ?? "—"}
                </span>
                {" · auto-renovación: "}
                {retainer.renovacion_automatica ? "sí" : "no"}
              </p>
              <DevHint>
                Datos en tiempo real desde Motor 23 (paso 1 + paso 2).
              </DevHint>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function SkeletonView() {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-24 w-full" />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
      <Skeleton className="h-32 w-full" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}

function KpiTile({
  icon: Icon,
  title,
  value,
  sub,
  pct,
}: {
  icon: LucideIcon;
  title: string;
  value: string;
  sub: string;
  pct?: number;
}) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-1.5 p-5">
        <div className="flex items-center gap-2 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
          <Icon size={16} strokeWidth={2.4} /> {title}
        </div>
        <p className="text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
          {value}
        </p>
        <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
          {sub}
        </p>
        {typeof pct === "number" && (
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-fulkro-ink-100">
            <div
              className={cn(
                "h-full",
                pct >= 90
                  ? "bg-fulkro-success"
                  : pct >= 70
                    ? "bg-fulkro-primary-700"
                    : "bg-fulkro-warning",
              )}
              style={{ width: `${Math.min(100, pct)}%` }}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
