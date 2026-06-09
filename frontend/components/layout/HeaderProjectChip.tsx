"use client";

import { FolderKanban } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { useActiveProjectStore } from "@/lib/stores/active-project-store";

// 2026-06-09 · Polish gate · píldora sólida clara sobre topbar oscuro (las
// variantes translúcidas del Badge son para tarjetas blancas · sobre chrome
// oscuro el texto -700 daba ~2:1 FAIL AA). Mirror ActiveProjectBanner.
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

/**
 * HeaderProjectChip · Sesión 3B-2B.4 Phase 1.2 · ADR-054 propagation.
 *
 * Visible solo en rutas `/admin/projects/[id]/*` · muestra cliente + proyecto
 * + ENS category badge en topbar para reforzar context Marcos cross-page.
 *
 * Source: useActiveProjectStore (ya hidratado por ActiveProjectSync).
 * Click → `/admin/projects/{id}/dashboard`. Empty state suprimido (no render
 * cuando NO activeProject · evita layout shift initial mount).
 */
export function HeaderProjectChip() {
  const pathname = usePathname();
  const activeProject = useActiveProjectStore((s) => s.activeProject);

  const onProjectRoute = pathname?.startsWith("/admin/projects/") ?? false;
  if (!onProjectRoute || !activeProject) {
    return null;
  }

  const catBadge = activeProject.ensCategory
    ? CATEGORIA_BADGE[activeProject.ensCategory]
    : null;

  return (
    <Link
      href={`/admin/projects/${activeProject.id}/dashboard`}
      data-testid="header-project-chip"
      className="hidden items-center gap-2 rounded-md border border-white/15 bg-white/[0.08] px-3 py-1.5 text-sm text-white transition-colors hover:bg-white/[0.14] md:inline-flex"
      aria-label={`Proyecto activo: ${activeProject.clientName} · ${activeProject.name}`}
    >
      <FolderKanban size={14} className="text-white/80" aria-hidden="true" />
      <span className="hidden text-[11px] font-semibold uppercase tracking-wider text-white/75 lg:inline">
        {activeProject.clientName}
      </span>
      <span className="font-medium text-white">{activeProject.name}</span>
      {catBadge ? (
        <Badge
          variant={catBadge.variant}
          className={`text-[10px] font-medium ${catBadge.chromeClass}`}
          data-testid="header-project-chip-category"
        >
          {catBadge.label}
        </Badge>
      ) : null}
    </Link>
  );
}
