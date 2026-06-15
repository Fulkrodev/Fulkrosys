"use client";

/**
 * /client-portal/incidents · SAN-E v3.MB-6 atom 3.
 *
 * CCN-STIC 817 cliente review + close signoff workflow.
 * Cliente VE solo workflow_state IN (resolved · closed) · Q4 cement.
 *
 * Layout:
 *  1. Header + counters (resolved · closed · pending review)
 *  2. List incidents (filterable) + Detail panel side-by-side
 */
import { AlertCircle, AlertTriangle, ShieldAlert } from "lucide-react";
import { useState } from "react";

import { IncidentCard } from "@/components/client-portal/incidents/IncidentCard";
import { IncidentDetail } from "@/components/client-portal/incidents/IncidentDetail";
import { AgentSuggestionBanner } from "@/components/client-portal/inline-agents/AgentSuggestionBanner";
import { PageContainer } from "@/components/layout/PageContainer";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useIncidentsClient } from "@/hooks/useIncidentsClient";

export default function IncidentsPage() {
  const {
    loading,
    error,
    incidents,
    reviewIncidentAction,
    refetch,
  } = useIncidentsClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const resolved = incidents.filter((i) => i.workflow_state === "resolved");
  const closed = incidents.filter((i) => i.workflow_state === "closed");
  const pendingReview = resolved.filter(
    (i) => i.client_review_status !== "revisada_ok",
  );
  const selected =
    incidents.find((i) => i.id === selectedId) ?? incidents[0] ?? null;

  return (
    <PageContainer variant="reading">
      <div className="space-y-6 pb-32">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-fulkro-primary-700">
          <AlertTriangle className="h-5 w-5" aria-hidden />
          <span className="text-xs uppercase tracking-wide font-semibold">
            Portal cliente · Incidentes seguridad
          </span>
        </div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-fulkro-ink-800">
          Incidentes y notificaciones <TooltipENS term="CCN_CERT" />
        </h1>
        <p className="text-sm text-fulkro-ink-600 max-w-3xl">
          Marcos gestiona los incidents de seguridad internamente. Cuando un
          incidente se resuelve, lo verás aquí para revisar y firmar el cierre.
          Si el incidente requiere notificación{" "}
          <TooltipENS term="CCN_CERT" /> (art op.exp.10{" "}
          <TooltipENS term="ENS" />), te indicaremos cómo proceder según el
          routing automático.
        </p>
      </header>

      <AgentSuggestionBanner
        slug="a11_auditor_virtual_check"
        pageUrl="/client-portal/incidents"
        dismissKey="incidents_auditor_dismissed"
        tierGatedNote="Verificación cross-doc del auditor virtual disponible desde categoría MEDIA."
      />

      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {error && (
        <Card className="p-5 border-destructive/40 bg-destructive/5">
          <div className="flex items-start gap-2 text-sm">
            <AlertCircle
              className="h-5 w-5 mt-0.5 text-destructive flex-shrink-0"
              aria-hidden
            />
            <div>
              <div className="font-semibold text-destructive">
                Error cargando incidents
              </div>
              <p className="text-fulkro-ink-600 mt-1">{error}</p>
            </div>
          </div>
        </Card>
      )}

      {!loading && !error && (
        <>
          <Card className="p-5">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-xs text-fulkro-ink-500 uppercase tracking-wide">
                  Resueltos pendientes review
                </div>
                <div className="text-2xl font-bold text-fulkro-warning mt-1 font-mono tabular-nums">
                  {pendingReview.length}
                </div>
              </div>
              <div>
                <div className="text-xs text-fulkro-ink-500 uppercase tracking-wide">
                  Resueltos
                </div>
                <div className="text-2xl font-bold text-fulkro-info mt-1 font-mono tabular-nums">
                  {resolved.length}
                </div>
              </div>
              <div>
                <div className="text-xs text-fulkro-ink-500 uppercase tracking-wide">
                  Cerrados (firmados)
                </div>
                <div className="text-2xl font-bold text-fulkro-success mt-1 font-mono tabular-nums">
                  {closed.length}
                </div>
              </div>
            </div>
          </Card>

          {incidents.length === 0 && (
            <Card className="p-5">
              <div className="flex items-start gap-2 text-sm text-fulkro-ink-600">
                <ShieldAlert
                  className="h-5 w-5 mt-0.5 text-fulkro-success flex-shrink-0"
                  aria-hidden
                />
                <div>
                  <div className="font-semibold text-fulkro-ink-800">
                    Sin incidents visibles
                  </div>
                  <p className="mt-1">
                    No hay incidentes resueltos ni cerrados que requieran tu
                    revisión. Los incidents en triaje o investigación los
                    gestiona Marcos internamente.
                  </p>
                </div>
              </div>
            </Card>
          )}

          {incidents.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                {incidents.map((i) => (
                  <IncidentCard
                    key={i.id}
                    incident={i}
                    onSelect={setSelectedId}
                    selected={(selected?.id ?? null) === i.id}
                  />
                ))}
              </div>
              {selected && (
                <IncidentDetail
                  incident={selected}
                  onReview={reviewIncidentAction}
                  onSigningComplete={refetch}
                />
              )}
            </div>
          )}
        </>
      )}
      </div>
    </PageContainer>
  );
}
