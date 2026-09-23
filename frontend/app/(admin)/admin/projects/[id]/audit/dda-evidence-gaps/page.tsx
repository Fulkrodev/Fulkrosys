import { DdaEvidenceGapsAdminView } from "@/components/admin/audit/DdaEvidenceGapsAdminView";

export const metadata = {
  title: "Cobertura DdA-Evidencias · Admin",
};

export default async function AdminGapsPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <DdaEvidenceGapsAdminView projectId={params.id} />;
}
