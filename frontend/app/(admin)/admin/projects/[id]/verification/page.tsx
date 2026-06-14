import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { InfoTag } from "@/components/ui/info-tag";
import { AutopilotSection } from "@/components/verification/AutopilotSection";
import { DeltaReport } from "@/components/verification/DeltaReport";
import { ENSHeatmap } from "@/components/verification/ENSHeatmap";
import { FindingsTable } from "@/components/verification/FindingsTable";
import { HandoffButton } from "@/components/verification/HandoffButton";
import { KillSwitchButton } from "@/components/verification/KillSwitchButton";
import { LaunchVerificationButton } from "@/components/verification/LaunchVerificationButton";
import { RemediationPlan } from "@/components/verification/RemediationPlan";
import { RunsHistory } from "@/components/verification/RunsHistory";
import { SecurityScoreHeader } from "@/components/verification/SecurityScoreHeader";

export default function VerificationPage({
  params,
}: {
  params: { id: string };
}) {
  const projectId = params.id;
  return (
    <div className="flex flex-col gap-6" data-testid="verification-page">
      <CopilotGuidedFlow {...PHASE_GUIDES.verification(projectId)} />
      <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h2>
            <InfoTag term="workflow_verificacion" display="Verificación técnica" />
          </h2>
          <p className="mt-1 text-base font-medium text-[color:var(--fulkro-body)]">
            Estado de seguridad continuo del sistema ·{" "}
            <InfoTag term="zero_false_positive" display="Cero Falsos Positivos" /> ·
            trazabilidad completa hacia <InfoTag term="ENS" display="ENS" />{" "}
            <InfoTag term="Anexo_II" display="Anexo II" />.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <LaunchVerificationButton projectId={projectId} />
          <HandoffButton projectId={projectId} />
          <KillSwitchButton projectId={projectId} />
        </div>
      </header>

      <Tabs defaultValue="estado" className="flex flex-col gap-6">
        <TabsList className="w-fit">
          <TabsTrigger value="estado" data-testid="verification-tab-estado">
            Estado de seguridad
          </TabsTrigger>
          <TabsTrigger value="autopilot" data-testid="verification-tab-autopilot">
            Autopilot M8
          </TabsTrigger>
        </TabsList>

        <TabsContent value="estado" className="flex flex-col gap-6">
          <SecurityScoreHeader projectId={projectId} />

          <ENSHeatmap projectId={projectId} />

          <div className="grid gap-5 xl:grid-cols-5">
            <div className="xl:col-span-3">
              <FindingsTable projectId={projectId} />
            </div>
            <div className="flex flex-col gap-5 xl:col-span-2">
              <DeltaReport projectId={projectId} />
              <RemediationPlan projectId={projectId} />
            </div>
          </div>

          <RunsHistory projectId={projectId} />
        </TabsContent>

        <TabsContent value="autopilot">
          <AutopilotSection projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
