import { PublicPortalShell } from "@/components/layout/PublicPortalShell";
import { RemediationPortal } from "@/components/remediation-portal/RemediationPortal";

export const metadata = {
  title: "Portal de remediación",
};

export default async function RemediationTokenPage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <PublicPortalShell>
      <RemediationPortal token={params.token} />
    </PublicPortalShell>
  );
}
