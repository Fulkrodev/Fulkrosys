import { RecentActivityCard } from "@/components/admin/RecentActivityCard";
import { ActiveAlertsCard } from "@/components/dashboard/ActiveAlertsCard";
import { NextActionCard } from "@/components/dashboard/NextActionCard";
import { PhaseProgressWizard } from "@/components/dashboard/PhaseProgressWizard";
import { ProjectEventsWrapper } from "@/components/dashboard/ProjectEventsWrapper";
import { ReadinessScoreCard } from "@/components/dashboard/ReadinessScoreCard";
import { WorkflowBlockingAlert } from "@/components/dashboard/WorkflowBlockingAlert";
import { CategoryGate } from "@/components/feature-flags/CategoryGate";
import { ProjectSummaryView } from "@/components/project/ProjectSummary";

export default function ProjectSummaryPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <ProjectEventsWrapper projectId={params.id}>
      <div className="space-y-6">
        {/* Primary fold · wizard cronológico + next action */}
        <PhaseProgressWizard projectId={params.id} />
        <NextActionCard projectId={params.id} />

        {/* Workflow blocking alert · MB-17.5 · solo MEDIA+/ALTA usan
            blocking gates (BASICA tiene 0 features blocks_phase_transition).
            Wrapped en CategoryGate como filtro defensivo. */}
        <CategoryGate categories={["MEDIA", "ALTA"]}>
          <WorkflowBlockingAlert projectId={params.id} />
        </CategoryGate>

        {/* Secondary fold · 2 cards complementarias */}
        <div className="grid gap-4 md:grid-cols-2">
          <ReadinessScoreCard projectId={params.id} />
          <ActiveAlertsCard projectId={params.id} />
        </div>

        {/* SAN-D MB-19.16 cosecha · DEC-MB13-RECENT-ACTIVITY-CARD ·
            audit feed admin home (ClientUserAudit hash chain + ClientTask
            transitions). Encaja entre alerts/readiness y vista detalle. */}
        <RecentActivityCard projectId={params.id} />

        {/* Tertiary fold · vista detalle proyecto existing (preserved) */}
        <ProjectSummaryView projectId={params.id} />
      </div>
    </ProjectEventsWrapper>
  );
}
