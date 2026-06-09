import { PublicPortalShell } from "@/components/layout/PublicPortalShell";
import { RemediationPortal } from "@/components/remediation-portal/RemediationPortal";

export const metadata = {
  title: "Portal de remediación",
};

export default function RemediationTokenPage({
  params,
}: {
  params: { token: string };
}) {
  return (
    <PublicPortalShell>
      <RemediationPortal token={params.token} />
    </PublicPortalShell>
  );
}
