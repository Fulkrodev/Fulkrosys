/**
 * Cliente · /client-portal/workflow (sub-atom 1.C.D.C.1 v3.8 REMODELADO ENRICHED).
 *
 * Vista cronológica friendly mono · subset enriched cliente:
 *   - WorkflowProgressBarClient (celebratory · NO countdown coercitivo)
 *   - WorkflowGuideTimelineClient (3 sections COMPLETADO · TU SIGUIENTE PASO · PRÓXIMOS PASOS)
 *
 * Consume endpoint workflow-guide (m_workflow_engine 1.C.D.A) · EnrichedStepState
 * con description_detailed_es + rationale_es + deliverable_codes + tooltips_ens.
 *
 * Histórico previo (8.B.6 FASE 8 ADR-026) usaba RoadmapView + NextActionCard
 * sobre portal_workflow endpoints (4 phases legacy). REMODELADO v3.8:
 *   - REUSE existing route /client-portal/workflow (sidebar "Mi proyecto" link)
 *   - REPLACE contenido con workflow-guide v3.8 enriched (NO route paralela)
 *   - Sostiene cleanup pages obsoletas autorizado + OPS-045 reveal infra existing.
 *
 * R29 sostenido empíricamente (audit pre-commit):
 *   ✅ Empty states celebratorios encouraging
 *   ✅ Mensajes progreso positivos
 *   ❌ NO push notifications inactividad
 *   ❌ NO deadlines coercitivos
 *   ❌ NO polling agresivo (STALE_TIME 60s vs 30s admin)
 */
"use client";

import { useEffect, useState } from "react";
import { Loader2, Lock } from "lucide-react";
import { useRouter } from "next/navigation";

import { ClientNextActionCard } from "@/components/client-portal/workflow/ClientNextActionCard";
import { ClientUnblockedBanner } from "@/components/client-portal/workflow/ClientUnblockedBanner";
import { MarcosPreparaSection } from "@/components/client-portal/workflow/MarcosPreparaSection";
import { EmptyState } from "@/components/ui/empty-state";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { WorkflowFAQContextual } from "@/components/workflow-guide-client/WorkflowFAQContextual";
import { WorkflowGuideTimelineClient } from "@/components/workflow-guide-client/WorkflowGuideTimelineClient";
import { WorkflowProgressBarClient } from "@/components/workflow-guide-client/WorkflowProgressBarClient";
import { WorkflowStepDetailDrawerClient } from "@/components/workflow-guide-client/WorkflowStepDetailDrawerClient";
import { useClientWorkflowGuide } from "@/hooks/useClientWorkflowGuide";
import type { EnrichedStepState } from "@/lib/api/client-workflow-guide";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";

interface ProjectInfo {
  id?: string;
  nombre?: string;
}

type LoadErrorVariant = "limited_access" | "no_project" | "generic";

export default function ClientWorkflowPage() {
  const router = useRouter();
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<LoadErrorVariant | null>(null);
  const [detailStep, setDetailStep] = useState<EnrichedStepState | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const openDetail = (step: EnrichedStepState) => {
    setDetailStep(step);
    setDetailOpen(true);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const proj = await clientApi<ProjectInfo>("/client-portal/project");
        if (cancelled) return;
        if (proj.id) {
          setProjectId(proj.id);
        } else {
          setLoadError("limited_access");
        }
        setProjectName(proj.nombre ?? null);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ClientApiError && err.status === 404) {
          setLoadError("no_project");
        } else {
          setLoadError("generic");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const guideQuery = useClientWorkflowGuide(projectId);

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-6 py-8">
      <header className="flex flex-col gap-2">
        <p className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
          Mi proyecto
        </p>
        <h1 className="flex flex-wrap items-center gap-2">
          {projectName ?? (
            <>
              Tu workflow <TooltipENS term="ENS" />
            </>
          )}
        </h1>
        {guideQuery.data ? (
          <p className="text-base font-medium text-[color:var(--fulkro-body)]">
            Estamos en la fase{" "}
            <span className="font-bold text-[color:var(--fulkro-title)]">
              {guideQuery.data.fase}
            </span>
            .
          </p>
        ) : null}
      </header>

      {loadError === "limited_access" ? (
        <div className="card p-2">
          <EmptyState
            icon={
              <Lock
                size={48}
                strokeWidth={2.3}
                className="text-[color:var(--fulkro-subtitle)]"
              />
            }
            title="Acceso limitado al proyecto"
            description="Tu rol actual no permite ver todos los detalles. Contacta con tu consultor para ampliar permisos."
            action={{
              label: "Contactar consultor",
              variant: "primary",
              onClick: () => router.push("/client-portal/inbox"),
            }}
            className="py-16"
          />
        </div>
      ) : null}

      {loadError === "no_project" ? (
        <div className="card p-2">
          <EmptyState
            icon={
              <Lock
                size={48}
                strokeWidth={2.3}
                className="text-[color:var(--fulkro-subtitle)]"
              />
            }
            title="Sin proyecto asociado"
            description="No hay proyecto asociado a tu cuenta. Contacta con tu consultor."
            action={{
              label: "Contactar consultor",
              variant: "primary",
              onClick: () => router.push("/client-portal/inbox"),
            }}
            className="py-16"
          />
        </div>
      ) : null}

      {loadError === "generic" ? (
        <div className="card p-2">
          <EmptyState
            icon={
              <Lock
                size={48}
                strokeWidth={2.3}
                className="text-[color:var(--fulkro-subtitle)]"
              />
            }
            title="Estamos teniendo problemas técnicos"
            description="Prueba refrescar la página. Si el problema persiste · contacta con Marcos."
            action={{
              label: "Contactar consultor",
              variant: "primary",
              onClick: () => router.push("/client-portal/inbox"),
            }}
            className="py-16"
          />
        </div>
      ) : null}

      {!projectId && !loadError ? (
        <div className="flex h-32 items-center justify-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
          <Loader2 size={18} className="animate-spin" /> cargando tu proyecto…
        </div>
      ) : null}

      {projectId && guideQuery.isLoading ? (
        <div className="flex h-32 items-center justify-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
          <Loader2 size={18} className="animate-spin" /> cargando workflow…
        </div>
      ) : null}

      {projectId && guideQuery.data ? (
        <>
          {/* 1.D.G.E · banner real-time SSE unblocked event */}
          <ClientUnblockedBanner
            projectId={projectId}
            ctaUrlResolver={(tid) => {
              const all = [
                ...(guideQuery.data!.current_step
                  ? [guideQuery.data!.current_step]
                  : []),
                ...guideQuery.data!.proximos,
              ];
              return all.find((s) => s.template_id === tid)?.cta_url ??
                undefined;
            }}
          />

          {/* 1.D.G.E · Tu siguiente acción · CTA prominent */}
          <ClientNextActionCard step={guideQuery.data.current_step} />

          {/* 1.D.G.E · Lo que Marcos está preparando · informational R29 */}
          <MarcosPreparaSection
            steps={[
              ...(guideQuery.data.current_step
                ? [guideQuery.data.current_step]
                : []),
              ...guideQuery.data.proximos,
            ]}
          />

          <WorkflowProgressBarClient
            pct={guideQuery.data.progress.global_pct}
            completed={guideQuery.data.progress.global_completed}
            total={guideQuery.data.progress.global_total}
          />

          <WorkflowGuideTimelineClient
            completed={guideQuery.data.completed}
            currentStep={guideQuery.data.current_step}
            proximos={guideQuery.data.proximos}
            onOpenDetail={openDetail}
          />

          <WorkflowFAQContextual
            onOpenCopiloto={() =>
              window.dispatchEvent(new Event("fulkro:open-cliente-copiloto"))
            }
          />

          <WorkflowStepDetailDrawerClient
            step={detailStep}
            projectId={projectId ?? undefined}
            open={detailOpen}
            onOpenChange={setDetailOpen}
          />
        </>
      ) : null}
    </main>
  );
}
