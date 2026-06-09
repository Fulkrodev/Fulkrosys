"use client";

import * as React from "react";
import {
  Activity,
  AlertCircle,
  FileIcon,
  Loader2,
  MessageSquare,
  PlayCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import {
  useCreateWorkspace,
  useFeedUnreadCount,
  useWorkspace,
  useWorkspaceFiles,
  useChatMessages,
  useFeedItems,
} from "@/hooks/useWorkspace";

import { ChatTab } from "./ChatTab";
import { FeedTab } from "./FeedTab";
import { FilesTab } from "./FilesTab";

export interface WorkspacePanelProps {
  projectId: string;
}

const TAB_DEFS = [
  { id: "files", label: "Archivos", icon: FileIcon },
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "feed", label: "Timeline", icon: Activity },
] as const;

type TabId = (typeof TAB_DEFS)[number]["id"];

export function WorkspacePanel({ projectId }: WorkspacePanelProps) {
  const [activeTab, setActiveTab] = React.useState<TabId>("files");
  const { data: workspace, isLoading: wsLoading, error: wsError } =
    useWorkspace(projectId);
  const createMutation = useCreateWorkspace(projectId);

  const { data: files = [] } = useWorkspaceFiles(projectId);
  const { data: messages = [] } = useChatMessages(projectId);
  const { data: feedItems = [] } = useFeedItems(projectId, { limit: 50 });
  const { data: unread } = useFeedUnreadCount(projectId);

  const noWorkspace =
    !wsLoading &&
    (!workspace || (wsError && (wsError as { status?: number }).status === 404));

  if (wsLoading) {
    return (
      <div className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
        <Loader2 className="size-4 animate-spin" />
        Cargando workspace…
      </div>
    );
  }

  if (noWorkspace) {
    return (
      <div className="p-4 sm:p-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="size-5 text-fulkro-warning" />
              Workspace no creado
            </CardTitle>
            <CardDescription>
              Crea un workspace para empezar a colaborar con el cliente: archivos staging ·
              chat bilateral · timeline de eventos.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              type="button"
              variant="primary"
              onClick={() => {
                createMutation.mutate(
                  { nombre: "Workspace del proyecto" },
                  {
                    onSuccess: () => toast.success("Workspace creado"),
                    onError: () => toast.error("Error al crear workspace"),
                  },
                );
              }}
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  Creando…
                </>
              ) : (
                <>
                  <PlayCircle className="mr-2 size-4" />
                  Crear workspace
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const tabCount = (id: TabId): number | null => {
    if (id === "files") return files.length;
    if (id === "chat") return messages.length;
    if (id === "feed") return feedItems.length;
    return null;
  };

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-fulkro-primary-700">
              Workspace del proyecto
            </h1>
            <p className="text-sm text-fulkro-ink-500">
              {workspace?.nombre ?? "Sin nombre"} · espacio compartido entre Marcos y el equipo del cliente.{" "}
              <TooltipENS term="workspace_proyecto" />
            </p>
          </div>
          <div className="flex items-center gap-2">
            {workspace?.estado === "archived" ? (
              <Badge variant="secondary">archivado</Badge>
            ) : workspace?.estado === "active" ? (
              <Badge variant="success">activo</Badge>
            ) : (
              <Badge variant="outline">{workspace?.estado ?? "—"}</Badge>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant="secondary">
            <FileIcon className="mr-1 size-3" /> {files.length} archivos
          </Badge>
          <Badge variant="secondary">
            <MessageSquare className="mr-1 size-3" /> {messages.length} mensajes
          </Badge>
          <Badge variant="secondary">
            <Activity className="mr-1 size-3" /> {feedItems.length} eventos
          </Badge>
          {unread && unread.unread_count > 0 ? (
            <Badge variant="warning">{unread.unread_count} sin leer</Badge>
          ) : null}
        </div>
      </header>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabId)}>
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1 bg-transparent p-0">
          {TAB_DEFS.map((tab) => {
            const Icon = tab.icon;
            const count = tabCount(tab.id);
            return (
              <TabsTrigger
                key={tab.id}
                value={tab.id}
                className={cn(
                  "data-[state=active]:bg-fulkro-primary-700 data-[state=active]:text-white",
                  "border border-fulkro-ink-100 bg-white",
                )}
              >
                <Icon className="mr-1.5 size-3.5" />
                {tab.label}
                {count !== null ? (
                  <span className="ml-1.5 rounded-full bg-fulkro-canvas px-1.5 py-0.5 text-[10px] font-mono text-fulkro-ink-700">
                    {count}
                  </span>
                ) : null}
              </TabsTrigger>
            );
          })}
        </TabsList>

        <TabsContent value="files" className="mt-6">
          <FilesTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="chat" className="mt-6">
          <ChatTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="feed" className="mt-6">
          <FeedTab projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
