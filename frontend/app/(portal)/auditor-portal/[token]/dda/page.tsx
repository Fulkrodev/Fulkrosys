import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { DdaView } from "@/components/auditor-portal/views/DdaView";

export const metadata = { title: "Portal auditor · DdA" };

export default async function AuditorPortalDdaPage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <AuditorPortalEntry token={params.token}>
      <DdaView token={params.token} />
    </AuditorPortalEntry>
  );
}
