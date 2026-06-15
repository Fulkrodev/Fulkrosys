"use client";

/**
 * /client-portal/remediaciones · Cliente UI Bloque 3+5 v3.12.
 *
 * Lista de propuestas de remediation enviadas por Marcos (admin):
 *   - GET /api/v1/client-portal/cloud-gaps · cliente-scoped via require_client_user
 *   - 3 secciones: pendientes de tu decisión · en progreso · ya resueltas
 *   - SSE real-time updates via useClientProjectEvents (extend cloud_remediation_*)
 *   - Click "Revisar y decidir" → ApprovalModal
 *
 * R29 firmísimo · friendly Spanish · NO presión · NUNCA jerga técnica.
 * Cross-project isolation backend-enforced (require_client_user + project_id resolve).
 */
import { useMemo, useState } from "react";
import { ShieldCheck } from "lucide-react";

import { ApprovalModal } from "@/components/client-portal/remediations/ApprovalModal";
import { RemediationCard } from "@/components/client-portal/remediations/RemediationCard";
import { RemediationClienteView } from "@/components/remediation/RemediationClienteView";
import { PageContainer } from "@/components/layout/PageContainer";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  REMEDIATIONS_QUERY_KEY,
  useClientRemediations,
} from "@/hooks/useClientCloudRemediations";
import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import type { RemediationGap } from "@/lib/api/client-cloud-remediations";

export default function RemediacionesPage() {
  const remediationsQuery = useClientRemediations();
  const [selected, setSelected] = useState<RemediationGap | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  // SSE real-time updates · refetch al recibir cualquier cloud_remediation_*
  useClientProjectEvents(remediationsQuery.data?.project_id ?? null, {
    invalidateQueries: [REMEDIATIONS_QUERY_KEY as unknown as string[]],
    onCloudRemediationProposed: () => {
      /* invalidation suffices · UI re-renders */
    },
    onCloudRemediationExecuting: () => {
      /* invalidation suffices */
    },
    onCloudRemediationExecuted: () => {
      /* invalidation suffices */
    },
    onCloudRemediationFailed: () => {
      /* invalidation suffices */
    },
  });

  const gaps = remediationsQuery.data?.gaps ?? [];

  const { pendientes, enProgreso, resueltas } = useMemo(() => {
    return {
      pendientes: gaps.filter((g) => g.approval_status === "proposed_to_cliente"),
      enProgreso: gaps.filter((g) =>
        ["approved", "executing"].includes(g.approval_status),
      ),
      resueltas: gaps.filter((g) =>
        ["executed", "failed"].includes(g.approval_status),
      ),
    };
  }, [gaps]);

  const openModal = (gap: RemediationGap) => {
    setSelected(gap);
    setModalOpen(true);
  };

  return (
    <PageContainer variant="reading">
      <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-amber-600" />
          Mejoras propuestas
        </h1>
        <p className="text-sm text-muted-foreground">
          Aquí ves las mejoras que Marcos te propone aplicar sobre tu cloud. Tú
          decides si autorizas · si tienes dudas, escríbele desde el chat.
        </p>
      </header>

      {remediationsQuery.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : remediationsQuery.isError ? (
        <Alert variant="danger">
          <AlertTitle>No pudimos cargar las propuestas</AlertTitle>
          <AlertDescription>
            Recarga la página · si sigue pasando avisa a Marcos.
          </AlertDescription>
        </Alert>
      ) : gaps.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck className="h-12 w-12" />}
          title="Sin mejoras propuestas todavía"
          description="Cuando Marcos detecte algo a mejorar te aparecerá aquí. Sin prisa por tu parte."
        />
      ) : (
        <div className="space-y-8" data-testid="remediations-list">
          {pendientes.length > 0 && (
            <section data-testid="section-pendientes">
              <h2 className="text-base font-medium mb-3">
                Pendientes de tu decisión · {pendientes.length}
              </h2>
              <div className="space-y-3">
                {pendientes.map((g) => (
                  <RemediationCard
                    key={g.id}
                    gap={g}
                    onReview={openModal}
                  />
                ))}
              </div>
            </section>
          )}

          {enProgreso.length > 0 && (
            <section data-testid="section-en-progreso">
              <h2 className="text-base font-medium mb-3 text-muted-foreground">
                Marcos las está aplicando · {enProgreso.length}
              </h2>
              <div className="space-y-3">
                {enProgreso.map((g) => (
                  <RemediationCard
                    key={g.id}
                    gap={g}
                    onReview={openModal}
                  />
                ))}
              </div>
            </section>
          )}

          {resueltas.length > 0 && (
            <section data-testid="section-resueltas">
              <h2 className="text-base font-medium mb-3 text-muted-foreground">
                Ya resueltas · {resueltas.length}
              </h2>
              <div className="space-y-3">
                {resueltas.map((g) => (
                  <RemediationCard
                    key={g.id}
                    gap={g}
                    onReview={openModal}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      <ApprovalModal
        gap={selected}
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setSelected(null);
        }}
      />

      {/* ADR-055 · remediación automática (cloud safe-auto + guarded autorizado) */}
      <div className="mt-8 border-t border-slate-200 pt-6">
        <RemediationClienteView />
      </div>
      </div>
    </PageContainer>
  );
}
