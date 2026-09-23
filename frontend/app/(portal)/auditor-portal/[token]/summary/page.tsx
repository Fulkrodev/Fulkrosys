import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { SummaryView } from "@/components/auditor-portal/views/SummaryView";

export const metadata = { title: "Portal auditor · Resumen del proyecto" };

export default async function AuditorPortalSummaryPage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <AuditorPortalEntry token={params.token}>
      <SummaryView token={params.token} />
    </AuditorPortalEntry>
  );
}
