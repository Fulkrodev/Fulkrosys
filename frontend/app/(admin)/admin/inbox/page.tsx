"use client";

/**
 * Admin inbox · chat threads + SLA tracking cross-projects (ADR-038
 * SAN-D MB-14.9).
 *
 * MB-14.9 SCOPED: vista admin enfocada per-projecto · cliente Marcos
 * navega a project específico desde Sidebar.tsx existente. Cross-project
 * inbox global diferido a MB-19+ (DEC-MB14-INBOX-CROSS-PROJECT).
 *
 * Para ahora: page muestra hint que admin debe abrir proyecto específico
 * para ver inbox chat. Component AdminChatInbox usable en
 * /admin/projects/[id]/chat (page TBD MB-19+ o cosechable per project
 * deepening).
 */
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Inbox } from "lucide-react";

export default function AdminInboxPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="mb-6 text-2xl font-bold">Inbox · Chat con clientes</h1>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Inbox className="h-5 w-5 text-fulkro-info" strokeWidth={2.3} />
            Chats activos por proyecto
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            La vista agregada cross-project se incorporará en MB-19+. Por
            ahora, abre el proyecto específico desde el sidebar para
            acceder al chat con el cliente y ver el SLA de respuesta.
          </p>
          <p className="text-sm text-muted-foreground">
            El componente <code>AdminChatInbox</code> (MB-14.6) está listo
            para integrarse en una sub-ruta per-project si surge la
            necesidad.
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
