import { DdaEvidenceGapsAdminView } from "@/components/admin/audit/DdaEvidenceGapsAdminView";

export const metadata = {
  title: "Cobertura DdA-Evidencias · Admin",
};

export default function AdminGapsPage({
  params,
}: {
  params: { id: string };
}) {
  return <DdaEvidenceGapsAdminView projectId={params.id} />;
}
