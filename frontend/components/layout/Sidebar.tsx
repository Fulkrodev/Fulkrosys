"use client";

import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Archive,
  Banknote,
  Bell,
  Briefcase,
  Calendar,
  FolderOpen,
  Gavel,
  Home,
  Layers,
  LifeBuoy,
  Loader2,
  MessageSquare,
  Search,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useClients } from "@/hooks/useClients";
import { api } from "@/lib/api";
import { ROUTES } from "@/lib/constants";
import type { Client } from "@/lib/types";
import { cn } from "@/lib/utils";

import { ActiveProjectBanner } from "./ActiveProjectBanner";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Passive count badge · render only when truthy AND > 0. */
  badgeCount?: number | null;
}

const TOP_NAV: NavItem[] = [
  { label: "Dashboard", href: ROUTES.dashboard, icon: Home },
  // Sub-atom Sesión 3B-2B.3 Phase X.2 · R23 strict cleanup.
  // Removed: "Clientes" (cliente entity ≈ project entity 1:1 MVP · selector
  // handled via /admin/projects). "Retainer" cross-cliente (per-project route
  // via /admin/projects/[id]/retainer suffices). "Churn risk" (migrated
  // as widget into /admin/dashboard · Step 4d).
  { label: "Reuniones", href: ROUTES.meetings, icon: Calendar },
  { label: "Proyectos", href: ROUTES.projects, icon: FolderOpen },
  { label: "Copiloto", href: ROUTES.copilot, icon: LifeBuoy },
  { label: "Operaciones", href: ROUTES.operations, icon: ShieldCheck },
  // FRENTE N · SIEM · consola de eventos de seguridad (correlación pentest)
  { label: "SIEM", href: ROUTES.siem, icon: ShieldAlert },
  // MB-9.bis · Self-compliance dashboards. The badge below is fed by
  // ``useComplianceSidebarStatus`` and surfaces ``open_alerts`` as a
  // discreet count — informational only, NEVER blocking (Marcos
  // NO-BLOCKER principle · LECCIÓN-OPS-046).
  { label: "Compliance", href: ROUTES.compliance, icon: Gavel },
  // Sub-atom 1.D.E v3.11 · MCPs sidebar global eliminada (R23 sostener
  // firmísimo · directiva Marcos). MCPs accionables SOLO via
  // /admin/projects/[id]/mcps · ProjectTabs entry "Pentest MCPs".
  { label: "Mensajes", href: ROUTES.messages, icon: MessageSquare },
  { label: "Notificaciones", href: ROUTES.notifications, icon: Bell },
  { label: "Finanzas", href: ROUTES.finance, icon: Banknote },
  { label: "Ajustes", href: ROUTES.settings, icon: Settings2 },
];


/** Lightweight shape pulled from /admin/compliance/monitor/status. */
interface ComplianceSidebarStatus {
  overall: string;
  open_alerts: number;
}


/** React Query hook · 60-second polling, no refetch on focus, slate badge. */
function useComplianceSidebarStatus() {
  return useQuery<ComplianceSidebarStatus>({
    queryKey: ["sidebar", "compliance-status"],
    queryFn: () =>
      api<ComplianceSidebarStatus>("/api/v1/admin/compliance/monitor/status"),
    refetchInterval: 60_000,
    refetchOnWindowFocus: false,
    staleTime: 30_000,
    // Sidebar is also rendered by routes outside the compliance flow
    // (pipeline / clients / ...). The request will 401 if the
    // user isn't an owner — swallow that silently rather than spam errors.
    retry: false,
  });
}

interface SidebarProps {
  onOpenCommandPalette: () => void;
  onNavigate?: () => void;
  className?: string;
}

export function Sidebar({
  onOpenCommandPalette,
  onNavigate,
  className,
}: SidebarProps) {
  const pathname = usePathname();
  const { data: clients, isLoading } = useClients();
  const { data: complianceStatus } = useComplianceSidebarStatus();
  const complianceAlertCount = complianceStatus?.open_alerts ?? 0;
  // #29 · clientes con retainer ACTIVO → bucket "En retainer" real (antes vacío).
  const { data: activeRetainerIds } = useQuery({
    queryKey: ["retainer", "active-client-ids"],
    queryFn: async () => {
      const res = await api<{ client_ids: string[] }>(
        "/api/v1/retainer/active-client-ids",
      );
      return new Set(res.client_ids);
    },
    staleTime: 60_000,
  });

  return (
    <aside
      // Sub-atom Sesión 3B-2B.2 Path A.0 re-run · architectural fix.
      //
      // WCAG color-contrast (root cause · axe-core/axe.js:17616-17620):
      //   ANY element with `background-image` (even with solid bg-color
      //   underneath) is marked "bgGradient" by axe-core → contrast check
      //   reports "incomplete" → serious violation. Previous inline-style
      //   fix combining bg-color + bg-image did NOT work because axe
      //   bails before reading the color. Fix: `.sidebar-chrome` utility
      //   class (globals.css) puts the gradient on a `::before`
      //   pseudo-element. axe-core walks DOM parents only · pseudo-
      //   elements invisible to it. Aside reports solid bg-color #0a1a5c
      //   only → contrast computed correctly.
      //
      // Full-height (root cause · empirical Marcos screenshot):
      //   Parent `(admin)/layout.tsx` outer `<div>` has `bg-fulkro-ink-50`
      //   (#fafafa = visible as "white"). On certain viewports/Chrome
      //   versions the sidebar's `sticky+flex+h-dvh` leaves a 1+px gap
      //   exposing parent's light bg → looks like "sidebar cut off after
      //   Churn risk". `sticky top-0` removed (parent doesn't scroll · no-op
      //   anyway · was producing the gap). `min-h-dvh` removed (redundant
      //   with `h-dvh`). Parent layout now uses `bg-[#0a1a5c]` matching
      //   sidebar so any pixel-level gap is invisible.
      className={cn(
        "sidebar-chrome flex h-dvh w-sidebar shrink-0 flex-col border-r border-white/10 text-white",
        className,
      )}
    >
      <div className="px-6 py-6">
        <Link
          href={ROUTES.dashboard}
          onClick={onNavigate}
          className="inline-flex"
        >
          <Image
            src="/brand/fulkro-logo-mono-white.svg"
            alt="FULKRO"
            width={240}
            height={64}
            priority
          />
        </Link>
      </div>

      {/* Sub-atom 1.E.2 · Phase C · ADR-054 · active project persistent
          banner cross-navigation. Visible 100% admin pages. Click trigger
          en banner → ProjectSwitcherDropdown (switch fluido entre projects). */}
      <ActiveProjectBanner />

      <nav aria-label="Navegación principal" className="px-3">
        <ul className="space-y-0.5">
          {TOP_NAV.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href ||
              (item.href !== ROUTES.dashboard && pathname.startsWith(item.href));
            // Resolve the badge count for this nav item. Today only
            // the Compliance entry is wired; other entries remain plain
            // until their owning motors expose similar status hooks.
            const badge =
              item.href === ROUTES.compliance
                ? complianceAlertCount
                : item.badgeCount ?? 0;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={onNavigate}
                  className={cn(
                    "flex items-center gap-3 rounded-md py-2 pl-3 pr-3 text-[15px] font-medium transition-colors border-l-4",
                    active
                      ? "bg-[var(--fulkro-chrome-active-bg)] text-white border-l-white/60"
                      : "text-white hover:bg-[var(--fulkro-chrome-hover-bg)] border-l-transparent",
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  <Icon size={16} className="text-white" />
                  <span className="flex-1">{item.label}</span>
                  {badge > 0 ? (
                    <span
                      className="inline-flex min-w-[1.4rem] items-center justify-center rounded-full bg-white/15 px-1.5 py-0.5 text-[11px] font-mono font-medium text-white/90"
                      aria-label={`${badge} ${
                        badge === 1 ? "elemento" : "elementos"
                      } pendiente${badge === 1 ? "" : "s"}`}
                    >
                      {badge}
                    </span>
                  ) : null}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="mt-6 border-t border-white/10" />

      <div
        className="scrollbar-fulkro min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-4"
        data-testid="sidebar-clients-scroll"
      >
        <ClientSection
          label="Clientes activos"
          icon={Layers}
          items={filterActive(clients)}
          loading={isLoading}
          empty="Aún no hay clientes en la BD."
        />
        <ClientSection
          label="En retainer"
          icon={Briefcase}
          items={filterRetainer(clients, activeRetainerIds)}
          loading={isLoading}
          empty="Ningún cliente en retainer."
          className="mt-5"
        />
        <div className="mt-5 space-y-1 border-t border-white/15 pt-4 text-sm text-white/90">
          {/* #23 · sin counts FALSOS hardcodeados (eran 3/12 · MVP). El Client
              del sidebar no expone lifecycle_state → mostramos solo el acceso a
              Operaciones (donde se gestionan archivables/archivados), sin
              inventar números. */}
          <StaticBucket
            label="Archivables"
            icon={Archive}
            href={ROUTES.operations}
          />
          <StaticBucket
            label="Archivados"
            icon={Archive}
            href={ROUTES.operations}
          />
        </div>
      </div>

      <div className="p-3">
        <Button
          variant="outline"
          size="md"
          className="w-full border-white/15 bg-white/10 font-medium text-white hover:bg-white/15 hover:text-white"
          onClick={onOpenCommandPalette}
        >
          <Search size={14} className="text-white" />
          <span className="flex-1 text-left">Buscar</span>
          <kbd className="rounded bg-white/15 px-1.5 py-0.5 font-mono text-[10px] text-white">
            ⌘K
          </kbd>
        </Button>
      </div>
    </aside>
  );
}

function ClientSection({
  label,
  icon: Icon,
  items,
  loading,
  empty,
  className,
}: {
  label: string;
  icon: LucideIcon;
  items: Client[];
  loading: boolean;
  empty: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <div className="flex items-center gap-2 px-2 pb-2 text-xs font-semibold uppercase tracking-wider text-white/80">
        <Icon size={12} className="text-white/80" />
        {label}
      </div>
      {loading ? (
        <div className="flex items-center gap-2 rounded-md px-2 py-2 text-sm text-white/80">
          <Loader2 size={13} className="animate-spin" />
          cargando clientes…
        </div>
      ) : items.length === 0 ? (
        <p className="rounded-md border border-dashed border-white/20 px-2 py-2 text-xs leading-snug text-white/70">
          {empty}
        </p>
      ) : (
        <ul className="space-y-0.5">
          {items.map((client) => (
            <li key={client.id}>
              <Link
                href={`${ROUTES.clients}/${clientSlug(client)}`}
                className="flex items-center gap-2 rounded-md px-2 py-2 text-sm font-medium text-white/95 hover:bg-[var(--fulkro-chrome-hover-bg)] hover:text-white"
              >
                <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full bg-white/55" />
                <span className="truncate">{client.nombre}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StaticBucket({
  label,
  count,
  icon: Icon,
  href,
}: {
  label: string;
  count?: number;
  icon: LucideIcon;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-2 rounded-md px-2 py-2 font-medium text-white/90 hover:bg-[var(--fulkro-chrome-hover-bg)] hover:text-white"
    >
      <Icon size={14} className="text-white/90" />
      <span className="flex-1 truncate">{label}</span>
      {typeof count === "number" ? (
        <span className="rounded bg-white/15 px-1.5 py-0.5 font-mono text-[11px] text-white">
          {count}
        </span>
      ) : null}
    </Link>
  );
}

function filterActive(clients?: Client[]): Client[] {
  return clients ?? [];
}

/**
 * #29 · clientes con un retainer ACTIVO, resuelto vía
 * GET /retainer/active-client-ids (antes el bucket se renderizaba siempre vacío
 * porque el Client del sidebar no trae flag de retainer).
 */
function filterRetainer(
  clients?: Client[],
  activeIds?: Set<string>,
): Client[] {
  if (!clients || !activeIds) return [];
  return clients.filter((c) => activeIds.has(c.id));
}

function clientSlug(client: Client): string {
  const base = client.nombre
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return base || client.id;
}
