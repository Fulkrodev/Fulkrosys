import { ClientChatPage } from "@/components/client-portal/ClientChatPage";

export default function ChatPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="mb-6 text-2xl font-bold">Chat con Marcos</h1>
      <ClientChatPage />
    </main>
  );
}
