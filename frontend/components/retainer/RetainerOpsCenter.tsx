"use client";

import {
  AlertTriangle,
  Briefcase,
  Calendar,
  ExternalLink,
  Loader2,
  RefreshCcw,
  Sparkles,
  Users,
} from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { toast } from "sonner";

import { CapacityTile } from "@/components/admin/retainers/CapacityTile";
import { RAGDot } from "@/components/data/RAGBadge";
import { DevHint } from "@/components/dev/DevHint";
import {
  DriftBadge,
  RenewalClock,
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
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  useAgent26Alerts,
  useRetainerOverview,
} from "@/hooks/useRetainer";
import type {
  Agent26AlertItem,
  RetainerOverviewItem,
} from "@/lib/api/retainer";
import { ROUTES } from "@/lib/constants";
import type { RagStatus } from "@/lib/types";
import { cn, formatDate, formatDay } from "@/lib/utils";

// ─── Filter types (locales, no leak fuera) ─────────────────────────

type Filter = {
  rag: RagStatus | "all";
  tier: string | "all";
  query: string;
};

function formatEuros(v: number): string {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(v);
}

function ragFromHealth(health: RagStatus): RagStatus {
  return health;
}

// ─── Component ─────────────────────────────────────────────────────

export function RetainerOpsCenter() {
  const overviewQ = useRetainerOverview();
  const alertsQ = useAgent26Alerts();

  const [filter, setFilter] = React.useState<Filter>({
    rag: "all",
    tier: "all",
    query: "",
  });
  const [busy, setBusy] = React.useState(false);

  const retainers: RetainerOverviewItem[] = React.useMemo(
    () => overviewQ.data?.retainers ?? [],
    [overviewQ.data],
  );

  const filtered = React.useMemo(() => {
    const q = filter.query.trim().toLowerCase();
    return retainers.filter((c) => {
      if (filter.rag !== "all" && c.health_status !== filter.rag) return false;
      if (filter.tier !== "all" && c.tier !== filter.tier) return false;
      if (!q) return true;
      return (
        c.client_name.toLowerCase().includes(q) ||
        c.tier.toLowerCase().includes(q)
      );
    });
  }, [retainers, filter]);

  const incidentsOpenTotal = React.useMemo(() => {
    if (!alertsQ.data) return 0;
    return alertsQ.data.filter(
      (a) => a.priority === "critical" || a.priority === "high",
    ).length;
  }, [alertsQ.data]);

  const driftLeaderboard = React.useMemo(() => {
    if (!alertsQ.data) return [];
    return alertsQ.data.slice(0, 5).map((a) => ({
      client_name: a.client_name,
      severity: priorityToRag(a.priority),
      label: a.title,
    }));
  }, [alertsQ.data]);

  const renewalsInFlight = React.useMemo(() => {
    return retainers
      .filter(
        (r) =>
          r.days_until_renewal !== null &&
          r.days_until_renewal !== undefined &&
          r.days_until_renewal <= 180,
      )
      .map((r) => ({
        client_name: r.client_name,
        t_minus_days: r.days_until_renewal!,
      }))
      .sort((a, b) => a.t_minus_days - b.t_minus_days);
  }, [retainers]);

  const upcomingActivities = React.useMemo(() => {
    return retainers
      .filter((r) => r.next_activity?.fecha)
      .slice(0, 5)
      .map((r) => ({
        client_name: r.client_name,
        date: r.next_activity!.fecha!,
        title: r.next_activity!.titulo ?? r.next_activity!.tipo,
      }));
  }, [retainers]);

  if (overviewQ.isLoading) {
    return <SkeletonView />;
  }

  if (overviewQ.isError) {
    return (
      <Alert variant="danger">
        <AlertTitle>Error cargando consola retainer</AlertTitle>
        <AlertDescription>
          {(overviewQ.error as Error)?.message ?? "Error desconocido"}
        </AlertDescription>
      </Alert>
    );
  }

  const data = overviewQ.data;
  if (!data) {
    return (
      <Card className="border-[color:var(--fulkro-surface-glass-border)] bg-[color:var(--fulkro-surface-glass)]">
        <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
          <Briefcase
            size={42}
            strokeWidth={2.2}
            className="text-[color:var(--fulkro-muted)]"
          />
          <p className="text-base font-medium text-[color:var(--fulkro-body)]">
            Aún no hay retainers activos.
          </p>
        </CardContent>
      </Card>
    );
  }

  const totalRetainers = data.total_retainers ?? retainers.length;
  const mrrTotal = data.mrr_total ?? 0;
  const monthToBillEur = mrrTotal; // backend ya factura mensual

  async function runOperator() {
    setBusy(true);
    try {
      await Promise.all([overviewQ.refetch(), alertsQ.refetch()]);
      toast.success("Agente 26 — análisis actualizado");
    } finally {
      setBusy(false);
    }
  }

  async function refreshOverview() {
    await Promise.all([overviewQ.refetch(), alertsQ.refetch()]);
    toast.success("Datos refrescados");
  }

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
            Consola Retainer{" "}
            <TooltipENS text="Vista agregada de todos tus clientes en retainer post-certificación · drift · MRR · alertas A26." />
          </h1>
          <p className="text-base font-medium text-[color:var(--fulkro-body)]">
            {totalRetainers} clientes activos · MRR{" "}
            {formatEuros(mrrTotal)}
            {data.agent_26_summary?.total_alerts !== undefined && (
              <>
                {" · "}
                {data.agent_26_summary.total_alerts} alertas Agente 26
              </>
            )}
            .{" "}
            <DevHint>
              GET /api/v1/retainer/paso2/dashboard · GET /api/v1/retainer/paso2/agent-26/alerts
            </DevHint>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={refreshOverview}>
            <RefreshCcw size={16} strokeWidth={2.4} /> Refrescar
          </Button>
          <Button
            variant="primary"
            size="md"
            disabled={busy}
            onClick={runOperator}
          >
            {busy ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Sparkles size={16} strokeWidth={2.4} />
            )}
            Agente 26 · priorizar
          </Button>
        </div>
      </header>

      <CapacityTile activeRetainers={totalRetainers} />

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatPill label="MRR" value={formatEuros(mrrTotal)} />
        <StatPill
          label="A facturar este mes"
          value={formatEuros(monthToBillEur)}
        />
        <StatPill
          label="Alertas críticas"
          value={String(incidentsOpenTotal)}
          emphasis={incidentsOpenTotal > 0 ? "warn" : undefined}
        />
        <StatPill
          label="Total retainers"
          value={String(totalRetainers)}
        />
      </section>

      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 p-4 text-xs">
          <input
            value={filter.query}
            onChange={(e) =>
              setFilter((f) => ({ ...f, query: e.target.value }))
            }
            placeholder="Filtrar por nombre o tier…"
            className="flex-1 rounded-md border border-fulkro-ink-300 bg-white px-2 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700"
          />
          <select
            aria-label="Filtrar por health status"
            value={filter.rag}
            onChange={(e) =>
              setFilter((f) => ({
                ...f,
                rag: e.target.value as Filter["rag"],
              }))
            }
            className="h-8 rounded-md border border-fulkro-ink-300 bg-white px-2 text-xs"
          >
            <option value="all">Todo health</option>
            <option value="green">Verde</option>
            <option value="amber">Ámbar</option>
            <option value="red">Rojo</option>
          </select>
          <select
            aria-label="Filtrar por tier retainer"
            value={filter.tier}
            onChange={(e) =>
              setFilter((f) => ({
                ...f,
                tier: e.target.value as Filter["tier"],
              }))
            }
            className="h-8 rounded-md border border-fulkro-ink-300 bg-white px-2 text-xs"
          >
            <option value="all">Todos los tiers</option>
            <option value="R_MICRO">Micro</option>
            <option value="R_LITE">Lite</option>
            <option value="R_STD">Standard</option>
            <option value="R_PLUS">Plus</option>
            <option value="R_CRITICAL">Critical</option>
          </select>
          <span className="text-fulkro-ink-500">
            {filtered.length}/{retainers.length} clientes
          </span>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {filtered.map((c) => (
            <RetainerCard key={c.retainer_id} item={c} />
          ))}
          {filtered.length === 0 && (
            <Card className="col-span-full border-[color:var(--fulkro-surface-glass-border)] bg-[color:var(--fulkro-surface-glass)]">
              <CardContent className="flex flex-col items-center gap-2 py-8">
                <Briefcase
                  size={28}
                  strokeWidth={2.2}
                  className="text-[color:var(--fulkro-muted)]"
                />
                <p className="text-sm font-medium text-[color:var(--fulkro-body)]">
                  Ningún cliente coincide con el filtro.
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        <aside className="flex flex-col gap-3">
          <QueueCard
            icon={AlertTriangle}
            title="Alertas Agente 26"
            items={driftLeaderboard.map((d) => ({
              left: d.client_name,
              right: d.label,
              severity: d.severity,
            }))}
            empty="Sin alertas activas."
          />
          <QueueCard
            icon={Briefcase}
            title="Renovaciones próximas"
            items={renewalsInFlight.map((r) => ({
              left: r.client_name,
              right: `T-${r.t_minus_days} d`,
              severity:
                r.t_minus_days <= 60
                  ? "red"
                  : r.t_minus_days <= 120
                    ? "amber"
                    : "green",
            }))}
            empty="Sin renovaciones inminentes."
          />
          <QueueCard
            icon={Calendar}
            title="Próximas actividades"
            items={upcomingActivities.map((c) => ({
              left: c.client_name,
              right: formatDay(c.date),
              severity: "green",
            }))}
            empty="Sin actividades agendadas."
          />
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2.5">
                <Users size={22} strokeWidth={2.4} /> Resumen
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5 text-sm">
              <Row label="Retainers activos" value={String(totalRetainers)} />
              <Row label="MRR" value={formatEuros(mrrTotal)} />
              <Row
                label="Alertas Agente 26"
                value={String(data.agent_26_summary?.total_alerts ?? 0)}
              />
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}

// ─── Subcomponents ─────────────────────────────────────────────────

function priorityToRag(p: Agent26AlertItem["priority"]): RagStatus {
  if (p === "critical" || p === "high") return "red";
  if (p === "medium") return "amber";
  return "green";
}

function RetainerCard({ item }: { item: RetainerOverviewItem }) {
  const rag = ragFromHealth(item.health_status);
  const renewalDays = item.days_until_renewal;

  // La vista cross-cliente (RetainerOverviewItem) NO expone horas/capacidad;
  // el consumo fino se calcula en RetainerProjectDashboard con datos del
  // proyecto. En vez de pintar una CapacityBar muda al 0% (que implicaría
  // falsamente "0% consumido"), mostramos un enlace honesto a la consola del
  // proyecto. §3.2/314.

  return (
    <Card className="overflow-hidden">
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-2">
              <RAGDot status={rag} className="h-2 w-2 shrink-0" />
              <span
                className="truncate text-sm font-semibold text-fulkro-primary-700"
                title={item.client_name}
              >
                {item.client_name}
              </span>
            </p>
            <p className="truncate text-sm font-medium text-[color:var(--fulkro-muted)]">
              {tierLabel(item.tier)}
            </p>
          </div>
          <div className="shrink-0">
            <RetainerPlanBadge
              plan={item.tier}
              feeEurMonth={item.monthly_fee}
            />
          </div>
        </div>

        <div className="space-y-2 text-sm">
          {item.next_activity ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                  Próxima actividad
                </span>
                <span className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                  {item.next_activity.fecha
                    ? formatDate(item.next_activity.fecha)
                    : "—"}
                </span>
              </div>
              <p className="text-fulkro-ink-700">
                {item.next_activity.titulo ?? item.next_activity.tipo}
              </p>
            </>
          ) : (
            <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
              Sin próximas actividades programadas.
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {renewalDays !== null && renewalDays !== undefined && (
            <RenewalClock
              tMinusDays={renewalDays}
              expiresAt={item.cert_renewal_date ?? undefined}
            />
          )}
          {item.renewal_status && (
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold",
                item.renewal_status === "urgent" ||
                  item.renewal_status === "overdue"
                  ? "bg-fulkro-danger/10 text-fulkro-danger"
                  : item.renewal_status === "warning"
                    ? "bg-fulkro-warning/10 text-fulkro-warning"
                    : "bg-fulkro-success/10 text-fulkro-success",
              )}
            >
              {item.renewal_status}
            </span>
          )}
        </div>

        <Link
          href={`${ROUTES.projects}/${item.client_id}/retainer`}
          className="inline-flex items-center gap-1 text-xs font-medium text-[color:var(--fulkro-muted)] hover:text-fulkro-info hover:underline"
        >
          Capacidad fina en el dashboard del proyecto
          <ExternalLink size={11} strokeWidth={2.4} />
        </Link>

        <div className="flex items-center justify-end gap-3">
          {item.retainer_id && (
            <a
              href={`/api/v1/retainer/${item.retainer_id}/reports/annual/${new Date().getFullYear()}/download`}
              className="inline-flex items-center gap-1 text-xs font-bold text-[color:var(--fulkro-accent)] hover:underline"
              data-testid={`retainer-annual-report-${item.retainer_id}`}
            >
              Informe anual ↓
            </a>
          )}
          <Link
            href={`${ROUTES.projects}/${item.client_id}/retainer`}
            className="inline-flex items-center gap-1 text-xs text-fulkro-info hover:underline"
          >
            Abrir consola{" "}
            <ExternalLink size={12} strokeWidth={2.4} />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

const TIER_LABELS: Record<string, string> = {
  R_MICRO: "Micro",
  R_LITE: "Lite",
  R_STD: "Standard",
  R_PLUS: "Plus",
  R_CRITICAL: "Critical",
};

function tierLabel(tier: string): string {
  return TIER_LABELS[tier] ?? tier;
}

function QueueCard({
  icon: Icon,
  title,
  items,
  empty,
}: {
  icon: typeof Calendar;
  title: string;
  items: { left: string; right: string; severity: RagStatus }[];
  empty: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2.5">
          <Icon size={22} strokeWidth={2.4} /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
            {empty}
          </p>
        ) : (
          <ul className="space-y-1.5 text-sm">
            {items.map((i, idx) => (
              <li
                key={`${i.left}-${idx}`}
                className="flex flex-col gap-0.5 rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-2 py-1.5"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <RAGDot status={i.severity} className="h-2 w-2 shrink-0" />
                  <span className="truncate font-medium" title={i.left}>
                    {i.left}
                  </span>
                </span>
                <span className="ml-4 font-mono text-sm font-medium text-[color:var(--fulkro-muted)]">
                  {i.right}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm font-medium text-[color:var(--fulkro-muted)]">
        {label}
      </span>
      <span className="font-bold text-[color:var(--fulkro-title)]">
        {value}
      </span>
    </div>
  );
}

function StatPill({
  label,
  value,
  emphasis,
}: {
  label: string;
  value: string;
  emphasis?: "warn";
}) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-white p-3 shadow-md",
        emphasis === "warn"
          ? "border-fulkro-warning/40"
          : "border-[color:var(--fulkro-surface-glass-border)]",
      )}
    >
      <p className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
        {label}
      </p>
      <p className="mt-0.5 text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
        {value}
      </p>
    </div>
  );
}

function SkeletonView() {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-16 w-full" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
      <Skeleton className="h-12 w-full" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
        <Skeleton className="h-96" />
      </div>
    </div>
  );
}
