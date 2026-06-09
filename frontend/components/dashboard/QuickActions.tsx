"use client";

/**
 * QuickActions · entry component context-aware.
 *
 * Sprint Polish block 2.B (post-MB-9.bis):
 * - Dashboard `/admin/dashboard` → genéricas (nuevo lead/proyecto/reunión/propuesta/retainer).
 * - Project detail `/admin/projects/[id]/...` → tier-based del proyecto
 *   (useProjectFeatures().data.categoria · BASICA | MEDIA | ALTA).
 *
 * El componente `QuickActions` (entry) detecta path con `usePathname()` y
 * delega a la variante correspondiente. `QuickActionsProjectDetail` asume
 * estar dentro de `ProjectFeaturesProvider` (montado en
 * `(admin)/admin/projects/[id]/layout.tsx`).
 */
import {
  Banknote,
  FileSignature,
  FileText,
  Folder,
  Gavel,
  LifeBuoy,
  MessageSquare,
  Plus,
  Radar,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  Users,
  Video,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { buttonVariants } from "@/components/ui/button";
import { ROUTES } from "@/lib/constants";
import { useProjectFeatures } from "@/lib/contexts/ProjectFeaturesContext";
import type { EnsCategory } from "@/lib/feature-flags.types";
import { cn } from "@/lib/utils";

interface Action {
  label: string;
  href: string;
  icon: LucideIcon;
}


const PROJECT_DETAIL_PATH = /^\/admin\/projects\/([^/]+)(\/.*)?$/;


function extractProjectIdFromPath(pathname: string | null): string | null {
  if (!pathname) return null;
  const match = PROJECT_DETAIL_PATH.exec(pathname);
  if (!match) return null;
  const id = match[1];
  if (id === "new" || id === "") return null;
  return id;
}


const DASHBOARD_ACTIONS: Action[] = [
  { label: "Nuevo lead", href: `${ROUTES.pipeline}?new=1`, icon: Plus },
  { label: "Nuevo proyecto", href: `${ROUTES.projects}?new=1`, icon: Users },
  { label: "Nueva reunión", href: `${ROUTES.meetings}/new`, icon: Video },
  {
    label: "Generar propuesta",
    href: `${ROUTES.pipeline}?action=proposal`,
    icon: FileText,
  },
  { label: "Consola retainer", href: ROUTES.retainer, icon: ShieldCheck },
];


// FRENTE G · "acceso total desde el dashboard" (directiva Marcos · 0 features
// inalcanzables). Navegación directa a TODAS las herramientas admin cross-cliente
// desde el dashboard principal (además del sidebar).
const DASHBOARD_NAV: Action[] = [
  { label: "Proyectos", href: ROUTES.projects, icon: Folder },
  { label: "Operaciones", href: ROUTES.operations, icon: ShieldCheck },
  { label: "Compliance", href: ROUTES.compliance, icon: Gavel },
  { label: "SIEM", href: ROUTES.siem, icon: ShieldAlert },
  { label: "Copiloto", href: ROUTES.copilot, icon: LifeBuoy },
  { label: "Mensajes", href: ROUTES.messages, icon: MessageSquare },
  { label: "Finanzas", href: ROUTES.finance, icon: Banknote },
  { label: "Ajustes", href: ROUTES.settings, icon: Settings2 },
];


function buildProjectActions(
  projectId: string,
  categoria: EnsCategory | undefined,
): Action[] {
  const base = `/admin/projects/${projectId}`;
  const actions: Action[] = [
    {
      label: "Categorización ENS",
      href: `${base}/archetype`,
      icon: ShieldCheck,
    },
    { label: "Evidencias", href: `${base}/evidence`, icon: Folder },
    { label: "Obligaciones", href: `${base}/obligations`, icon: FileText },
    { label: "Conformidad", href: `${base}/conformity`, icon: FileSignature },
  ];

  if (categoria === "MEDIA" || categoria === "ALTA") {
    actions.push({
      label: "Riesgos MAGERIT",
      href: `${base}/dossier`,
      icon: ShieldAlert,
    });
  }
  if (categoria === "ALTA") {
    actions.push({
      label: "Auditoría dry-run",
      href: `${base}/audit-dry-run`,
      icon: Radar,
    });
  }
  return actions;
}


function ActionLink({ action }: { action: Action }) {
  const Icon = action.icon;
  // Sub-atom Sesión 3B-2B.2 Phase A.1:
  // - data-testid="cta-quick-action-{slug}" → satisfies polish ctaVisible audit
  //   (selector `main [data-testid*='cta']`) · per-link unique testid.
  // - aria-label + title → native hover tooltip + a11y label for screen readers
  //   (icon-text is redundant but tooltip adds delay context for new users) ·
  //   satisfies polish helpTooltip audit (selector `main [aria-label]` once
  //   audit-helpers updated · current `main button[aria-label]` still misses
  //   anchors so we also add data-tooltip as universal marker).
  const slug = action.label.toLowerCase().replace(/\s+/g, "-");
  return (
    <Link
      href={action.href}
      aria-label={action.label}
      title={action.label}
      data-tooltip={action.label}
      data-testid={`cta-quick-action-${slug}`}
      className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
    >
      <Icon size={14} aria-hidden />
      <span>{action.label}</span>
    </Link>
  );
}


function QuickActionsDashboard() {
  return (
    <div className="flex flex-col gap-3" data-testid="quick-actions-dashboard">
      <div className="flex flex-wrap gap-2">
        {DASHBOARD_ACTIONS.map((a) => (
          <ActionLink key={a.href} action={a} />
        ))}
      </div>
      {/* FRENTE G · acceso total a herramientas desde el dashboard */}
      <div
        className="flex flex-wrap gap-2 border-t border-fulkro-ink-200 pt-3"
        data-testid="quick-actions-dashboard-nav"
      >
        {DASHBOARD_NAV.map((a) => (
          <ActionLink key={a.href} action={a} />
        ))}
      </div>
    </div>
  );
}


function QuickActionsProjectDetail({ projectId }: { projectId: string }) {
  const { data, isLoading } = useProjectFeatures();
  const actions = buildProjectActions(projectId, data?.categoria);
  return (
    <div
      className="flex flex-wrap gap-2"
      data-testid="quick-actions-project-detail"
      data-categoria={data?.categoria ?? (isLoading ? "loading" : "unknown")}
    >
      {actions.map((a) => (
        <ActionLink key={a.href} action={a} />
      ))}
    </div>
  );
}


export function QuickActions() {
  const pathname = usePathname();
  const projectId = extractProjectIdFromPath(pathname);
  if (projectId) {
    return <QuickActionsProjectDetail projectId={projectId} />;
  }
  return <QuickActionsDashboard />;
}
