import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { E041View } from "@/components/auditor-portal/views/E041View";

export const metadata = { title: "Portal auditor · E-041 Declaración" };

export default async function AuditorPortalE041Page(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <AuditorPortalEntry token={params.token}>
      <E041View token={params.token} />
    </AuditorPortalEntry>
  );
}
