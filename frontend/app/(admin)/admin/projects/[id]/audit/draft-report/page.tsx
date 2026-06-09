import { DraftReportAdminView } from "@/components/admin/audit/DraftReportAdminView";

export const metadata = {
  title: "Borrador del informe · Admin",
};

export default function AdminDraftReportPage({
  params,
}: {
  params: { id: string };
}) {
  return <DraftReportAdminView projectId={params.id} />;
}
