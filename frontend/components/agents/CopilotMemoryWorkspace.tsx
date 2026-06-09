"use client";

/**
 * CopilotMemoryWorkspace · página /admin/copilot con memoria por proyecto (#23).
 *
 * Selector de proyecto (project_id REAL) → lista de conversaciones persistidas
 * → chat con recall. Antes la página usaba el camino stateless (useCopilot) sin
 * persistencia: "háblame de lo de hace 3 meses" no funcionaba. Ahora sí.
 *
 * Memoria POR PROYECTO · RLS `copilot_isolation` server-side (el front consume).
 */
import { MessageSquarePlus, Trash2 } from "lucide-react";
import * as React from "react";

import { CopilotConversationChat } from "@/components/agents/CopilotConversationChat";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateConversation,
  useDeleteConversation,
  useMemoryProjects,
  useProjectConversations,
} from "@/hooks/useCopilotConversations";
import { useActiveProjectStore } from "@/lib/stores/active-project-store";
import { cn } from "@/lib/utils";

export function CopilotMemoryWorkspace() {
  const lastUsedProjectId = useActiveProjectStore((s) => s.lastUsedProjectId);
  const projectsQuery = useMemoryProjects();
  const projects = React.useMemo(
    () => projectsQuery.data ?? [],
    [projectsQuery.data],
  );

  const [projectId, setProjectId] = React.useState<string | null>(null);
  const [conversationId, setConversationId] = React.useState<string | null>(
    null,
  );

  // Default de proyecto: lastUsed si está en la lista, si no el primero.
  React.useEffect(() => {
    if (projectId || projects.length === 0) return;
    const fromStore = projects.find((p) => p.project_id === lastUsedProjectId);
    setProjectId(fromStore?.project_id ?? projects[0].project_id);
  }, [projects, lastUsedProjectId, projectId]);

  const conversationsQuery = useProjectConversations(projectId);
  const conversations = React.useMemo(
    () => conversationsQuery.data ?? [],
    [conversationsQuery.data],
  );

  // Al cambiar de proyecto, auto-selecciona la conversación más reciente.
  React.useEffect(() => {
    if (!projectId) return;
    if (conversations.length === 0) {
      setConversationId(null);
      return;
    }
    const stillThere = conversations.some((c) => c.id === conversationId);
    if (!stillThere) setConversationId(conversations[0].id);
  }, [projectId, conversations, conversationId]);

  const createMutation = useCreateConversation(projectId);
  const deleteMutation = useDeleteConversation(projectId);

  const activeProject = projects.find((p) => p.project_id === projectId);

  async function handleNew() {
    if (!projectId) return;
    const titulo = `Conversación ${new Date().toLocaleString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })}`;
    const conv = await createMutation.mutateAsync({ titulo });
    setConversationId(conv.id);
  }

  async function handleDelete(id: string) {
    await deleteMutation.mutateAsync(id);
    if (conversationId === id) setConversationId(null);
  }

  return (
    <div className="space-y-4" data-testid="copilot-memory-workspace">
      {/* Selector de proyecto */}
      <div className="flex flex-wrap items-center gap-3">
        <label
          htmlFor="copilot-project-select"
          className="text-sm font-medium text-foreground/70"
        >
          Proyecto:
        </label>
        <Select
          value={projectId ?? undefined}
          onValueChange={(v) => {
            setProjectId(v);
            setConversationId(null);
          }}
          disabled={projectsQuery.isLoading || projects.length === 0}
        >
          <SelectTrigger
            id="copilot-project-select"
            className="w-[22rem] max-w-full"
            data-testid="copilot-project-select"
          >
            <SelectValue
              placeholder={
                projectsQuery.isLoading
                  ? "Cargando proyectos…"
                  : "Elige un proyecto"
              }
            />
          </SelectTrigger>
          <SelectContent>
            {projects.map((p) => (
              <SelectItem key={p.project_id} value={p.project_id}>
                {p.nombre}
                {p.cliente_nombre ? ` · ${p.cliente_nombre}` : ""}
                {p.categoria_objetivo ? ` (${p.categoria_objetivo})` : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {activeProject?.fase && (
          <span className="text-xs text-muted-foreground">
            Fase: {activeProject.fase}
          </span>
        )}
      </div>

      {!projectsQuery.isLoading && projects.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No hay proyectos activos todavía. Da de alta un proyecto para empezar
          a usar la memoria del copiloto.
        </p>
      )}

      {projectId && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-[16rem_1fr]">
          {/* Rail de conversaciones */}
          <aside
            className="flex flex-col gap-2 rounded-xl border bg-card p-3"
            data-testid="copilot-conversation-list"
          >
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="w-full justify-start gap-2"
              onClick={() => void handleNew()}
              disabled={createMutation.isPending}
              data-testid="copilot-new-conversation"
            >
              <MessageSquarePlus className="size-4" />
              Nueva conversación
            </Button>

            <div className="mt-1 space-y-1 overflow-y-auto">
              {conversationsQuery.isLoading && (
                <p className="px-1 text-xs text-muted-foreground">Cargando…</p>
              )}
              {!conversationsQuery.isLoading && conversations.length === 0 && (
                <p className="px-1 py-2 text-xs text-muted-foreground">
                  Sin conversaciones en este proyecto. Crea una nueva.
                </p>
              )}
              {conversations.map((c) => (
                <div
                  key={c.id}
                  className={cn(
                    "group flex items-center gap-1 rounded-md px-2 py-1.5 text-sm",
                    c.id === conversationId
                      ? "bg-primary/10 text-primary"
                      : "hover:bg-muted/60",
                  )}
                >
                  <button
                    type="button"
                    onClick={() => setConversationId(c.id)}
                    className="flex-1 truncate text-left"
                    data-testid="copilot-conversation-item"
                    title={c.titulo ?? "Conversación"}
                  >
                    {c.titulo ?? "Conversación"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDelete(c.id)}
                    aria-label="Borrar conversación"
                    className="opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </aside>

          {/* Panel de chat con memoria */}
          {conversationId ? (
            <CopilotConversationChat
              projectId={projectId}
              conversationId={conversationId}
            />
          ) : (
            <div className="flex h-[24rem] items-center justify-center rounded-xl border bg-card text-sm text-muted-foreground">
              Elige o crea una conversación para empezar.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
