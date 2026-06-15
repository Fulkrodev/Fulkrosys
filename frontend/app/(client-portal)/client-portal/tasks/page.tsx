import { ClientTasksList } from "@/components/client-portal/ClientTasksList";
import { PageContainer } from "@/components/layout/PageContainer";

export default function ClientTasksPage() {
  return (
    <PageContainer variant="app">
      <h1 className="mb-6 text-2xl font-bold">Mis tareas</h1>
      <ClientTasksList />
    </PageContainer>
  );
}
