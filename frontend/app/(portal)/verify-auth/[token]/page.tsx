import { PublicPortalShell } from "@/components/layout/PublicPortalShell";
import { VerifyAuthPortal } from "@/components/verify-auth/VerifyAuthPortal";

export const metadata = {
  title: "Autorización de verificación",
};

export default async function VerifyAuthTokenPage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <PublicPortalShell>
      <VerifyAuthPortal token={params.token} />
    </PublicPortalShell>
  );
}
