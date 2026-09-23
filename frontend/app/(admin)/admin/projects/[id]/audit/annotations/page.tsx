import { AdminAnnotationsReview } from "@/components/admin/audit/AdminAnnotationsReview";

export const metadata = {
  title: "Anotaciones del auditor · Admin",
};

export default async function AdminAuditAnnotationsPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <AdminAnnotationsReview projectId={params.id} />;
}
