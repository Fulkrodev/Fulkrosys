import { AdminAnnotationsReview } from "@/components/admin/audit/AdminAnnotationsReview";

export const metadata = {
  title: "Anotaciones del auditor · Admin",
};

export default function AdminAuditAnnotationsPage({
  params,
}: {
  params: { id: string };
}) {
  return <AdminAnnotationsReview projectId={params.id} />;
}
