import { ClientTasksList } from "@/components/client-portal/ClientTasksList";

export default function ClientTasksPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <h1 className="mb-6 text-2xl font-bold">Mis tareas</h1>
      <ClientTasksList />
    </main>
  );
}
