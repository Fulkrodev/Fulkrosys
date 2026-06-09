"use client";

import * as React from "react";
import { MessageSquare, Send, User, UserCog, Zap } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import { useChatMessages, useSendMessage } from "@/hooks/useWorkspace";
import type { ChatAutorTipo, ChatMessage } from "@/lib/admin-workspace/api";

export interface ChatTabProps {
  projectId: string;
}

const AUTOR_TIPO_META: Record<ChatAutorTipo, { label: string; variant: "info" | "success" | "secondary"; icon: typeof User }> = {
  marcos: { label: "Marcos", variant: "info", icon: UserCog },
  cliente: { label: "Cliente", variant: "success", icon: User },
  sistema: { label: "Sistema", variant: "secondary", icon: Zap },
};

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="prose prose-sm max-w-none break-words">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function MessageCard({ message }: { message: ChatMessage }) {
  const tipo =
    (["marcos", "cliente", "sistema"] as ChatAutorTipo[]).find(
      (t) => t === message.autor_tipo,
    ) ?? "marcos";
  const meta = AUTOR_TIPO_META[tipo];
  const Icon = meta.icon;
  const isMine = tipo === "marcos";

  return (
    <Card
      className={cn(
        "border-l-4",
        isMine && "border-l-fulkro-info",
        tipo === "cliente" && "border-l-fulkro-success",
        tipo === "sistema" && "border-l-fulkro-ink-300",
      )}
    >
      <CardContent className="space-y-2 p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Icon className="size-4 text-fulkro-ink-500" />
            <Badge variant={meta.variant}>{meta.label}</Badge>
            <span className="text-xs font-medium text-fulkro-ink-700">
              {message.autor}
            </span>
          </div>
          <span className="text-xs text-fulkro-ink-500">
            {message.created_at
              ? new Date(message.created_at).toLocaleString("es-ES", {
                  dateStyle: "short",
                  timeStyle: "short",
                })
              : "—"}
          </span>
        </div>
        <MarkdownContent content={message.mensaje} />
        {message.respondiendo_a ? (
          <p className="text-xs italic text-fulkro-ink-500">
            ↳ respondiendo a mensaje {message.respondiendo_a.slice(0, 8)}…
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function ChatTab({ projectId }: ChatTabProps) {
  const { data: messages = [], isLoading } = useChatMessages(projectId);
  const sendMutation = useSendMessage(projectId);

  const [draft, setDraft] = React.useState("");
  const [activeTab, setActiveTab] = React.useState<"edit" | "preview">("edit");

  const handleSend = () => {
    const text = draft.trim();
    if (text.length === 0) {
      toast.warning("Escribe un mensaje antes de enviar");
      return;
    }
    sendMutation.mutate(
      { autor: "marcos", autor_tipo: "marcos", mensaje: text },
      {
        onSuccess: () => {
          setDraft("");
          setActiveTab("edit");
          toast.success("Mensaje enviado");
        },
        onError: () => toast.error("Error al enviar"),
      },
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <MessageSquare size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Chat del workspace
            <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
              ({messages.length})
            </span>
          </h3>
          <TooltipENS term="workspace_proyecto" />
        </div>
        <div className="text-xs text-fulkro-ink-500">
          Bilateral · Marcos ↔ cliente · cifrado at-rest
        </div>
      </div>

      <div className="max-h-[480px] space-y-2 overflow-y-auto rounded border border-fulkro-ink-100 bg-fulkro-canvas/50 p-3">
        {isLoading ? (
          <p className="text-sm text-fulkro-ink-500">Cargando mensajes…</p>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-10 text-fulkro-ink-500">
            <MessageSquare className="size-8" />
            <p className="text-sm">Sin mensajes · empieza la conversación</p>
          </div>
        ) : (
          messages.map((m) => <MessageCard key={m.id} message={m} />)
        )}
      </div>

      <Card>
        <CardContent className="p-3">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "edit" | "preview")}>
            <TabsList>
              <TabsTrigger value="edit">Editar</TabsTrigger>
              <TabsTrigger value="preview">Vista previa</TabsTrigger>
            </TabsList>
            <TabsContent value="edit" className="mt-2">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Escribe un mensaje · soporta markdown (** **, _ _, [link](url), etc)"
                className="min-h-[100px] w-full rounded border border-fulkro-ink-200 bg-white p-2 font-mono text-sm focus:border-fulkro-primary-700 focus:outline-none"
              />
            </TabsContent>
            <TabsContent value="preview" className="mt-2">
              <div className="min-h-[100px] rounded border border-fulkro-ink-200 bg-white p-2">
                {draft.trim() ? (
                  <MarkdownContent content={draft} />
                ) : (
                  <p className="text-sm italic text-fulkro-ink-300">
                    Vista previa vacía · escribe en la pestaña Editar
                  </p>
                )}
              </div>
            </TabsContent>
          </Tabs>
          <div className="mt-2 flex items-center justify-between gap-2">
            <p className="text-xs text-fulkro-ink-500">
              {draft.length} caracteres · {draft.split("\n").length} líneas
            </p>
            <Button
              type="button"
              variant="primary"
              onClick={handleSend}
              disabled={sendMutation.isPending || draft.trim().length === 0}
            >
              <Send className="mr-2 size-4" />
              {sendMutation.isPending ? "Enviando…" : "Enviar"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
