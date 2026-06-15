"use client";

/**
 * /client-portal/cumplimiento · Cliente UI Bloque 4 Phase A v3.12.
 *
 * Resumen de cumplimiento per-project aggregator cross-motor (5 áreas):
 *   - Conformidad (M27)
 *   - Mejoras propuestas (Bloque 3+5 cloud remediations)
 *   - Tareas pendientes (M21)
 *   - Documentos a subir (M07 evidencias)
 *   - Temas críticos abiertos (M04 gaps)
 *
 * Backend aggregator endpoint NEW: GET /api/v1/client-portal/compliance-summary
 * Refetch 60s automático · staleTime 30s · friendly Spanish R29.
 */
import { ShieldCheck } from "lucide-react";

import { ComplianceSummaryCard } from "@/components/client-portal/compliance/ComplianceSummaryCard";
import { PageContainer } from "@/components/layout/PageContainer";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useClientComplianceSummary } from "@/hooks/useClientComplianceSummary";
import {
  HEALTH_LABELS,
  HEALTH_VARIANTS,
  type HealthIndicator,
} from "@/lib/api/client-compliance-summary";

function overallHeadline(status: HealthIndicator): string {
  if (status === "ok") return "¡Todo al día!";
  if (status === "warning") return "Algunas cosas a revisar";
  if (status === "critical") return "Hay temas que necesitan tu atención";
  return "Estamos cargando tu resumen";
}

export default function CumplimientoPage() {
  const query = useClientComplianceSummary();
  const data = query.data;
  const areas = data?.areas ?? [];

  return (
    <PageContainer variant="reading">
      <div className="space-y-6">
        <header className="space-y-2">
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-emerald-700" />
          Resumen de cumplimiento
        </h1>
        <p className="text-sm text-muted-foreground">
          Aquí ves cómo va tu proyecto · sin tecnicismos. Si algo necesita tu
          atención, te lo decimos amablemente.
        </p>
      </header>

      {query.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : query.isError ? (
        <Alert variant="danger">
          <AlertTitle>No pudimos cargar el resumen</AlertTitle>
          <AlertDescription>
            Recarga la página · si sigue pasando avisa a Marcos.
          </AlertDescription>
        </Alert>
      ) : !data || areas.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck className="h-12 w-12" />}
          title="Aún no tenemos resumen"
          description="Cuando Marcos genere los primeros datos te aparecerán aquí. Sin prisa."
        />
      ) : (
        <>
          {/* Overall headline */}
          <div
            className="rounded-lg border bg-card p-4 flex items-center gap-3"
            data-testid="overall-headline"
            data-overall={data.overall_health}
          >
            <div className="flex-1">
              <p className="text-base font-medium">
                {overallHeadline(data.overall_health)}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Actualizado · {new Date(data.generated_at).toLocaleString("es-ES")}
              </p>
            </div>
            <Badge variant={HEALTH_VARIANTS[data.overall_health]}>
              {HEALTH_LABELS[data.overall_health]}
            </Badge>
          </div>

          {/* Per-area cards */}
          <div className="space-y-3" data-testid="areas-list">
            {areas.map((a) => (
              <ComplianceSummaryCard key={a.area_key} area={a} />
            ))}
          </div>
        </>
      )}
      </div>
    </PageContainer>
  );
}
