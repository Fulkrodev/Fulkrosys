"use client";

/**
 * ActiveProjectSync · routing guard sync activeProject store con URL param.
 *
 * Sub-atom 1.E.2 Phase C · ADR-054.
 *
 * Mounted dentro /admin/projects/[id]/layout.tsx. URL param `projectId`
 * es source of truth canonical · este componente:
 *
 *   1. Si activeProject?.id !== projectId · fetch `/api/v1/projects/{id}/header`
 *      + setActiveProject(...) con metadata fresh
 *   2. Si fetch fails (404 project NOT accessible · network error):
 *      clearActiveProject + redirect /admin/projects con toast warning
 *   3. Sync transparent · NO UI disruption · run-once per projectId change
 *
 * Reuses existing endpoint GET /api/v1/projects/{id}/header (ProjectHeader
 * componente already uses esto · cache TanStack Query staleTime 60s
 * shared via queryKey ["project-composer","header",projectId]).
 */
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { ROUTES } from "@/lib/constants";
import { useActiveProjectStore } from "@/lib/stores/active-project-store";
import type { EnsCategory } from "@/lib/stores/active-project-store";
import { useCopilotStore } from "@/lib/stores/copilot-store";

interface ProjectHeaderResponse {
  project: {
    id: string;
    nombre: string;
    fase: string;
    categoria_objetivo: string | null;
    lifecycle_state: string | null;
    fecha_kickoff: string | null;
    fecha_objetivo_certificacion: string | null;
    certified_at: string | null;
  };
  cliente: {
    id: string;
    nombre: string;
    cif: string;
    sector: string | null;
    provincia: string | null;
  };
}

function parseEnsCategory(raw: string | null): EnsCategory | null {
  if (raw === "BASICA" || raw === "MEDIA" || raw === "ALTA") return raw;
  return null;
}

export function ActiveProjectSync({ projectId }: { projectId: string }) {
  const router = useRouter();
  const activeProject = useActiveProjectStore((s) => s.activeProject);
  const setActiveProject = useActiveProjectStore((s) => s.setActiveProject);
  const clearActiveProject = useActiveProjectStore((s) => s.clearActiveProject);
  const setCopilotPanelContext = useCopilotStore((s) => s.setPanelContext);
  // Sub-atom Sesión 3B-2A Phase A.1 · clear copilot messages when projectId
  // changes · prevents stale UI showing previous project conversation.
  // Backend conversations are persisted FK project_id (CopilotConversation +
  // CopilotMessage) · frontend store is ephemeral session-scoped UX only.
  const clearCopilotMessages = useCopilotStore((s) => s.clear);

  const needsSync = !activeProject || activeProject.id !== projectId;

  const { data, isError } = useQuery<ProjectHeaderResponse>({
    queryKey: ["project-composer", "header", projectId],
    queryFn: () =>
      api<ProjectHeaderResponse>(`/api/v1/projects/${projectId}/header`),
    enabled: Boolean(projectId) && needsSync,
    staleTime: 60_000,
    retry: false,
  });

  useEffect(() => {
    if (!data || !needsSync) return;
    setActiveProject({
      id: data.project.id,
      name: data.project.nombre,
      clientId: data.cliente.id,
      clientName: data.cliente.nombre,
      ensCategory: parseEnsCategory(data.project.categoria_objetivo),
      status: data.project.lifecycle_state ?? data.project.fase ?? "active",
      lastAccessedAt: Date.now(),
    });
  }, [data, needsSync, setActiveProject]);

  // Sub-atom 1.E.2 Phase D · sync copilot-store panelContext.projectId con
  // activeProject. Sostiene useCopilot(projectId) auto-scoped sin tocar
  // call sites · panelContext.projectId fallback chain. Cross-portal NO
  // overlap (cliente NO usa active-project-store · 1 proyecto/user natively).
  //
  // Sub-atom Sesión 3B-2A Phase A.1 · also clear ephemeral messages when
  // projectId changes · avoids showing stale conversation from previous
  // project during navigation transitions. Backend FK enforce isolation ·
  // this is UX freshness only.
  useEffect(() => {
    const pid = activeProject?.id;
    if (!pid) return;
    setCopilotPanelContext({
      projectId: pid,
      clientId: activeProject.clientId,
      projectPhase: activeProject.status,
    });
    clearCopilotMessages();
  }, [
    activeProject?.id,
    activeProject?.clientId,
    activeProject?.status,
    setCopilotPanelContext,
    clearCopilotMessages,
  ]);

  useEffect(() => {
    if (isError) {
      clearActiveProject();
      toast.warning("Proyecto no accesible · redirigiendo al selector");
      router.replace(ROUTES.projects);
    }
  }, [isError, clearActiveProject, router]);

  return null;
}
