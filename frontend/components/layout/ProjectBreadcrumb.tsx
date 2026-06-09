"use client";

/**
 * ProjectBreadcrumb · persistent navegación context project-scoped.
 *
 * Sub-atom 1.E.2 Phase C · ADR-054.
 *
 * Visible all /admin/projects/[id]/* pages dentro del layout. Pattern:
 *   [Cliente] > [Proyecto] > [Sub-página]
 *
 * Click [Cliente] → /admin/clients (lista clients)
 * Click [Proyecto] → /admin/projects/{id}/dashboard
 * Click [Sub-página] = current (no-op)
 *
 * Sub-page label derived from pathname final segment · friendly label
 * via SUB_PAGE_LABELS map. Si NO match → capitalize segment.
 *
 * Empty state: si NO activeProject (initial mount antes routing guard
 * hydrate) → render skeleton placeholder evitar layout shift.
 */
import { ChevronRight, FolderKanban } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ROUTES } from "@/lib/constants";
import { useActiveProjectStore } from "@/lib/stores/active-project-store";

const SUB_PAGE_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  dda: "DdA",
  magerit: "MAGERIT",
  dimensiones: "Dimensiones",
  archetype: "Arquetipo",
  diagnosis: "Diagnóstico",
  discovery: "Descubrimiento",
  conformity: "Conformidad",
  contratos: "Contratos",
  changes: "Cambios",
  discrepancies: "Discrepancias",
  documents: "Documentos",
  dossier: "Dossier ENAC",
  equipo: "Equipo",
  evidence: "Evidencias",
  exit: "Cierre",
  "feature-flags": "Feature flags",
  financial: "Financiero",
  implementation: "Implantación",
  mcps: "Pentest MCPs",
  obligations: "Obligaciones",
  onboarding: "Onboarding",
  "planes-accion": "Planes acción",
  providers: "Proveedores",
  retainer: "Retainer",
  risks: "Riesgos",
  roles: "Roles ENS",
  transparency: "Transparencia",
  workspace: "Workspace",
  awareness: "Concienciación",
  "audit-dry-run": "Audit dry-run",
  audit: "Auditoría",
  "backup-policy": "Backup policy",
  bia: "BIA",
  billing: "Billing",
  "cloud-connectors": "Conexiones Cloud",
  communication: "Comunicación",
  aepd: "AEPD",
  policies: "Políticas",
  timeline: "Timeline",
};

function deriveSubPageLabel(segment: string): string {
  return (
    SUB_PAGE_LABELS[segment] ??
    segment
      .split("-")
      .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
      .join(" ")
  );
}

export function ProjectBreadcrumb() {
  const pathname = usePathname();
  const activeProject = useActiveProjectStore((s) => s.activeProject);

  if (!activeProject) {
    // Skeleton placeholder · evitar layout shift mientras routing guard hidrata.
    return (
      <nav
        aria-label="Breadcrumb"
        className="flex h-5 animate-pulse items-center gap-2 text-xs"
        data-testid="project-breadcrumb-skeleton"
      >
        <span className="h-3 w-24 rounded bg-fulkro-ink-200" />
        <ChevronRight size={11} className="text-fulkro-ink-300" />
        <span className="h-3 w-32 rounded bg-fulkro-ink-200" />
      </nav>
    );
  }

  // Pathname pattern: /admin/projects/{id}/{...sub-page-segments}
  // Extract sub-page segment(s) after the id.
  const parts = pathname.split("/").filter(Boolean); // [admin, projects, {id}, ...rest]
  const subSegments = parts.slice(3); // segments after {id}
  const subPageLabel =
    subSegments.length > 0 ? deriveSubPageLabel(subSegments[0]) : "Dashboard";
  const isAtDashboard = subSegments.length === 0 || subSegments[0] === "dashboard";

  return (
    <nav
      aria-label="Breadcrumb"
      className="flex flex-wrap items-center justify-between gap-1.5 text-xs text-fulkro-ink-600"
      data-testid="project-breadcrumb"
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <Link
          href={ROUTES.clients}
          className="font-medium hover:text-fulkro-primary-700 hover:underline"
          data-testid="project-breadcrumb-client"
        >
          {activeProject.clientName}
        </Link>
        <ChevronRight size={11} className="text-fulkro-ink-600" aria-hidden />
        <Link
          href={`${ROUTES.projects}/${activeProject.id}/dashboard`}
          className={
            isAtDashboard
              ? "font-semibold text-fulkro-primary-700"
              : "font-medium hover:text-fulkro-primary-700 hover:underline"
          }
          data-testid="project-breadcrumb-project"
        >
          {activeProject.name}
        </Link>
        {!isAtDashboard ? (
          <>
            <ChevronRight size={11} className="text-fulkro-ink-600" aria-hidden />
            <span
              className="font-semibold text-fulkro-ink-700"
              data-testid="project-breadcrumb-subpage"
            >
              {subPageLabel}
            </span>
          </>
        ) : null}
      </div>

      {/* Sub-atom Sesión 3B-2A Phase A.2 · explicit "Cambiar proyecto" button
          a la derecha del breadcrumb. Always visible · NO presión · click
          vuelve siempre al selector clean. */}
      <Link
        href={ROUTES.projects}
        className="inline-flex items-center gap-1.5 rounded-md border border-fulkro-ink-200 bg-white px-2.5 py-1 text-xs font-medium text-fulkro-ink-600 hover:bg-fulkro-ink-100 hover:text-fulkro-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-info focus-visible:ring-offset-2"
        data-testid="project-breadcrumb-change"
        aria-label="Cambiar a otro proyecto"
      >
        <FolderKanban size={12} />
        Cambiar proyecto
      </Link>
    </nav>
  );
}
