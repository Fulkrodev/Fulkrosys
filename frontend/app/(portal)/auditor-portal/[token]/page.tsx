import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { SectionPlaceholder } from "@/components/auditor-portal/SectionPlaceholder";

export const metadata = {
  title: "Portal del auditor ENAC",
};

export default async function AuditorPortalTokenPage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <AuditorPortalEntry token={params.token}>
      <SectionPlaceholder
        title="Bienvenido · Portal del auditor ENAC"
        description="Has accedido al portal del auditor. Selecciona una sección en el menú lateral para consultar la documentación del proyecto."
      />
    </AuditorPortalEntry>
  );
}
