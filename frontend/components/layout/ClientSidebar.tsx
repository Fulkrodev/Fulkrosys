"use client";

/**
 * ClientSidebar — SIMPLIFIED · sub-atom 1.D.F.bis.III.D v3.11 indispensable-only.
 *
 * Modelo "indispensable-cliente-only":
 *   - Cliente HACE: aportar info empresa · subir docs · firmar Ed25519 · LMS · ver tasks
 *   - Marcos OPERA todo lo demás desde admin
 *
 * Sidebar refactor 14 → 10 entries agrupados por sección:
 *
 *   PRINCIPAL (4 entries · lo que el cliente HACE):
 *     1. Inicio                → /client-portal/         (Home)
 *     2. Mis tareas            → /client-portal/tasks    (CheckSquare · catálogo lo que TÚ haces)
 *     3. Mis firmas pendientes → /client-portal/firmas-hub (FileSignature)
 *     4. Subir documentos      → /client-portal/files    (FolderUp)
 *
 *   MI EMPRESA (2 entries · info empresa):
 *     5. Onboarding inicial    → /client-portal/onboarding (LayoutDashboard)
 *     6. Facturación           → /client-portal/billing  (Receipt)
 *
 *   COMUNICACIÓN (3 entries · chat consultor):
 *     7. Chat con Marcos       → /client-portal/chat     (MessageCircle)
 *     8. Mensajes              → /client-portal/inbox    (MessageSquare)
 *     9. WhatsApp opt-in       → /client-portal/whatsapp (Smartphone)
 *
 *   MI CUENTA (1 entry):
 *     10. Mi cuenta            → /client-portal/account  (User)
 *
 *   ────── separador ──────
 *   Salir → action logout (LogOut)
 *
 * Pages NO sidebar (acceso vía tasks contextual · NO eliminan):
 *   /policies · /dda · /magerit · /conformidad · /dpc-anual · /actas · /incidents
 *   /retainer-checkin · /pentest-authorization · /workflow · /evidencias
 *   → Cliente llega vía tareas específicas que Marcos asigna · NO navega manualmente
 *
 * R29 + R30 inverso sostenidos · cliente sidebar friendly NO admin lingo.
 */

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BadgeCheck,
  CalendarClock,
  CalendarRange,
  CheckSquare,
  ClipboardList,
  Cloud,
  FileSignature,
  FolderUp,
  Home,
  ShieldAlert,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  MessageCircle,
  MessageSquare,
  Receipt,
  Settings,
  ShieldCheck,
  Smartphone,
  User,
  Wrench,
  type LucideIcon,
} from "lucide-react";

import { useLogout } from "@/hooks/useLogout";
import { useClientBranding } from "@/lib/branding/ClientBrandingProvider";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  exact?: boolean;
}

interface NavSection {
  label: string | null;
  items: NavItem[];
}

const CLIENT_NAV_SECTIONS: NavSection[] = [
  {
    label: null,
    items: [
      { label: "Inicio", href: "/client-portal/", icon: Home, exact: true },
      {
        label: "Cumplimiento",
        href: "/client-portal/cumplimiento",
        icon: ShieldCheck,
      },
      {
        // #12 · la página existía pero estaba huérfana (sin entrada en nav).
        // El cliente VE/DESCARGA su Declaración de Conformidad (Premisa #1
        // BÁSICA) o sigue el estado ENAC (MEDIA/ALTA).
        label: "Mi certificación",
        href: "/client-portal/certificacion",
        icon: BadgeCheck,
      },
      {
        label: "Mis tareas",
        href: "/client-portal/tasks",
        icon: CheckSquare,
      },
      {
        label: "Firmas pendientes",
        href: "/client-portal/firmas-hub",
        icon: FileSignature,
      },
      {
        label: "Subir documentos",
        href: "/client-portal/files",
        icon: FolderUp,
      },
      {
        // #24 · icono distinto del de "Cumplimiento" (antes ambos ShieldCheck
        // → confusión visual). Wrench = remediaciones/mejoras.
        label: "Mejoras propuestas",
        href: "/client-portal/remediaciones",
        icon: Wrench,
      },
      {
        // Sesión 3B-2B.8 Phase 1E · plan adecuación cliente READ-ONLY
        label: "Mi plan ENS",
        href: "/client-portal/plan",
        icon: CalendarRange,
      },
      {
        // Auditoría 2026-06-07 · "todas las tareas del cliente en el portal":
        // páginas existentes pero huérfanas en el nav. El cliente DEBE poder
        // llegar a incidentes (notificar CCN-CERT), actas (firmar) y la DPC
        // anual (revisión post-certificación) sin URL directa.
        label: "Incidentes",
        href: "/client-portal/incidents",
        icon: ShieldAlert,
      },
      {
        label: "Actas",
        href: "/client-portal/actas",
        icon: ClipboardList,
      },
      {
        label: "DPC anual",
        href: "/client-portal/dpc-anual",
        icon: CalendarClock,
      },
      {
        // feat/fulkro-100 · continuidad de negocio (BIA/DRP): el cliente aporta
        // su tolerancia (RTO/RPO) y aprueba su Plan de Continuidad.
        label: "Continuidad",
        href: "/client-portal/continuidad",
        icon: LifeBuoy,
      },
    ],
  },
  {
    label: "Mi empresa",
    items: [
      {
        label: "Onboarding",
        href: "/client-portal/onboarding",
        icon: LayoutDashboard,
      },
      {
        // Sesión 3B-2B.8 Phase 1C · steady-state mgmt cloud connections
        label: "Conexiones cloud",
        href: "/client-portal/cloud-connections",
        icon: Cloud,
      },
      {
        label: "Facturación",
        href: "/client-portal/billing",
        icon: Receipt,
      },
    ],
  },
  {
    label: "Comunicación",
    items: [
      {
        label: "Chat con Marcos",
        href: "/client-portal/chat",
        icon: MessageCircle,
      },
      {
        label: "Mensajes",
        href: "/client-portal/inbox",
        icon: MessageSquare,
      },
      {
        label: "WhatsApp",
        href: "/client-portal/whatsapp",
        icon: Smartphone,
      },
    ],
  },
  {
    label: "Mi cuenta",
    items: [
      {
        label: "Mi cuenta",
        href: "/client-portal/account",
        icon: User,
      },
      {
        // #27 · hub de Ajustes (notificaciones · seguridad/MFA · WhatsApp) ·
        // antes /client-portal/settings no tenía índice (404) ni enlace.
        label: "Ajustes",
        href: "/client-portal/settings",
        icon: Settings,
      },
    ],
  },
];

interface ClientSidebarProps {
  onNavigate?: () => void;
  className?: string;
}

export function ClientSidebar({ onNavigate, className }: ClientSidebarProps) {
  const pathname = usePathname();
  const { handleLogout, loading: logoutLoading } = useLogout("client");
  // Sesión 3B-2B.8 CLUSTER 4 Phase 4D · multi-tenant cliente logo display
  const { logoUrl, branding } = useClientBranding();

  return (
    <aside
      // Architectural fix · gradient via ::before pseudo-element so axe-core
      // computes contrast against solid #0a1a5c (see Sidebar.tsx for full
      // root-cause explanation referencing axe-core/axe.js:17616-17620).
      className={cn(
        "sidebar-chrome flex h-dvh w-sidebar shrink-0 flex-col border-r border-white/10 text-white",
        className,
      )}
      aria-label="Navegación portal cliente"
      data-testid="cliente-sidebar"
    >
      <div className="px-6 py-6">
        <Link
          href="/client-portal/"
          onClick={onNavigate}
          className="inline-flex"
        >
          {logoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={logoUrl}
              alt={`Logo cliente ${branding?.client_id ?? ""}`.trim()}
              width={240}
              height={64}
              className="max-h-16 w-auto object-contain"
              data-testid="cliente-sidebar-cliente-logo"
            />
          ) : (
            <Image
              src="/brand/fulkro-logo-mono-white.svg"
              alt="FULKRO"
              width={240}
              height={64}
              priority
              data-testid="cliente-sidebar-fulkro-logo"
            />
          )}
        </Link>
      </div>

      <nav
        aria-label="Navegación principal cliente"
        className="px-3 flex-1 overflow-y-auto"
      >
        {CLIENT_NAV_SECTIONS.map((section, idx) => (
          <div
            key={section.label ?? `section-${idx}`}
            className={idx > 0 ? "mt-4" : ""}
          >
            {section.label && (
              <p
                className="px-3 mb-1.5 text-[10px] uppercase tracking-wider font-semibold text-white/55"
                data-testid={`cliente-nav-section-${section.label
                  .toLowerCase()
                  .replace(/\s+/g, "-")}`}
              >
                {section.label}
              </p>
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = item.exact
                  ? pathname === item.href ||
                    pathname === item.href.replace(/\/$/, "")
                  : pathname === item.href ||
                    pathname.startsWith(`${item.href}/`);
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
                      data-testid={`cliente-nav-${item.label
                        .toLowerCase()
                        .replace(/\s+/g, "-")}`}
                    >
                      <Icon
                        size={20}
                        strokeWidth={2.3}
                        className="text-white"
                      />
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="mt-auto border-t border-white/10 px-3 py-3">
        <button
          type="button"
          onClick={handleLogout}
          disabled={logoutLoading}
          className="flex w-full items-center gap-3 rounded-md py-2 pl-3 pr-3 text-[14px] font-medium text-white hover:bg-[var(--fulkro-chrome-hover-bg)] disabled:opacity-50"
          data-testid="cliente-nav-logout"
        >
          <LogOut size={18} strokeWidth={2.3} />
          <span>{logoutLoading ? "Saliendo…" : "Salir"}</span>
        </button>
      </div>
    </aside>
  );
}
