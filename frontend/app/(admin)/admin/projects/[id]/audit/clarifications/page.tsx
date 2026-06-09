import { AdminClarificationsInbox } from "@/components/admin/audit/AdminClarificationsInbox";

export const metadata = {
  title: "Aclaraciones del auditor · Admin",
};

export default function AdminAuditClarificationsPage({
  params,
}: {
  params: { id: string };
}) {
  return <AdminClarificationsInbox projectId={params.id} />;
}
