import { AdminChatPanel } from "@/components/admin/AdminChatPanel";

export default async function AdminChatProjectPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-6 text-2xl font-bold">Chat con cliente</h1>
      <AdminChatPanel projectId={params.id} />
    </div>
  );
}
