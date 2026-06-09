import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { MageritView } from "@/components/auditor-portal/views/MageritView";

export const metadata = { title: "Portal auditor · MAGERIT" };

export default function AuditorPortalMageritPage({
  params,
}: {
  params: { token: string };
}) {
  return (
    <AuditorPortalEntry token={params.token}>
      <MageritView token={params.token} />
    </AuditorPortalEntry>
  );
}
