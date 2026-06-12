"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AuthGuard } from "@/components/auth/AuthGuard";
import { ClientHeader } from "@/components/layout/ClientHeader";
import { ClientSidebar } from "@/components/layout/ClientSidebar";
import { SupportAccessBanner } from "@/components/layout/SupportAccessBanner";
import { ClientFooter } from "@/components/client-portal/footer/ClientFooter";
import { CopilotoDock } from "@/components/copiloto/CopilotoDock";
import { CoachNextStepStrip } from "@/components/client-portal/coach/CoachNextStepStrip";
import { OnboardingTutorial } from "@/components/client-portal/tutorial/OnboardingTutorial";
import { useClientProjectId } from "@/hooks/useClientProjectId";
import { ClientBrandingProvider } from "@/lib/branding/ClientBrandingProvider";
import { ProjectFeaturesProvider } from "@/lib/contexts/ProjectFeaturesContext";

/**
 * Wrapper client-side del layout client-portal — detecta paths
 * públicos y renderiza chrome (Sidebar+Header) solo para rutas
 * autenticadas (FASE 10.A.fix audit Marcos).
 *
 * Patrón: server-layout delega aquí para mantener el export metadata
 * (que requiere server component) sin perder la capacidad de
 * conditional chrome basada en usePathname (que requiere client).
 *
 * AuthGuard requiredRole="client" gestiona:
 *   - whitelist PUBLIC_CLIENT_PATHS (login, forgot, reset) — render
 *     directo sin fetch /client-portal/me.
 *   - rutas autenticadas — fetch + redirect 401 a /client-portal/login.
 *
 * Defensa redundante con middleware: middleware ya filtra server-side.
 *
 * Ver CONSISTENCY-001 (chrome unificado), 10.A audit Marcos.
 */

const PUBLIC_CLIENT_PATHS = new Set<string>([
  "/client-portal/login",
  "/client-portal/forgot-password",
  "/client-portal/reset-password",
]);

export function ClientPortalChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_CLIENT_PATHS.has(pathname ?? "");

  if (isPublic) {
    // Login & paths públicos: layout limpio sin chrome.
    return (
      <AuthGuard requiredRole="client">
        <div className="min-h-dvh bg-fulkro-ink-50">{children}</div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard requiredRole="client">
      <ClientBrandingProvider>
        <ClientProjectFeaturesGate>
          <div className="flex h-dvh bg-fulkro-ink-50">
            <ClientSidebar className="hidden lg:flex" />
            <div className="flex min-w-0 flex-1 flex-col">
              <SupportAccessBanner />
              <ClientHeader />
              <main
                id="main-content"
                tabIndex={-1}
                className="flex-1 overflow-y-auto pb-16 md:pb-24 focus:outline-none"
              >
                {/* Ola C · el copiloto guía al cliente en TODAS las páginas */}
                <CoachStripMount />
                {children}
                <ClientFooter />
              </main>
            </div>
          </div>
          <CopilotoDock />
          <OnboardingTutorial />
        </ClientProjectFeaturesGate>
      </ClientBrandingProvider>
    </AuthGuard>
  );
}


/**
 * Mount `<ProjectFeaturesProvider>` resolviendo projectId vía
 * `useClientProjectId` (sub-atom 1.C.C.A · GAP-1 audit).
 *
 * Mientras projectId no resuelve, pasamos string vacío: el Provider
 * usa `enabled: Boolean(projectId)` → useQuery NO dispara fetch · data
 * stays undefined · `hasFeature(...) === false` · `<CategoryGate>` con
 * `feature=` renderiza fallback. Transient mínimo · UX aceptable.
 */
function ClientProjectFeaturesGate({ children }: { children: ReactNode }) {
  const { projectId } = useClientProjectId();
  return (
    <ProjectFeaturesProvider projectId={projectId ?? ""}>
      {children}
    </ProjectFeaturesProvider>
  );
}

/**
 * Ola C · monta la banda "tu siguiente paso" del copiloto en TODAS las páginas
 * autenticadas del cliente. Resuelve projectId vía `useClientProjectId` (dedupe
 * con el gate · misma query cacheada). El strip se auto-oculta (null) cuando no
 * hay acción pendiente, así que no satura las páginas.
 */
function CoachStripMount() {
  const { projectId } = useClientProjectId();
  return <CoachNextStepStrip projectId={projectId ?? null} />;
}
