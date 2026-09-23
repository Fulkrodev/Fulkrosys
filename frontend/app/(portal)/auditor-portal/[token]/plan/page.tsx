import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { PlanView } from "@/components/auditor-portal/views/PlanView";

export const metadata = { title: "Portal auditor · Plan adecuación" };

export default async function AuditorPortalPlanPage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <AuditorPortalEntry token={params.token}>
      <PlanView token={params.token} />
    </AuditorPortalEntry>
  );
}
