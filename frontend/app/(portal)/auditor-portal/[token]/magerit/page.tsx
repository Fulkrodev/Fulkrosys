import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { MageritView } from "@/components/auditor-portal/views/MageritView";

export const metadata = { title: "Portal auditor · MAGERIT" };

export default async function AuditorPortalMageritPage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <AuditorPortalEntry token={params.token}>
      <MageritView token={params.token} />
    </AuditorPortalEntry>
  );
}
