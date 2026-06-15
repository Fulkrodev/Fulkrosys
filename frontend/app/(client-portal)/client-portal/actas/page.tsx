"use client";

/**
 * /client-portal/actas · SAN-E v3.MB-6 atom 5.
 *
 * Actas 4 tipos signable · cliente revisa + firma. Layout:
 *  1. Header
 *  2. Filter chips subtype (sub-Q3 cement · sticky horizontal mobile)
 *  3. Empty state si NO actas visibles
 *  4. List ActaCard + Detail panel side-by-side (mobile: stacked)
 */
import { AlertCircle, FileText } from "lucide-react";
import { useState } from "react";

import { ActaCard } from "@/components/client-portal/actas/ActaCard";
import { ActaDetail } from "@/components/client-portal/actas/ActaDetail";
import { PageContainer } from "@/components/layout/PageContainer";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type ActaSubtype,
  ACTA_SUBTYPES,
  ACTA_SUBTYPE_SHORT_LABELS,
} from "@/lib/api/actas";
import { useActasClient } from "@/hooks/useActasClient";
import { cn } from "@/lib/utils";

const FILTER_CHIPS: Array<{ value: ActaSubtype | null; label: string }> = [
  { value: null, label: "Todas" },
  ...ACTA_SUBTYPES.map((s) => ({
    value: s,
    label: ACTA_SUBTYPE_SHORT_LABELS[s],
  })),
];

export default function ActasPage() {
  const {
    loading,
    error,
    actas,
    subtypeFilter,
    setSubtypeFilter,
    reviewActaAction,
    refetch,
  } = useActasClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = actas.find((a) => a.id === selectedId) ?? actas[0] ?? null;

  return (
    <PageContainer variant="app">
      <div className="space-y-6 pb-32">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-fulkro-primary-700">
          <FileText className="h-5 w-5" aria-hidden />
          <span className="text-xs uppercase tracking-wide font-semibold">
            Portal cliente · Actas
          </span>
        </div>
        <h1 className="text-2xl font-bold text-fulkro-ink-800">
          Actas reuniones
        </h1>
        <p className="text-sm text-fulkro-ink-600 max-w-3xl">
          Actas de comité, kickoff, auditoría y cierre del proyecto. Cada acta
          llega curada por Marcos y queda firmada por ti para asegurar la
          trazabilidad.
        </p>
      </header>

      <div
        data-testid="subtype-filter-chips"
        className="flex flex-nowrap gap-2 overflow-x-auto pb-1 -mx-1 px-1 sticky top-0 bg-white z-10"
      >
        {FILTER_CHIPS.map((chip) => {
          const active = subtypeFilter === chip.value;
          return (
            <button
              key={chip.value ?? "all"}
              type="button"
              data-testid={`subtype-chip-${chip.value ?? "all"}`}
              data-active={active}
              onClick={() => setSubtypeFilter(chip.value)}
              className={cn(
                "shrink-0 px-3 py-1.5 rounded-full border text-xs font-medium transition-colors",
                active
                  ? "bg-fulkro-primary-700 border-fulkro-primary-700 text-white"
                  : "bg-white border-fulkro-ink-200 text-fulkro-ink-700 hover:bg-fulkro-ink-50",
              )}
            >
              {chip.label}
            </button>
          );
        })}
      </div>

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
                Error cargando actas
              </div>
              <p className="text-fulkro-ink-600 mt-1">{error}</p>
            </div>
          </div>
        </Card>
      )}

      {!loading && !error && actas.length === 0 && (
        <Card className="p-5">
          <div className="flex items-start gap-3 text-sm">
            <AlertCircle
              className="h-5 w-5 mt-0.5 text-fulkro-info flex-shrink-0"
              aria-hidden
            />
            <div className="flex-1">
              <div className="font-semibold text-fulkro-ink-800">
                {subtypeFilter
                  ? `Sin actas de tipo "${ACTA_SUBTYPE_SHORT_LABELS[subtypeFilter]}"`
                  : "Sin actas disponibles"}
              </div>
              <p className="text-fulkro-ink-600 mt-1">
                Cuando Marcos envíe nuevas actas para tu revisión y firma,
                aparecerán aquí.
              </p>
            </div>
          </div>
        </Card>
      )}

      {!loading && !error && actas.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            {actas.map((a) => (
              <ActaCard
                key={a.id}
                acta={a}
                onSelect={setSelectedId}
                selected={(selected?.id ?? null) === a.id}
              />
            ))}
          </div>
          {selected && (
            <ActaDetail
              acta={selected}
              onReview={reviewActaAction}
              onSigningComplete={refetch}
            />
          )}
        </div>
      )}
      </div>
    </PageContainer>
  );
}
