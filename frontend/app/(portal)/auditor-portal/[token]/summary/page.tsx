import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { SummaryView } from "@/components/auditor-portal/views/SummaryView";

export const metadata = { title: "Portal auditor · Resumen del proyecto" };

export default function AuditorPortalSummaryPage({
  params,
}: {
  params: { token: string };
}) {
  return (
    <AuditorPortalEntry token={params.token}>
      <SummaryView token={params.token} />
    </AuditorPortalEntry>
  );
}
