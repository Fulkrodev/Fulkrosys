/**
 * /admin/projects/[id]/dimensiones · sub-atom 1.C.D.A.0.2 v3.8.
 *
 * Page admin consolidada · 19 dimensiones del proyecto (Anexo L plan v3.8).
 * Marcos completa wizard 5 steps + 1 resumen · single source of truth.
 *
 * Capture distribuida natural en paralelo:
 *   - m13_commercial proposal_service · dims comerciales pre-venta
 *   - m_meetings actions · dims básicas reunión exploratoria
 *   - m16_onboarding · cliente onboarding completa subset
 *
 * Cualquier dim editable cualquier momento desde esta page · sostiene
 * R23 (project-scoped UI) + R24.a (admin source of truth) + R30 (tooltips
 * ENS asume cero conocimiento técnico).
 */
import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { DimensionsWizardPanel } from "@/components/dimensions/DimensionsWizardPanel";

export const metadata = {
  title: "Dimensiones del proyecto · FULKRO",
};

export default function DimensionsPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-foreground">
          Dimensiones del proyecto
        </h1>
        <p className="text-sm text-muted-foreground">
          19 dimensiones de adaptación que drive el workflow. Captura
          distribuida (m13 pre-venta · m16 onboarding cliente) consolidada
          aquí · Marcos puede editar cualquiera cualquier momento.
        </p>
      </header>
      <CopilotGuidedFlow {...PHASE_GUIDES.dimensiones(params.id)} />
      <DimensionsWizardPanel projectId={params.id} />
    </div>
  );
}
