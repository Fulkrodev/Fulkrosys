import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { DdaView } from "@/components/auditor-portal/views/DdaView";

export const metadata = { title: "Portal auditor · DdA" };

export default function AuditorPortalDdaPage({
  params,
}: {
  params: { token: string };
}) {
  return (
    <AuditorPortalEntry token={params.token}>
      <DdaView token={params.token} />
    </AuditorPortalEntry>
  );
}
