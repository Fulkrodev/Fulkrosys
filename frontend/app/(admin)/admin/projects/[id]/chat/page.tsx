import { AdminChatPanel } from "@/components/admin/AdminChatPanel";

export default function AdminChatProjectPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-6 text-2xl font-bold">Chat con cliente</h1>
      <AdminChatPanel projectId={params.id} />
    </div>
  );
}
