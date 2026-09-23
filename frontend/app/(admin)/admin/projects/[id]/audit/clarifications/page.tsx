import { AdminClarificationsInbox } from "@/components/admin/audit/AdminClarificationsInbox";

export const metadata = {
  title: "Aclaraciones del auditor · Admin",
};

export default async function AdminAuditClarificationsPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <AdminClarificationsInbox projectId={params.id} />;
}
