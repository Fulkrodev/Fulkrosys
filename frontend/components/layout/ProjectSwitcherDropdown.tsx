"use client";

/**
 * ProjectSwitcherDropdown · cambio fluido entre proyectos.
 *
 * Sub-atom 1.E.2 Phase C · ADR-054 · embedded en ActiveProjectBanner.
 *
 * Pattern reuse PortalSwitcher (DropdownMenu shadcn/ui) + useClients()
 * hook (existing). Cada client = 1 proyecto típico (piloto MEDIA · 1:1
 * cliente↔proyecto). Future-1.E.2.advanced-switcher extiende a múltiples
 * proyectos por cliente cuando demand-driven.
 *
 * Click trigger → dropdown lista clients accesibles. Click client →
 * navigate /admin/projects/{client_slug}/dashboard. URL es source of
 * truth · routing guard /admin/projects/[id]/layout.tsx hidrata
 * activeProject store onMount.
 *
 * Empty state: si NO clients (loading o BD vacía) · trigger disabled
 * con tooltip explicativo.
 */
import { ArrowLeftRight, Loader2 } from "lucide-react";
import Link from "next/link";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useClients } from "@/hooks/useClients";
import { ROUTES } from "@/lib/constants";
import { useActiveProjectStore } from "@/lib/stores/active-project-store";

function clientSlug(client: { id: string; nombre: string }): string {
  // Mirror Sidebar.tsx pattern · uses client.id as slug for project route.
  return client.id;
}

// AVISO (medido 2026-09-10 · recorrido completo, BLOQUE E): el enlace de abajo
// está roto POR DOS SITIOS A LA VEZ, y por eso NO se ha arreglado a medias.
//
//   1. `/dashboard` no existe. No hay ninguna carpeta `dashboard` bajo
//      `app/(admin)/admin/projects/[id]/`. Se corrigió en HeaderProjectChip,
//      ProjectBreadcrumb y CreateProjectModal, que apuntaban al mismo sitio
//      inexistente (allí bastaba con quitar el sufijo: `/admin/projects/{id}`
//      redirige a `/summary`).
//   2. Aquí, además, se mete un id de CLIENTE donde va un id de PROYECTO. Un
//      cliente puede tener varios proyectos y `clientSlug` devuelve
//      `client.id` sin más.
//
// Quitar sólo el `/dashboard` cambiaría un 404 visible por una página de
// «proyecto no encontrado» servida con HTTP 200: sería sustituir un fallo que
// se ve por uno que no se ve, que es exactamente lo contrario de lo que busca
// esta campaña. Arreglarlo de verdad exige resolver cliente → proyecto (elegir
// cuál, o listar los suyos), y eso es una decisión de producto, no una
// corrección de una línea.

export function ProjectSwitcherDropdown() {
  const { data: clients, isLoading } = useClients();
  const activeProject = useActiveProjectStore((s) => s.activeProject);

  const hasClients = !isLoading && clients && clients.length > 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        type="button"
        disabled={!hasClients}
        className="inline-flex items-center gap-1 rounded-md border border-white/15 bg-white/5 px-2 py-0.5 text-[11px] font-medium text-white/90 transition-colors hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-50"
        data-testid="project-switcher-trigger"
        aria-label="Cambiar de proyecto"
      >
        {isLoading ? (
          <Loader2 size={11} className="animate-spin" />
        ) : (
          <ArrowLeftRight size={11} />
        )}
        <span>Cambiar</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="z-50 min-w-[260px] bg-white"
        data-testid="project-switcher-content"
      >
        <DropdownMenuLabel className="text-xs uppercase tracking-wider text-fulkro-ink-500">
          Proyectos disponibles
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {hasClients ? (
          clients.map((client) => {
            const isActive = activeProject?.clientId === client.id;
            return (
              <DropdownMenuItem
                key={client.id}
                asChild
                className={isActive ? "bg-fulkro-ink-100 font-semibold" : ""}
              >
                <Link
                  href={`${ROUTES.projects}/${clientSlug(client)}/dashboard`}
                  className="flex w-full items-center justify-between gap-2 px-3 py-2 text-sm"
                  data-testid={`project-switcher-item-${client.id}`}
                >
                  <span className="truncate">{client.nombre}</span>
                  {isActive ? (
                    <span
                      className="text-[10px] font-semibold uppercase tracking-wider text-fulkro-info"
                      aria-label="Proyecto activo"
                    >
                      activo
                    </span>
                  ) : null}
                </Link>
              </DropdownMenuItem>
            );
          })
        ) : (
          <DropdownMenuItem disabled className="text-sm italic text-fulkro-ink-500">
            Sin proyectos disponibles
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link
            href={ROUTES.projects}
            className="flex w-full items-center justify-between gap-2 px-3 py-2 text-sm text-fulkro-info"
          >
            Ver todos los proyectos
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
