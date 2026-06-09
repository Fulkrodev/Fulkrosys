import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { PlanView } from "@/components/auditor-portal/views/PlanView";

export const metadata = { title: "Portal auditor · Plan adecuación" };

export default function AuditorPortalPlanPage({
  params,
}: {
  params: { token: string };
}) {
  return (
    <AuditorPortalEntry token={params.token}>
      <PlanView token={params.token} />
    </AuditorPortalEntry>
  );
}
