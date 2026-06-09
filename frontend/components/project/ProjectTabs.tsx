"use client";

import type * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  AlertTriangle,
  Bug,
  BookOpenCheck,
  Building2,
  Cloud,
  Compass,
  ClipboardCheck,
  Crown,
  DoorOpen,
  FileSearch,
  FileSignature,
  FlaskConical,
  FolderKanban,
  GanttChartSquare,
  Gavel,
  GraduationCap,
  HardDrive,
  Layers,
  LayoutDashboard,
  LayoutPanelLeft,
  Lightbulb,
  ListChecks,
  MessageCircle,
  MessageSquare,
  Network,
  Palette,
  Radar,
  RefreshCcw,
  Repeat,
  Scale,
  ScrollText,
  Search,
  Settings,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Stethoscope,
  Target,
  Beaker,
  TrendingUp,
  UserCog,
  UserPlus,
  Users2,
  Wallet,
  Warehouse,
  Workflow,
  type LucideIcon,
} from "lucide-react";

import { DiscrepanciasCriticalBadge } from "@/components/agents/DiscrepanciasCriticalBadge";

import { useProjectFeatures } from "@/lib/contexts/ProjectFeaturesContext";
import { cn } from "@/lib/utils";
import type {
  EnsCategory,
  FeatureKey,
  ProjectFeatureFlags,
  PymeArchetype,
} from "@/lib/feature-flags.types";

interface TabDescriptor {
  href: string;
  label: string;
  icon: LucideIcon;
  /** When true, active match is exact (no startsWith). */
  exact?: boolean;
  /** Mostrar solo si feature aplica al proyecto (ADR-036 MB-17.3). */
  feature?: FeatureKey;
  /** Mostrar solo si categoría del proyecto está en este list. */
  categories?: EnsCategory[];
  /** Mostrar solo si arquetipo (lowercase enum) está en este list. */
  archetypes?: PymeArchetype[];
}

const MAIN_TABS: TabDescriptor[] = [
  { href: "/summary", label: "Resumen", icon: LayoutDashboard, exact: false },
  // Sub-area 2B Sesión 3B-2B.9 CLUSTER 2 · vista cronológica admin R30 inverso
  // (thin wrapper project-scoped reusa ProjectCronologicaView · OPS-026 DRY)
  { href: "/workflow", label: "Workflow", icon: Workflow },
  // Sub-atom 1.C.D.A.0 v3.8 · admin source of truth 19 dimensiones adaptación
  { href: "/dimensiones", label: "Dimensiones", icon: Compass },
  { href: "/roadmap", label: "Roadmap", icon: Radar },
  { href: "/diagnosis", label: "Diagnóstico", icon: Network },
  { href: "/obligations", label: "Obligaciones", icon: Scale },
  { href: "/plan", label: "Plan", icon: GanttChartSquare },
  { href: "/implementation", label: "Implantación", icon: ListChecks },
  // Sub-atom 1.D.F.A v3.11 · M03 DdA admin page (73 medidas Anexo II)
  { href: "/dda", label: "DdA", icon: ClipboardCheck },
  { href: "/evidence", label: "Evidencias", icon: FileSearch },
  { href: "/dossier", label: "Dossier", icon: BookOpenCheck },
  { href: "/financial", label: "Financiero", icon: Wallet },
  { href: "/communication", label: "Comunicación", icon: MessageSquare },
  { href: "/risks", label: "Riesgos", icon: ShieldAlert },
  { href: "/magerit", label: "MAGERIT", icon: Layers },
];

const SUB_TABS: TabDescriptor[] = [
  { href: "/documents", label: "Documentos (IDMS)", icon: FolderKanban },
  // #18 · chat en tiempo real con el cliente (m21 AdminChatPanel) · antes
  // huérfano en la navegación. Distinto de "Comunicación" (m18 · notificaciones).
  { href: "/chat", label: "Chat cliente", icon: MessageCircle },
  { href: "/conformity", label: "Conformidad", icon: FileSignature },
  // Sub-atom 1.D.D.A v3.11 · M14 Contracts admin standalone page
  { href: "/contratos", label: "Contratos", icon: FileSignature },
  { href: "/changes", label: "Cambios", icon: Target },
  // Verificación + Auditoría · solo MEDIA+/ALTA (BASICA usa autoevaluación 809)
  {
    href: "/verification",
    label: "Verificación",
    icon: ShieldCheck,
    categories: ["MEDIA", "ALTA"],
  },
  {
    href: "/audit",
    label: "Auditoría",
    icon: ClipboardCheck,
    categories: ["MEDIA", "ALTA"],
  },
  { href: "/equipo", label: "Equipo", icon: UserCog },
  // Sub-area 2C Sesión 3B-2B.9 CLUSTER 2 · settings HUB thin landing 6 routes existing
  // (Pattern P-CL2-4 ENRICH · OPS-026 DRY · NO duplicate funcionalidad)
  { href: "/settings", label: "Configuración", icon: Settings },
  // Sub-atom Sesión 3B-2B.3 Phase X.4a · cliente entity datos (was /admin/clients/[id]
  // Datos tab before R23 strict cleanup · migrated to project-scoped 1:1 MVP).
  { href: "/cliente-info", label: "Datos cliente", icon: Building2 },
  // Sub-atom Sesión 3B-2B.3 Phase X.4e · auditor handoff magic links project-scoped
  // (was /admin/magic-links cross-cliente · 35 purposes → 3 auditor purposes only).
  { href: "/auditor-handoff", label: "Entrega auditor", icon: ScrollText },
  // Sub-atom 1.E.2.bis Phase C · client_users management per project
  { href: "/users", label: "Usuarios portal", icon: Users2 },
  // Sub-atom 1.E.2.bis Phase D · per-project personalización (branding · settings)
  { href: "/personalizacion", label: "Personalización", icon: Palette },
  { href: "/roles", label: "Topología de roles", icon: Users2 },
  // Sub-atom 1.D.A v3.10 · A21 detector discrepancias ENS-only · admin tab
  { href: "/discrepancies", label: "Discrepancias", icon: AlertTriangle },
  // Sub-atom 1.D.C v3.11 · Dashboard K.3 Planes Acción cross-motor · admin tab
  { href: "/planes-accion", label: "Planes acción", icon: ListChecks },
  // Sub-atom 1.D.E v3.11 · MCPs accionables project-scoped (R23 firmísimo)
  { href: "/mcps", label: "Pentest MCPs", icon: Shield },
  // Sub-atom 1.D.X.J v3.12 · Cloud Connectors unified layer (M16 OAuth reuse)
  { href: "/cloud-connectors", label: "Conexiones Cloud", icon: Cloud },
  // Sub-atom 1.E.1.B.2 v3.12 · AI Act art.50 transparency log (admin full view)
  { href: "/transparency", label: "Transparencia IA", icon: ScrollText },
  // (Retainer project-scoped vive en "/retainer" más abajo · se eliminó el tab
  //  duplicado y roto "/admin/retainers" que renderizaba /admin/projects/{id}/admin/retainers → 404.)
  // Sub-atom 1.D.F.B v3.11 · ProjectTabs sweep · 10 entries faltantes
  // motores existing (M01 archetype · M10/A11 audit-dry-run · M16 onboarding ·
  // M22 awareness+discovery · M23 retainer per-proyecto · M26 backup · aepd ·
  // bia · workspace). R23 sostener firmísimo (TODO project-scoped vía /admin/projects/[id]/X).
  { href: "/workspace", label: "Workspace", icon: LayoutPanelLeft },
  { href: "/onboarding", label: "Onboarding", icon: UserPlus },
  { href: "/archetype", label: "Arquetipo", icon: Building2 },
  { href: "/discovery", label: "Discovery", icon: Search },
  { href: "/awareness", label: "Concienciación", icon: Lightbulb },
  { href: "/audit-dry-run", label: "Auditoría seca", icon: FlaskConical },
  { href: "/aepd", label: "AEPD", icon: Gavel },
  { href: "/bia", label: "BIA", icon: TrendingUp },
  { href: "/backup-policy", label: "Backups", icon: HardDrive },
  { href: "/retainer", label: "Retainer (proy.)", icon: Repeat },
  { href: "/providers", label: "Proveedores", icon: Warehouse },
  { href: "/renewal", label: "Renovación", icon: RefreshCcw },
  { href: "/exit", label: "Cierre", icon: DoorOpen },
];

// Tabs específicos categoría ALTA · accesos rápidos a sub-vistas
// /verification?focus=... y obligaciones específicas (ADR-036
// routes mapping · sub-routes dedicadas diferidas MB-19+).
const PROFILE_TABS: TabDescriptor[] = [
  {
    href: "/verification?focus=pentest_cpstic",
    label: "Pentest CPSTIC",
    icon: Bug,
    feature: "alta_pentest_cpstic",
  },
  {
    href: "/verification?focus=red_team",
    label: "Red Team",
    icon: Crown,
    feature: "alta_red_team",
  },
  {
    href: "/verification?focus=cpstic_products",
    label: "Productos CPSTIC",
    icon: Beaker,
    feature: "alta_productos_cpstic",
  },
  // Arquetipos
  {
    href: "/obligations?regulation=rgpd_art9",
    label: "Art.9 RGPD (salud)",
    icon: Stethoscope,
    feature: "art9_rgpd_data",
  },
  {
    href: "/obligations?regulation=dora",
    label: "DORA",
    icon: ShieldAlert,
    feature: "dora_dual_compliance",
  },
  {
    href: "/obligations?regulation=pce_univ",
    label: "PCE Universidades",
    icon: GraduationCap,
    feature: "pce_universidades",
  },
];

function isTabApplicable(
  tab: TabDescriptor,
  data: ProjectFeatureFlags | undefined,
  hasFeature: (k: FeatureKey) => boolean,
): boolean {
  if (!tab.feature && !tab.categories && !tab.archetypes) return true;
  if (!data) return false;
  if (tab.feature) return hasFeature(tab.feature);
  if (tab.categories) return tab.categories.includes(data.categoria);
  if (tab.archetypes && data.archetype) {
    return tab.archetypes.includes(data.archetype);
  }
  return false;
}

function pathOnly(href: string): string {
  const idx = href.indexOf("?");
  return idx === -1 ? href : href.slice(0, idx);
}

export function ProjectTabs({ projectId }: { projectId: string }) {
  const pathname = usePathname();
  const { data, hasFeature } = useProjectFeatures();
  const basePath = `/admin/projects/${projectId}`;

  const visibleMain = MAIN_TABS.filter((t) =>
    isTabApplicable(t, data, hasFeature),
  );
  const visibleSub = SUB_TABS.filter((t) =>
    isTabApplicable(t, data, hasFeature),
  );
  const visibleProfile = PROFILE_TABS.filter((t) =>
    isTabApplicable(t, data, hasFeature),
  );

  return (
    <div className="flex flex-col gap-4">
      <nav
        aria-label="Secciones del proyecto"
        style={{
          backgroundColor: "var(--fulkro-surface-glass)",
          borderColor: "var(--fulkro-surface-glass-border)",
        }}
        className="flex items-center gap-1.5 overflow-x-auto rounded-xl border p-2 shadow-sm md:flex-wrap"
      >
        {visibleMain.map((tab) => (
          <TabLink
            key={tab.href}
            tab={tab}
            basePath={basePath}
            pathname={pathname}
          />
        ))}
      </nav>

      <nav
        aria-label="Otras vistas del proyecto"
        className="flex items-center gap-2.5 overflow-x-auto md:flex-wrap"
      >
        <span className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
          Extras
        </span>
        {visibleSub.map((tab) => (
          <SubTabLink
            key={tab.href}
            tab={tab}
            basePath={basePath}
            pathname={pathname}
            extra={
              tab.href === "/discrepancies" ? (
                <DiscrepanciasCriticalBadge projectId={projectId} />
              ) : undefined
            }
          />
        ))}
      </nav>

      {visibleProfile.length > 0 && (
        <nav
          aria-label="Vistas específicas categoría/arquetipo"
          className="flex items-center gap-2.5 overflow-x-auto md:flex-wrap"
        >
          <span className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
            Específico
          </span>
          {visibleProfile.map((tab) => (
            <SubTabLink
              key={tab.href}
              tab={tab}
              basePath={basePath}
              pathname={pathname}
            />
          ))}
        </nav>
      )}
    </div>
  );
}

function TabLink({
  tab,
  basePath,
  pathname,
}: {
  tab: TabDescriptor;
  basePath: string;
  pathname: string;
}) {
  const href = `${basePath}${tab.href}`;
  const active = pathname.startsWith(`${basePath}${pathOnly(tab.href)}`);
  const Icon = tab.icon;
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center gap-2.5 rounded-lg px-4 py-2.5 text-base font-bold transition-colors",
        active
          ? "bg-fulkro-primary-900 text-white shadow-md"
          : "text-[color:var(--fulkro-body)] hover:bg-[color:var(--fulkro-surface-glass-strong)] hover:text-[color:var(--fulkro-title)]",
      )}
      aria-current={active ? "page" : undefined}
    >
      <Icon size={18} strokeWidth={2.2} />
      {tab.label}
    </Link>
  );
}

function SubTabLink({
  tab,
  basePath,
  pathname,
  extra,
}: {
  tab: TabDescriptor;
  basePath: string;
  pathname: string;
  extra?: React.ReactNode;
}) {
  const href = `${basePath}${tab.href}`;
  const active = pathname.startsWith(`${basePath}${pathOnly(tab.href)}`);
  const Icon = tab.icon;
  return (
    <Link
      href={href}
      style={
        active
          ? {
              backgroundColor: "var(--fulkro-surface-glass-strong)",
              borderColor: "var(--fulkro-surface-glass-border)",
              color: "var(--fulkro-title)",
            }
          : {
              borderColor: "transparent",
              color: "var(--fulkro-body)",
            }
      }
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm font-semibold transition-colors",
        active
          ? ""
          : "hover:border-[color:var(--fulkro-surface-glass-border)] hover:bg-[color:var(--fulkro-surface-glass)]",
      )}
    >
      <Icon size={15} strokeWidth={2.2} />
      {tab.label}
      {extra}
    </Link>
  );
}
