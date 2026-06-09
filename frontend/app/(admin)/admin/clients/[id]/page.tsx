"use client";

/**
 * /admin/clients/[id] · Sesión 3B-2B.3 Phase X.4b · architectural router.
 *
 * Pre-cleanup: 193 LOC cross-cliente detail with 7 tabs (Datos · Usuarios ·
 * Proyectos · Mensajes · Facturas · Audit · Contactos).
 *
 * Post-cleanup (R23 strict · cliente entity ≈ project entity 1:1 MVP):
 * resolve cliente.id → project.id (first/only project per cliente) and
 * redirect to project-scoped equivalent of each historic tab.
 *
 * Tab migration map (already implemented · this router gates the redirect):
 *   - Datos cliente  → /admin/projects/[projectId]/cliente-info (NEW Step 4a)
 *   - Usuarios       → /admin/projects/[projectId]/users
 *   - Proyectos      → ELIMINATED (1:1 MVP · cliente = project context already)
 *   - Mensajes       → /admin/projects/[projectId]/communication
 *   - Facturas       → /admin/projects/[projectId]/financial
 *   - Audit Log      → /admin/projects/[projectId]/audit
 *   - Contactos      → /admin/projects/[projectId]/equipo
 *
 * Backward compat: bookmarks to /admin/clients/{id} continue to work · this
 * page resolves cliente → project (idempotent) and replaces URL with the
 * canonical project-scoped destination (defaults to /cliente-info as the
 * primary cliente-entity entry).
 *
 * Edge cases:
 *   - cliente has 0 projects: redirect to /admin/projects (selector) so Marcos
 *     creates the first one.
 *   - cliente has N>1 projects (future-X multi-project): redirect to selector
 *     filtered by cliente_id (TODO when scenario arises post-piloto).
 *   - cliente not found / 404: redirect to /admin/projects with toast.
 */
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { use, useEffect } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { listClientProjects } from "@/lib/admin-clients/api";
import type { ProjectOut } from "@/lib/admin-clients/schemas";

export default function LegacyClientDetailRouter({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: clientId } = use(params);
  const router = useRouter();

  const projectsQ = useQuery<ProjectOut[]>({
    queryKey: ["admin-clients", "projects-router", clientId],
    queryFn: () => listClientProjects(clientId),
    staleTime: 30_000,
    retry: 1,
  });

  useEffect(() => {
    if (projectsQ.isLoading) return;
    if (projectsQ.isError) {
      toast.error("No se pudo cargar el cliente · redirigiendo a proyectos.");
      router.replace("/admin/projects");
      return;
    }
    const projects = projectsQ.data ?? [];
    if (projects.length === 0) {
      toast.info(
        "Este cliente todavía no tiene proyectos · crea uno desde el selector.",
      );
      router.replace("/admin/projects");
      return;
    }
    // 1:1 MVP: pick the first project. Future-X multi-project: surface picker.
    const projectId = projects[0].id;
    router.replace(`/admin/projects/${projectId}/cliente-info`);
  }, [projectsQ.isLoading, projectsQ.isError, projectsQ.data, router]);

  return (
    <div
      className="container mx-auto flex max-w-md flex-col items-center gap-4 py-16 text-center"
      data-testid="clients-detail-legacy-router"
    >
      <Loader2 className="h-6 w-6 animate-spin text-fulkro-primary-700" aria-hidden />
      <div>
        <p className="text-base font-medium text-fulkro-ink-700">
          Esta ruta ha cambiado.
        </p>
        <p className="mt-1 text-sm text-fulkro-ink-700">
          Las pestañas del cliente ahora viven bajo el proyecto correspondiente.
          Te llevamos al proyecto activo.
        </p>
      </div>
    </div>
  );
}
