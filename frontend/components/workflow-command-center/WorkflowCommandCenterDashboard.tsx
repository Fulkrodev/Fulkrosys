/**
 * WorkflowCommandCenterDashboard · 4 zones cronológicas · sub-atom 1.C.D.B.1 v3.8.
 *
 * Layout: Zone 1 🔴 Urgente HOY (hero) · Zone 2 🟡 Esta semana (cards) ·
 * Zone 3 🟢 En marcha (compact rows) · Zone 4 📅 Próximos 30d (forecast timeline).
 *
 * Auto-refresh 30s polling via useCommandCenterMultiClient hook.
 * Empty states NO genéricos (celebratory · onboarding).
 */
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import { useCommandCenterMultiClient } from "@/hooks/useWorkflowCommandCenter";

import { ForecastTimeline30d } from "./ForecastTimeline30d";
import { ProjectCardUrgent } from "./ProjectCardUrgent";
import { ProjectCardWeekly } from "./ProjectCardWeekly";
import { ProjectRowCompact } from "./ProjectRowCompact";

const URGENT_MAX_VISIBLE = 3;
const WEEKLY_MAX_VISIBLE = 5;

export function WorkflowCommandCenterDashboard() {
  const { data, isLoading, isError, error, refetch } =
    useCommandCenterMultiClient();

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (isError) {
    return (
      <div className="space-y-2 rounded-lg border border-destructive/30 bg-destructive/5 p-4">
        <p className="font-medium">No se pudo cargar el command center</p>
        <p className="text-sm text-foreground/70">
          {error instanceof Error ? error.message : String(error)}
        </p>
        <button
          onClick={() => refetch()}
          className="text-sm text-primary underline"
        >
          Reintentar
        </button>
      </div>
    );
  }

  if (!data) return null;

  const totalActive =
    data.urgentes_hoy.length +
    data.esta_semana.length +
    data.en_marcha.length +
    data.proximos_30d.length;

  if (totalActive === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center space-y-2">
          <p className="text-lg">📋 Aún no tienes proyectos activos</p>
          <p className="text-sm text-foreground/60">
            Crea el primer proyecto desde la sección de Clientes para empezar.
          </p>
        </CardContent>
      </Card>
    );
  }

  const urgentVisible = data.urgentes_hoy.slice(0, URGENT_MAX_VISIBLE);
  const urgentExtra = data.urgentes_hoy.length - URGENT_MAX_VISIBLE;
  const weeklyVisible = data.esta_semana.slice(0, WEEKLY_MAX_VISIBLE);
  const weeklyExtra = data.esta_semana.length - WEEKLY_MAX_VISIBLE;

  return (
    <div className="space-y-6">
      {/* Zone 1 · 🔴 URGENTE HOY · hero pinned top */}
      <section aria-labelledby="zone-urgente-heading">
        <header className="mb-3 flex items-center justify-between gap-3">
          <h2
            id="zone-urgente-heading"
            className="text-lg font-semibold flex items-center gap-2"
          >
            <span aria-hidden="true">🔴</span> Urgente hoy
            {data.urgentes_hoy.length > 0 && (
              <span className="text-sm font-normal text-foreground/60">
                · {data.urgentes_hoy.length}{" "}
                {data.urgentes_hoy.length === 1
                  ? "cliente requiere acción inmediata"
                  : "clientes requieren acción inmediata"}
              </span>
            )}
          </h2>
        </header>
        {data.urgentes_hoy.length === 0 ? (
          <Card className="border-emerald-200 bg-emerald-50/50 dark:bg-emerald-950/20">
            <CardContent className="py-6 text-center">
              <p className="text-base">
                ✨ Sin urgencias hoy · puedes focus en pipeline o trabajo profundo
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {urgentVisible.map((card) => (
              <ProjectCardUrgent key={card.project_id} card={card} />
            ))}
            {urgentExtra > 0 && (
              <p className="text-sm text-foreground/60 italic">
                + {urgentExtra} urgencia{urgentExtra === 1 ? "" : "s"} más
              </p>
            )}
          </div>
        )}
      </section>

      {/* Zone 2 · 🟡 ESTA SEMANA · cards */}
      {data.esta_semana.length > 0 && (
        <section aria-labelledby="zone-semana-heading">
          <header className="mb-3">
            <h2
              id="zone-semana-heading"
              className="text-lg font-semibold flex items-center gap-2"
            >
              <span aria-hidden="true">🟡</span> Esta semana
              <span className="text-sm font-normal text-foreground/60">
                · {data.esta_semana.length} pendiente
                {data.esta_semana.length === 1 ? "" : "s"} admin-side
              </span>
            </h2>
          </header>
          <div className="grid gap-2 md:grid-cols-2">
            {weeklyVisible.map((card) => (
              <ProjectCardWeekly key={card.project_id} card={card} />
            ))}
          </div>
          {weeklyExtra > 0 && (
            <p className="mt-2 text-sm text-foreground/60 italic">
              + {weeklyExtra} pendiente{weeklyExtra === 1 ? "" : "s"} más
            </p>
          )}
        </section>
      )}

      {/* Zone 3 · 🟢 EN MARCHA · compact rows */}
      {data.en_marcha.length > 0 && (
        <section aria-labelledby="zone-marcha-heading">
          <header className="mb-3">
            <h2
              id="zone-marcha-heading"
              className="text-lg font-semibold flex items-center gap-2"
            >
              <span aria-hidden="true">🟢</span> En marcha
              <span className="text-sm font-normal text-foreground/60">
                · {data.en_marcha.length} cliente
                {data.en_marcha.length === 1 ? "" : "s"} status verde
              </span>
            </h2>
          </header>
          <div className="space-y-2">
            {data.en_marcha.map((card) => (
              <ProjectRowCompact key={card.project_id} card={card} />
            ))}
          </div>
        </section>
      )}

      {/* Zone 4 · 📅 PRÓXIMOS 30 DÍAS · forecast timeline */}
      {data.proximos_30d.length > 0 && (
        <section aria-labelledby="zone-30d-heading">
          <Card>
            <CardHeader>
              <CardTitle id="zone-30d-heading" className="text-base">
                <span aria-hidden="true">📅</span> Próximos 30 días
                <span className="ml-2 text-sm font-normal text-foreground/60">
                  · forecast hitos
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ForecastTimeline30d cards={data.proximos_30d} />
            </CardContent>
          </Card>
        </section>
      )}
    </div>
  );
}

// ============================================================
// Loading skeleton · coherente con 4 zones structure
// ============================================================

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <section>
        <Skeleton className="h-6 w-48 mb-3" />
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      </section>
      <section>
        <Skeleton className="h-6 w-48 mb-3" />
        <div className="grid gap-2 md:grid-cols-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </section>
      <section>
        <Skeleton className="h-6 w-48 mb-3" />
        <Skeleton className="h-10 w-full mb-2" />
        <Skeleton className="h-10 w-full" />
      </section>
    </div>
  );
}
