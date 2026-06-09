"use client";

/**
 * /client-portal/retainer-checkin · SAN-E v3.MB-6 atom 4.
 *
 * Comité Retainer trimestral · cliente review + firma audit ENAC.
 *
 * Layout:
 *  1. Header + intro CCN-STIC 805 (trimestral cadencia uniforme)
 *  2. Empty state si NO checkins (Q5: redirect link retainer-offer)
 *  3. List CheckinCard + Detail panel side-by-side
 */
import { AlertCircle, CalendarCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { CheckinCard } from "@/components/client-portal/retainer-checkin/CheckinCard";
import { CheckinDetail } from "@/components/client-portal/retainer-checkin/CheckinDetail";
import { ClientDigestCard } from "@/components/client-portal/retainer-checkin/ClientDigestCard";
import { AgentSuggestionBanner } from "@/components/client-portal/inline-agents/AgentSuggestionBanner";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useRetainerCheckin } from "@/hooks/useRetainerCheckin";

export default function RetainerCheckinPage() {
  const { loading, error, checkins, reviewCheckinAction, refetch } =
    useRetainerCheckin();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = checkins.find((c) => c.id === selectedId) ?? checkins[0] ?? null;

  return (
    <div className="space-y-6 px-4 py-6 sm:px-6 md:px-8 max-w-6xl mx-auto pb-32">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-fulkro-primary-700">
          <CalendarCheck className="h-5 w-5" aria-hidden />
          <span className="text-xs uppercase tracking-wide font-semibold">
            Portal cliente · Comité Retainer
          </span>
        </div>
        <h1 className="text-2xl font-bold text-fulkro-ink-800">
          Comités trimestrales Retainer
        </h1>
        <p className="text-sm text-fulkro-ink-600 max-w-3xl">
          Revisión trimestral del estado de seguridad cross-motor: actividades,
          incidents, vulnerabilidades, normativa y cambios stakeholders. Cada
          comité llega curado por Marcos y queda firmado por ti con{" "}
          <TooltipENS term="OTP" /> step-up para asegurar la trazabilidad{" "}
          <TooltipENS term="ENAC" />.
        </p>
      </header>

      {/* Sub-atom 1.D.X.VERIFY 2b · digest mensual cliente R29 */}
      <ClientDigestCard />

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
                Error cargando comités retainer
              </div>
              <p className="text-fulkro-ink-600 mt-1">{error}</p>
            </div>
          </div>
        </Card>
      )}

      {!loading && !error && checkins.length === 0 && (
        <Card className="p-5">
          <div className="flex items-start gap-3 text-sm">
            <AlertCircle
              className="h-5 w-5 mt-0.5 text-fulkro-info flex-shrink-0"
              aria-hidden
            />
            <div className="flex-1">
              <div className="font-semibold text-fulkro-ink-800">
                Sin comités retainer programados
              </div>
              <p className="text-fulkro-ink-600 mt-1">
                Cuando tu proyecto entre en fase retainer activo, Marcos
                generará un comité trimestral automáticamente y aparecerá aquí
                para tu revisión y firma.
              </p>
              <Link
                href="/client-portal/firma"
                className="inline-flex items-center mt-3 text-sm font-medium text-fulkro-primary-700 hover:text-fulkro-primary-800 underline"
              >
                Más sobre la firma electrónica FULKRO
              </Link>
            </div>
          </div>
        </Card>
      )}

      {!loading && !error && checkins.length > 0 && (
        <>
          <AgentSuggestionBanner
            slug="a19_propuestas_justify"
            pageUrl="/client-portal/retainer-checkin"
            dismissKey="retainer_checkin_justify_dismissed"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
          <div className="space-y-2">
            {checkins.map((c) => (
              <CheckinCard
                key={c.id}
                checkin={c}
                onSelect={setSelectedId}
                selected={(selected?.id ?? null) === c.id}
              />
            ))}
          </div>
          {selected && (
            <CheckinDetail
              checkin={selected}
              onReview={reviewCheckinAction}
              onSigningComplete={refetch}
            />
          )}
          </div>
        </>
      )}
    </div>
  );
}
