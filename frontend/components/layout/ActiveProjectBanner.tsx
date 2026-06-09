"use client";

/**
 * ActiveProjectBanner · sidebar top section · sub-atom 1.E.2 Phase C.
 *
 * Visible 100% admin pages cross-navigation. Marcos siempre sabe
 * "qué cliente/proyecto estoy operando" en sidebar persistent.
 *
 * Estados:
 *   - Active project set → cliente + project name + ENS category badge
 *     + click → opens ProjectSwitcherDropdown (switch entre projects)
 *   - No active project → "Selecciona un proyecto" + button → /admin/projects
 *
 * Pattern reuse PortalSwitcher (DropdownMenu shadcn/ui).
 *
 * Ver ADR-054 Project-Scoped Admin UX.
 */
import { useQuery } from "@tanstack/react-query";
import { Building2, ChevronDown, FolderOpen } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { getClientBranding } from "@/lib/api/personalizacion-admin";
import { ROUTES } from "@/lib/constants";
import { useActiveProjectStore } from "@/lib/stores/active-project-store";

import { ProjectSwitcherDropdown } from "./ProjectSwitcherDropdown";

const HEX_COLOR_PATTERN = /^#[0-9A-Fa-f]{6}$/;

// 2026-06-09 · Polish gate · las variantes success/warning/secondary del Badge
// son translúcidas para TARJETAS BLANCAS; sobre el sidebar oscuro el texto -700
// quedaba ~2:1 (FAIL AA serious). chromeClass fuerza píldora sólida CLARA con
// texto oscuro → legible sobre cualquier chrome oscuro (axe PASS).
const CATEGORIA_BADGE: Record<
  string,
  { label: string; variant: "secondary" | "warning" | "success"; chromeClass: string }
> = {
  BASICA: {
    label: "BÁSICA",
    variant: "secondary",
    chromeClass: "bg-fulkro-ink-100 text-fulkro-ink-900",
  },
  MEDIA: {
    label: "MEDIA",
    variant: "warning",
    chromeClass: "bg-fulkro-warning-50 text-fulkro-warning-700",
  },
  ALTA: {
    label: "ALTA",
    variant: "success",
    chromeClass: "bg-fulkro-success-50 text-fulkro-success-700",
  },
};

export function ActiveProjectBanner() {
  const activeProject = useActiveProjectStore((s) => s.activeProject);

  // Sesión 3B-2B.4 Phase 1.2 · subtle brand-color accent matching cliente
  // primary_color (when set). Validates hex pattern frontend-side antes
  // inject inline style. Quietly disabled (retry: false) si endpoint 404 /
  // cliente sin branding · banner cae back a chrome neutro.
  const { data: branding } = useQuery({
    queryKey: ["sidebar", "client-branding", activeProject?.clientId],
    queryFn: () => getClientBranding(activeProject!.clientId),
    enabled: Boolean(activeProject?.clientId),
    staleTime: 5 * 60_000,
    retry: false,
  });

  const accentColor =
    branding?.primary_color && HEX_COLOR_PATTERN.test(branding.primary_color)
      ? branding.primary_color
      : null;

  if (!activeProject) {
    return (
      <div
        className="mx-3 mb-3 rounded-md border border-dashed border-white/25 px-3 py-3 text-xs text-white/85"
        data-testid="active-project-banner-empty"
      >
        <div className="mb-2 flex items-center gap-2">
          <FolderOpen size={13} className="text-white/85" />
          <span className="font-semibold uppercase tracking-wider">
            Sin proyecto activo
          </span>
        </div>
        <p className="mb-2 text-[11px] leading-snug text-white/70">
          Selecciona un proyecto para acceder a sus datos y herramientas.
        </p>
        <Link
          href={ROUTES.projects}
          className="inline-flex items-center gap-1.5 text-[12px] font-medium text-white hover:underline"
        >
          Ir a proyectos
          <ChevronDown size={11} className="-rotate-90" />
        </Link>
      </div>
    );
  }

  const catBadge = activeProject.ensCategory
    ? CATEGORIA_BADGE[activeProject.ensCategory]
    : null;

  return (
    <div
      className="mx-3 mb-3 rounded-md border border-white/15 bg-white/[0.06] px-3 py-3"
      data-testid="active-project-banner"
      style={
        accentColor
          ? { borderLeft: `3px solid ${accentColor}` }
          : undefined
      }
    >
      <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-white/75">
        <Building2 size={11} className="text-white/75" />
        <span className="truncate">{activeProject.clientName}</span>
      </div>
      <div className="mb-2 text-sm font-semibold leading-tight text-white">
        {activeProject.name}
      </div>
      <div className="flex items-center justify-between gap-2">
        {catBadge ? (
          <Badge
            variant={catBadge.variant}
            className={`text-[10px] font-medium ${catBadge.chromeClass}`}
            data-testid="active-project-category-badge"
          >
            {catBadge.label}
          </Badge>
        ) : (
          <span className="text-[11px] italic text-white/55">
            Sin categoría
          </span>
        )}
        <ProjectSwitcherDropdown />
      </div>
    </div>
  );
}
