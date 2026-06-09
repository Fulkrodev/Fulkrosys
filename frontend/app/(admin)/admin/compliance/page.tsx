"use client";

/**
 * /admin/compliance · Compliance portal landing dashboard (sub-atom Sesión 3B-1 Phase B.1).
 *
 * Single entry point que consolida sub-portales compliance cumulative:
 *   - /admin/compliance/monitor (Self-Monitoring System · 17 checks · MB-9.bis Bloque 4)
 *   - /admin/compliance/projects (Cross-project aggregator · Bloque 4 Phase B)
 *   - /admin/compliance/norma-reports (Norma-specific reports per regulation)
 *
 * Pattern: card grid · cada sub-portal su KPI summary + Link cta enter.
 *
 * Architectural decision Phase 0: Option B Consolidation (NOT new route group ·
 * preserves admin layout · less disruption · ENS Radar /(radar) pattern separate
 * sostained). R23 explicit exception · top-level admin multi-cliente legítimo.
 */
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bell,
  Briefcase,
  CheckCircle2,
  FileText,
  Gavel,
  Lock,
  Loader2,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAdminCrossProjectCompliance } from "@/hooks/useAdminCrossProjectCompliance";
import { useDashboardKpis } from "@/hooks/useDashboardData";
import { listActiveAlertsGlobal } from "@/lib/admin-alerts/api";
import { getMonitorStatus } from "@/lib/admin-compliance-monitor/api";
import { listNormas } from "@/lib/admin-compliance-monitor/norma-api";
import { cn } from "@/lib/utils";

// Sub-atom Sesión 3B-2A Phase C.1 · Fulkro own compliance priority normas.
// Per briefing PART E: surface ENS + ISO 27001 + RGPD prominently as the
// "Compliance propio Fulkro" section · dogfooding regla inviolable #7.
const FULKRO_OWN_NORMA_KEYS = [
  "ens_rd_311_2022",
  "iso_27001_2022",
  "rgpd_ue_2016_679",
] as const;

const FULKRO_OWN_NORMA_LABELS: Record<string, string> = {
  ens_rd_311_2022: "ENS Medio",
  iso_27001_2022: "ISO 27001:2022",
  rgpd_ue_2016_679: "RGPD",
};

const FULKRO_OWN_NORMA_DESC: Record<string, string> = {
  ens_rd_311_2022:
    "RD 311/2022 · Marcos cumple ENS Medio sobre su propia plataforma (dogfooding · Regla inviolable #7).",
  iso_27001_2022:
    "ISO 27001:2022 · controles A.5-A.18 de seguridad de la información gestionados internamente.",
  rgpd_ue_2016_679:
    "Reglamento UE 2016/679 · datos de clientes procesados por Fulkro con cumplimiento privacy by design.",
};

interface PortalCardProps {
  title: string;
  description: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  /** Optional summary line shown above CTA. */
  summary?: React.ReactNode;
  /** Optional badge label/tone. */
  badge?: { label: string; tone: "success" | "warning" | "info" | "secondary" };
  testid?: string;
}

function PortalCard({
  title,
  description,
  href,
  icon: Icon,
  summary,
  badge,
  testid,
}: PortalCardProps) {
  return (
    <Card
      className="flex h-full flex-col transition-all hover:border-fulkro-info hover:shadow-md"
      data-testid={testid}
    >
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <Icon className="mt-1 h-5 w-5 shrink-0 text-fulkro-primary-700" />
            <div>
              <CardTitle className="text-base">{title}</CardTitle>
              <CardDescription className="mt-1">{description}</CardDescription>
            </div>
          </div>
          {badge ? (
            <Badge variant={badge.tone} className="text-[10px]">
              {badge.label}
            </Badge>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="mt-auto flex flex-col gap-3 pt-2">
        {summary ? (
          <div className="rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-3 text-sm">
            {summary}
          </div>
        ) : null}
        <Link
          href={href}
          className={cn(
            buttonVariants({ variant: "primary", size: "sm" }),
            "w-full justify-center",
          )}
          data-testid={`${testid}-enter`}
        >
          Abrir
          <ArrowRight className="ml-1 h-3.5 w-3.5" />
        </Link>
      </CardContent>
    </Card>
  );
}

export default function ComplianceLandingPage() {
  // Self-monitoring snapshot (MB-9.bis · 17 checks · platform global)
  const monitorQuery = useQuery({
    queryKey: ["compliance-landing", "monitor-status"],
    queryFn: getMonitorStatus,
    refetchInterval: 60_000,
    refetchOnWindowFocus: false,
    retry: false,
  });

  // Cross-project aggregator (Bloque 4 Phase B · multi-cliente)
  const projectsQuery = useAdminCrossProjectCompliance();

  // Sub-atom Sesión 3B-2A Phase C.1 · Fulkro own compliance normas
  // (ENS + ISO 27001 + RGPD) prominently surfaced. Reuses listNormas
  // endpoint (production · 7 normas · MB-9.bis mini-atom 3).
  const normasQuery = useQuery({
    queryKey: ["compliance-landing", "fulkro-own-normas"],
    queryFn: listNormas,
    refetchInterval: 60_000,
    refetchOnWindowFocus: false,
    retry: false,
  });

  // Sub-area 2E Sesión 3B-2B.9 CLUSTER 2 · cross-client mini widgets
  // (Pattern P-CL2-4 EXTEND existing landing · NO new /cross-client route
  // per R23 doctrine · OPS-026 DRY reuse hooks existing).
  const kpisQuery = useDashboardKpis();
  const globalAlertsQuery = useQuery({
    queryKey: ["compliance-landing", "global-alerts"],
    queryFn: listActiveAlertsGlobal,
    refetchInterval: 60_000,
    refetchOnWindowFocus: false,
    retry: false,
  });

  // #J-GAP3 · los plugins backend exponen norma_key en MAYÚSCULAS
  // (ENS_RD_311_2022) mientras estas constantes están en minúsculas → la
  // comparación directa NUNCA casaba y las 3 cards de compliance propio
  // quedaban en "Sin datos" perpetuo. Normalizamos a minúsculas en la
  // comparación (DO-NOW · sin tocar BD · alternativa a PE-1).
  const fulkroOwnNormas = normasQuery.data?.filter((n) =>
    FULKRO_OWN_NORMA_KEYS.includes(
      n.norma_key.toLowerCase() as (typeof FULKRO_OWN_NORMA_KEYS)[number],
    ),
  );

  return (
    <div className="container mx-auto max-w-7xl space-y-6 py-6">
      {/* Sub-atom Sesión 3B-2A Phase C.2 · brand header logo + title
          (pattern análogo /(radar)/ layout · diferenciación cognitiva por
          iconografía + copy + URL · paleta purple+ink sostenida). */}
      <header className="overflow-hidden rounded-xl border border-fulkro-primary-200 bg-gradient-to-r from-fulkro-primary-50 via-white to-fulkro-accent-300/10 px-5 py-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-6 w-6 text-fulkro-primary-700" />
              <span className="text-xs font-bold uppercase tracking-wider text-fulkro-primary-700">
                Fulkro · Compliance Center
              </span>
            </div>
            <h1 className="text-2xl font-semibold text-fulkro-primary-700">
              Centro de cumplimiento
            </h1>
            <p className="max-w-2xl text-sm text-fulkro-ink-700">
              Vista unificada: la plataforma FULKRO, el estado cross-cliente y
              los informes por normativa. Marcos cumple ENS Medio + ISO 27001 +
              RGPD sobre su propia infraestructura (dogfooding · Regla
              inviolable #7).
            </p>
          </div>
          <Badge variant="info" className="text-[10px]">
            <Sparkles className="mr-1 h-3 w-3" />
            Auto-audit propio FULKRO
          </Badge>
        </div>
      </header>

      {/* Sub-atom Sesión 3B-2A Phase C.1 · Fulkro own compliance section
          prominent · ENS + ISO 27001 + RGPD surfaced antes de los portales
          sub-portales generales. Status badges + run report + history link. */}
      <section
        className="rounded-xl border border-fulkro-primary-200 bg-white p-5 shadow-sm"
        aria-labelledby="fulkro-own-compliance-heading"
      >
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2
              id="fulkro-own-compliance-heading"
              className="flex items-center gap-2 text-lg font-bold text-fulkro-primary-700"
            >
              <Lock className="h-5 w-5" />
              Compliance propio Fulkro
            </h2>
            <p className="mt-0.5 text-sm text-fulkro-ink-700">
              Auto-auditoría continua: la plataforma FULKRO cumple ENS Medio +
              ISO 27001 + RGPD sobre sí misma · informes ENAC-ready descargables.
            </p>
          </div>
          <Link
            href="/admin/compliance/norma-reports"
            className="text-xs font-medium text-fulkro-info hover:underline"
            data-testid="fulkro-own-norma-reports-link"
          >
            Ver todas las normativas →
          </Link>
        </header>

        <div className="grid gap-3 md:grid-cols-3" data-testid="fulkro-own-normas-grid">
          {FULKRO_OWN_NORMA_KEYS.map((key) => {
            const norma = fulkroOwnNormas?.find(
              (n) => n.norma_key.toLowerCase() === key,
            );
            const isLoading = normasQuery.isLoading;
            const status = norma?.latest_status ?? null;
            const score = norma?.latest_score ?? null;
            return (
              <article
                key={key}
                className="rounded-lg border border-fulkro-ink-200 bg-fulkro-ink-50/50 p-4 transition-colors hover:border-fulkro-primary-200 hover:bg-white"
                data-testid={`fulkro-own-norma-${key}`}
              >
                <header className="mb-2 flex items-start justify-between gap-2">
                  <h3 className="text-sm font-bold text-fulkro-ink-900">
                    {FULKRO_OWN_NORMA_LABELS[key]}
                  </h3>
                  {isLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-fulkro-ink-400" />
                  ) : status === "green" ? (
                    <Badge variant="success" className="text-[10px]">
                      <CheckCircle2 className="mr-1 h-3 w-3" />
                      Conforme
                    </Badge>
                  ) : status === "yellow" ? (
                    <Badge variant="warning" className="text-[10px]">
                      <AlertTriangle className="mr-1 h-3 w-3" />
                      Aviso
                    </Badge>
                  ) : status === "red" ? (
                    <Badge variant="danger" className="text-[10px]">
                      <AlertTriangle className="mr-1 h-3 w-3" />
                      Pendiente
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-[10px]">
                      Sin datos
                    </Badge>
                  )}
                </header>
                <p className="mb-3 text-xs text-fulkro-ink-600">
                  {FULKRO_OWN_NORMA_DESC[key]}
                </p>
                {score !== null ? (
                  <p className="mb-2 text-xs text-fulkro-ink-500">
                    Score último: <span className="font-mono font-bold text-fulkro-ink-800">{score.toFixed(0)}/100</span>
                  </p>
                ) : null}
                <Link
                  href={`/admin/compliance/norma-reports#${key}`}
                  className="inline-flex items-center gap-1 text-xs font-medium text-fulkro-info hover:underline"
                  data-testid={`fulkro-own-norma-${key}-link`}
                >
                  Ver informe + descargar
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </article>
            );
          })}
        </div>
      </section>

      {/* Sub-area 2D Sesión 3B-2B.9 CLUSTER 2 · Fulkro own ENS Medio progress
          cards M04 gaps + M03 DdA + M09 audit-prep (REFACTOR+EXTEND existing
          landing per Pattern P-CL2-4 · OPS-052 manifestación 67ª).

          M04 wired al snapshot self-monitoring existing (19 checks técnicos
          ya cubren foundation). M03 + M09 son honest defer Future-X explicit
          (Pattern P-CL2-3) hasta que entity fulkro_own_project_id especial
          + servicios self-applied shipped (Future-3B-4.F.* series). */}
      <section
        className="rounded-xl border border-fulkro-accent-200 bg-white p-5 shadow-sm"
        aria-labelledby="fulkro-own-ens-medio-heading"
      >
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2
              id="fulkro-own-ens-medio-heading"
              className="flex items-center gap-2 text-lg font-bold text-fulkro-primary-700"
            >
              <ShieldCheck className="h-5 w-5" />
              Fulkro propio · ENS Medio progress
            </h2>
            <p className="mt-0.5 text-sm text-fulkro-ink-700">
              Estado dogfooding aplicado · M04 gaps técnicos · M03 DdA propia ·
              M09 audit-prep pre-ENAC bienal Fulkro propio.
            </p>
          </div>
          <Badge variant="info" className="text-[10px]">
            <Lock className="mr-1 h-3 w-3" />
            Auto-aplicado FULKRO
          </Badge>
        </header>

        <div
          className="grid gap-3 md:grid-cols-3"
          data-testid="fulkro-own-ens-medio-grid"
        >
          {/* M04 gaps Fulkro propio · wired al monitor existing (19 checks
              técnicos cubren foundation · open_alerts proxy del gap count). */}
          <article
            className="rounded-lg border border-fulkro-ink-200 bg-fulkro-ink-50/50 p-4 transition-colors hover:border-fulkro-primary-200 hover:bg-white"
            data-testid="fulkro-own-m04-gaps-card"
          >
            <header className="mb-2 flex items-start justify-between gap-2">
              <h3 className="text-sm font-bold text-fulkro-ink-900">
                M04 · Gaps técnicos
              </h3>
              {monitorQuery.isLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-fulkro-ink-400" />
              ) : (
                <Badge
                  variant={
                    (monitorQuery.data?.open_alerts ?? 0) === 0
                      ? "success"
                      : (monitorQuery.data?.open_alerts ?? 0) > 5
                        ? "danger"
                        : "warning"
                  }
                  className="text-[10px]"
                >
                  {monitorQuery.data?.open_alerts ?? 0} abiertos
                </Badge>
              )}
            </header>
            <p className="mb-3 text-xs text-fulkro-ink-600">
              Gaps detectados sobre la plataforma propia (proxy al
              self-monitoring · 19 checks técnicos cumulative).
            </p>
            <Link
              href="/admin/compliance/monitor"
              className="inline-flex items-center gap-1 text-xs font-medium text-fulkro-info hover:underline"
              data-testid="fulkro-own-m04-gaps-link"
            >
              Ver detalle 19 checks
              <ArrowRight className="h-3 w-3" />
            </Link>
          </article>

          {/* M03 DdA propia · honest defer Future-X (requires self entity +
              backend self-DdA generator · Future-3B-4.F.fulkro-self-dda-m03). */}
          <article
            className="rounded-lg border border-fulkro-ink-200 bg-fulkro-ink-50/50 p-4 opacity-90"
            data-testid="fulkro-own-m03-dda-card"
          >
            <header className="mb-2 flex items-start justify-between gap-2">
              <h3 className="text-sm font-bold text-fulkro-ink-900">
                M03 · DdA Fulkro propio
              </h3>
              <Badge variant="outline" className="text-[10px]">
                Próximamente
              </Badge>
            </header>
            <p className="mb-3 text-xs text-fulkro-ink-600">
              Declaración de Aplicabilidad firmada Ed25519 sobre las 73 medidas
              ENS Medio aplicadas a la plataforma propia.
            </p>
            <p
              className="text-[10px] italic text-fulkro-ink-500"
              data-testid="fulkro-own-m03-dda-future-ref"
            >
              Future-3B-4.F.fulkro-self-dda-m03-ed25519-artifact (~3-4h post-piloto)
            </p>
          </article>

          {/* M09 audit-prep Fulkro propio · honest defer Future-X
              (requires self entity + full M09 cycle · Future-3B-4.F.fulkro-self
              -audit-prep-m09-full-cycle). */}
          <article
            className="rounded-lg border border-fulkro-ink-200 bg-fulkro-ink-50/50 p-4 opacity-90"
            data-testid="fulkro-own-m09-audit-card"
          >
            <header className="mb-2 flex items-start justify-between gap-2">
              <h3 className="text-sm font-bold text-fulkro-ink-900">
                M09 · Audit-prep ENAC bienal
              </h3>
              <Badge variant="outline" className="text-[10px]">
                Próximamente
              </Badge>
            </header>
            <p className="mb-3 text-xs text-fulkro-ink-600">
              Preparación dossier ENAC para auditoría bienal Fulkro propio ·
              evidencias M07 self-applied + readiness score continuous.
            </p>
            <p
              className="text-[10px] italic text-fulkro-ink-500"
              data-testid="fulkro-own-m09-audit-future-ref"
            >
              Future-3B-4.F.fulkro-self-audit-prep-m09-full-cycle (~2-3h post-piloto)
            </p>
          </article>
        </div>
      </section>

      {/* Sub-area 2E Sesión 3B-2B.9 CLUSTER 2 · Cross-client supervisión
          high-level widgets · MRR mini + Alertas globales mini + Pipeline mini
          (Pattern P-CL2-4 EXTEND existing landing · OPS-052 manifestación 68ª).

          R23 legitimate cross-client view doctrine sostenida (NO entry a
          proyecto · solo high-level supervisión). NO crear /admin/compliance
          /cross-client (colisiona con landing actual + duplica
          /admin/compliance/projects aggregator existing). */}
      <section
        className="rounded-xl border border-fulkro-info/30 bg-white p-5 shadow-sm"
        aria-labelledby="cross-client-overview-heading"
      >
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2
              id="cross-client-overview-heading"
              className="flex items-center gap-2 text-lg font-bold text-fulkro-primary-700"
            >
              <Users className="h-5 w-5" />
              Cross-client overview · supervisión high-level
            </h2>
            <p className="mt-0.5 text-sm text-fulkro-ink-700">
              Vista agregada cross-cliente · revenue MRR · alertas globales ·
              pipeline activo. NO entry a ningún proyecto · solo supervisión.
            </p>
          </div>
          <Link
            href="/admin/compliance/projects"
            className="text-xs font-medium text-fulkro-info hover:underline"
            data-testid="cross-client-projects-link"
          >
            Ver detalle multi-cliente →
          </Link>
        </header>

        <div
          className="grid gap-3 md:grid-cols-3"
          data-testid="cross-client-overview-grid"
        >
          {/* MRR mini widget · reuse useDashboardKpis existing */}
          <article
            className="rounded-lg border border-fulkro-ink-200 bg-fulkro-ink-50/50 p-4 transition-colors hover:border-fulkro-success/40 hover:bg-white"
            data-testid="cross-client-mrr-widget"
          >
            <header className="mb-2 flex items-start justify-between gap-2">
              <h3 className="text-sm font-bold text-fulkro-ink-900">
                MRR retainers
              </h3>
              <TrendingUp
                className="h-4 w-4 text-fulkro-success"
                aria-hidden="true"
              />
            </header>
            {kpisQuery.isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-fulkro-ink-400" />
            ) : kpisQuery.data ? (
              <>
                <p className="mb-1 text-2xl font-bold tabular-nums text-fulkro-ink-900">
                  €{kpisQuery.data.mrr_eur.toFixed(0)}
                </p>
                <p className="text-xs text-fulkro-ink-600">
                  {kpisQuery.data.retainers_active} retainer
                  {kpisQuery.data.retainers_active === 1 ? "" : "s"} activo
                  {kpisQuery.data.retainers_active === 1 ? "" : "s"} ·
                  treasury 30d €{kpisQuery.data.treasury_30d_eur.toFixed(0)}
                </p>
              </>
            ) : (
              <p className="text-xs text-fulkro-ink-500">Sin datos</p>
            )}
          </article>

          {/* Alertas globales mini widget · reuse listActiveAlertsGlobal */}
          <article
            className="rounded-lg border border-fulkro-ink-200 bg-fulkro-ink-50/50 p-4 transition-colors hover:border-fulkro-warning/40 hover:bg-white"
            data-testid="cross-client-alerts-widget"
          >
            <header className="mb-2 flex items-start justify-between gap-2">
              <h3 className="text-sm font-bold text-fulkro-ink-900">
                Alertas globales
              </h3>
              <Bell
                className={cn(
                  "h-4 w-4",
                  (globalAlertsQuery.data?.length ?? 0) > 0
                    ? "text-fulkro-warning"
                    : "text-fulkro-ink-400",
                )}
                aria-hidden="true"
              />
            </header>
            {globalAlertsQuery.isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-fulkro-ink-400" />
            ) : (
              <>
                <p className="mb-1 text-2xl font-bold tabular-nums text-fulkro-ink-900">
                  {globalAlertsQuery.data?.length ?? 0}
                </p>
                <p className="text-xs text-fulkro-ink-600">
                  Cross-cliente abiertas ·{" "}
                  <Link
                    href="/admin/alerts"
                    className="text-fulkro-info hover:underline"
                  >
                    inbox completo
                  </Link>
                </p>
              </>
            )}
          </article>

          {/* Pipeline mini widget · reuse useDashboardKpis (leads + projects) */}
          <article
            className="rounded-lg border border-fulkro-ink-200 bg-fulkro-ink-50/50 p-4 transition-colors hover:border-fulkro-info/40 hover:bg-white"
            data-testid="cross-client-pipeline-widget"
          >
            <header className="mb-2 flex items-start justify-between gap-2">
              <h3 className="text-sm font-bold text-fulkro-ink-900">
                Pipeline activo
              </h3>
              <Briefcase
                className="h-4 w-4 text-fulkro-info"
                aria-hidden="true"
              />
            </header>
            {kpisQuery.isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-fulkro-ink-400" />
            ) : kpisQuery.data ? (
              <>
                <p className="mb-1 text-2xl font-bold tabular-nums text-fulkro-ink-900">
                  {kpisQuery.data.active_projects} proy.
                </p>
                <p className="text-xs text-fulkro-ink-600">
                  {kpisQuery.data.leads_count} lead
                  {kpisQuery.data.leads_count === 1 ? "" : "s"} · valor €
                  {kpisQuery.data.leads_value_eur.toFixed(0)}
                </p>
              </>
            ) : (
              <p className="text-xs text-fulkro-ink-500">Sin datos</p>
            )}
          </article>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {/* Self-monitoring · 17 checks platform global */}
        <PortalCard
          title="Self-monitoring FULKRO"
          description="17 checks autónomos sobre la propia plataforma · alertas + reportes semanales/mensuales."
          href="/admin/compliance/monitor"
          icon={Activity}
          testid="compliance-portal-monitor"
          summary={
            monitorQuery.isLoading ? (
              <p className="flex items-center gap-2 text-xs text-fulkro-ink-500">
                <Loader2 className="h-3 w-3 animate-spin" /> Cargando estado…
              </p>
            ) : monitorQuery.data ? (
              <div className="space-y-1 text-xs">
                <p className="font-medium">
                  Estado general:{" "}
                  <span
                    className={cn(
                      monitorQuery.data.overall === "green" && "text-fulkro-success",
                      monitorQuery.data.overall === "yellow" && "text-fulkro-warning",
                      monitorQuery.data.overall === "red" && "text-fulkro-danger",
                      monitorQuery.data.overall === "unknown" && "text-fulkro-ink-500",
                    )}
                  >
                    {monitorQuery.data.overall === "green" && "✓ OK"}
                    {monitorQuery.data.overall === "yellow" && "⚠ Avisos"}
                    {monitorQuery.data.overall === "red" && "✕ Críticos"}
                    {monitorQuery.data.overall === "unknown" && "? Sin datos"}
                  </span>
                </p>
                <p className="text-fulkro-ink-500">
                  {monitorQuery.data.open_alerts ?? 0} alertas abiertas
                </p>
              </div>
            ) : (
              <p className="text-xs text-fulkro-ink-500">
                Estado no disponible · entra para detalle.
              </p>
            )
          }
          badge={
            monitorQuery.data?.overall === "red"
              ? { label: "Críticos", tone: "warning" }
              : monitorQuery.data?.overall === "yellow"
                ? { label: "Avisos", tone: "info" }
                : monitorQuery.data?.overall === "green"
                  ? { label: "OK", tone: "success" }
                  : undefined
          }
        />

        {/* Cross-project compliance · Bloque 4 Phase B */}
        <PortalCard
          title="Compliance multi-cliente"
          description="Salud de cumplimiento agregada por proyecto cliente · cross-motor (M27 conformidad · M04 gaps · evidencias)."
          href="/admin/compliance/projects"
          icon={ShieldCheck}
          testid="compliance-portal-projects"
          summary={
            projectsQuery.isLoading ? (
              <p className="flex items-center gap-2 text-xs text-fulkro-ink-500">
                <Loader2 className="h-3 w-3 animate-spin" /> Cargando proyectos…
              </p>
            ) : projectsQuery.data ? (
              <div className="space-y-1 text-xs">
                <p className="font-medium">
                  {projectsQuery.data.total_projects} proyectos activos
                </p>
                <div className="flex flex-wrap items-center gap-2 text-fulkro-ink-500">
                  {projectsQuery.data.counts_by_health.critical > 0 ? (
                    <span className="inline-flex items-center gap-1 text-fulkro-danger">
                      <AlertTriangle className="h-3 w-3" />
                      {projectsQuery.data.counts_by_health.critical} críticos
                    </span>
                  ) : null}
                  {projectsQuery.data.counts_by_health.warning > 0 ? (
                    <span className="text-fulkro-warning">
                      {projectsQuery.data.counts_by_health.warning} avisos
                    </span>
                  ) : null}
                  {projectsQuery.data.counts_by_health.ok > 0 ? (
                    <span className="inline-flex items-center gap-1 text-fulkro-success">
                      <CheckCircle2 className="h-3 w-3" />
                      {projectsQuery.data.counts_by_health.ok} OK
                    </span>
                  ) : null}
                </div>
              </div>
            ) : (
              <p className="text-xs text-fulkro-ink-500">
                Datos no disponibles · entra para detalle.
              </p>
            )
          }
        />

        {/* Norma-specific reports */}
        <PortalCard
          title="Informes por normativa"
          description="Reportes generados por marco normativo: ENS · RGPD · NIS2 · DORA · AI Act."
          href="/admin/compliance/norma-reports"
          icon={FileText}
          testid="compliance-portal-norma-reports"
          summary={
            <p className="text-xs text-fulkro-ink-700">
              Consulta reportes oficiales por cada normativa aplicable a tus
              clientes. Útil para auditorías ENAC y entregables a stakeholders.
            </p>
          }
        />

        {/* System health · platform global */}
        <PortalCard
          title="Salud del sistema"
          description="Estado técnico de la plataforma FULKRO · DB · LLM observability · checks compliance."
          href="/admin/system-health"
          icon={Gavel}
          testid="compliance-portal-system-health"
          summary={
            <p className="text-xs text-fulkro-ink-700">
              Self-monitoring técnico de la plataforma · útil cuando los clientes
              te preguntan por uptime o cuando preparas la auditoría bienal del
              propio FULKRO.
            </p>
          }
        />
      </div>

      <footer className="border-t border-fulkro-ink-200 pt-4 text-xs text-fulkro-ink-500">
        <p>
          🛡 Pre-cert auditor ENAC: la plataforma FULKRO cumple ENS Medio sobre
          sí misma · dogfooding sostained · Regla inviolable #7.
        </p>
      </footer>
    </div>
  );
}
