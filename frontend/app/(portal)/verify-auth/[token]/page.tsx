import { PublicPortalShell } from "@/components/layout/PublicPortalShell";
import { VerifyAuthPortal } from "@/components/verify-auth/VerifyAuthPortal";

export const metadata = {
  title: "Autorización de verificación",
};

export default function VerifyAuthTokenPage({
  params,
}: {
  params: { token: string };
}) {
  return (
    <PublicPortalShell>
      <VerifyAuthPortal token={params.token} />
    </PublicPortalShell>
  );
}
