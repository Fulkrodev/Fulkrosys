import { DraftReportAdminView } from "@/components/admin/audit/DraftReportAdminView";

export const metadata = {
  title: "Borrador del informe · Admin",
};

export default async function AdminDraftReportPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <DraftReportAdminView projectId={params.id} />;
}
