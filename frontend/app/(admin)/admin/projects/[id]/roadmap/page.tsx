/**
 * Admin · /admin/projects/[id]/roadmap (sub-bloque 8.B.5 FASE 8 · ADR-026).
 *
 * Layout 70/30:
 * - Left: RoadmapView (PhaseStepper + PhaseCards) + CopilotGuidedFlow (Sesión 3A B.2)
 * - Right: NextActionCard list (top 5 priority)
 */
"use client";

import { Loader2 } from "lucide-react";

import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { NextActionCard } from "@/components/workflow/NextActionCard";
import { RoadmapView } from "@/components/workflow/RoadmapView";
import { useNextActions, useRoadmap } from "@/hooks/useWorkflowAdmin";

export default function ProjectRoadmapPage({
  params,
}: {
  params: { id: string };
}) {
  const projectId = params.id;
  const roadmapQuery = useRoadmap(projectId);
  const actionsQuery = useNextActions(projectId, 5);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_340px]">
      <section className="space-y-5">
        <header>
          <h2>Roadmap del proyecto</h2>
          <p className="mt-1 text-base font-medium text-[color:var(--fulkro-body)]">
            10 fases lifecycle ENS · estado y progreso por fase.
          </p>
        </header>
        <CopilotGuidedFlow
          phaseId="roadmap-overview"
          title="Cómo funciona el roadmap ENS"
          intro="El roadmap te lleva paso a paso por las 10 fases del ENS: desde categorizar el sistema hasta el retainer post-certificación. Cada fase desbloquea la siguiente cuando los hitos están firmados."
          whyImportant="Saltarse fases o adelantar trabajo sin haber firmado lo anterior genera problemas en auditoría ENAC. El roadmap garantiza trazabilidad y cumplimiento RD 311/2022."
          steps={[
            {
              label: "Empieza por Categorización",
              detail: "M01 + 19 dimensiones · firma E-012 acta de categorización",
            },
            {
              label: "Análisis de riesgos MAGERIT",
              detail: "M02 + M19 · catálogo amenazas + salvaguardas mapeadas Anexo II",
            },
            {
              label: "Plan de adecuación y DdA",
              detail: "M04 plan + M03 73 medidas + firma cliente Ed25519",
            },
            {
              label: "Implantación + Verificación",
              detail: "M06/M07 docs + evidencias · M08 pentest si MEDIA/ALTA",
            },
            {
              label: "Conformidad + Retainer",
              detail: "M27 declaración E-041 · M23 retainer mensual post-cert",
            },
          ]}
          commonMistakes={[
            "Saltar Categorización para 'ahorrar tiempo': el resto depende de la categoría firmada",
            "Generar DdA antes de MAGERIT: las medidas quedan sin trazar a riesgo real",
            "Cancelar retainer post-cert: la re-auditoría bienal lo encarece 3-5x",
          ]}
          estimatedTime="Calendar realista: BÁSICA 4-6 semanas · MEDIA 8-10 semanas · ALTA 12-16 semanas"
          helpTopics={[
            { label: "Guía completa por fases", href: "/docs/copilot/phase-explanations.md", external: true },
            { label: "Pregunta al copiloto FULKRO", href: "#copilot-dock" },
          ]}
          nextAction={{
            label: "Ir a Categorización",
            targetUrl: `/admin/projects/${projectId}/dimensiones`,
          }}
        />
        {roadmapQuery.isLoading ? (
          <div className="flex h-32 items-center justify-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
            <Loader2 size={18} className="animate-spin" /> cargando roadmap…
          </div>
        ) : roadmapQuery.data ? (
          <RoadmapView roadmap={roadmapQuery.data} />
        ) : (
          <p className="text-base font-medium text-[color:var(--fulkro-muted)]">
            No se pudo cargar el roadmap.
          </p>
        )}
      </section>

      <aside>
        <header className="mb-5">
          <h3 className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
            Próximas acciones
          </h3>
        </header>
        {actionsQuery.isLoading ? (
          <div className="flex h-24 items-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
            <Loader2 size={16} className="animate-spin" /> cargando…
          </div>
        ) : actionsQuery.data && actionsQuery.data.length > 0 ? (
          <div className="flex flex-col gap-3">
            {actionsQuery.data.map((action) => (
              <NextActionCard key={action.action_id} action={action} />
            ))}
          </div>
        ) : (
          <p className="text-base font-medium text-[color:var(--fulkro-muted)]">
            No hay acciones pendientes para esta fase.
          </p>
        )}
      </aside>
    </div>
  );
}
