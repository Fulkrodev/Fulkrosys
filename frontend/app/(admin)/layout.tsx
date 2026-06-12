"use client";

import { X } from "lucide-react";
import * as React from "react";
import { usePathname } from "next/navigation";

import { AuthGuard } from "@/components/auth/AuthGuard";
import { OnboardingTourAdmin } from "@/components/admin/copilot/OnboardingTourAdmin";
import { CopilotNextStepBanner } from "@/components/copilot/CopilotNextStepBanner";
import { CopilotPanel } from "@/components/copilot/CopilotPanel";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/button";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [paletteOpen, setPaletteOpen] = React.useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = React.useState(false);
  const pathname = usePathname();

  React.useEffect(() => {
    setMobileSidebarOpen(false);
  }, [pathname]);

  React.useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setMobileSidebarOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <AuthGuard requiredRole="owner">
      <a href="#main-content" className="skip-link">
        Saltar al contenido
      </a>
      {/*
        Sub-atom Sesión 3B-2B.2 Path A.0 re-run · architectural fix sidebar full-height.
        Outer wrapper bg-[#0a1a5c] matches Sidebar's solid bg-color so any pixel-level
        gap between sidebar and viewport edge (sticky + flex + dvh edge cases) is
        invisible (same color). Main content column carries bg-fulkro-ink-50 instead.
        Marcos report: "después de Churn risk · background DEJA de ser dark navy ·
        cambia a BLANCO" → root cause was parent bg-fulkro-ink-50 showing through.
      */}
      <div className="flex h-dvh bg-[#0a1a5c]">
        <Sidebar
          className="hidden lg:flex"
          onOpenCommandPalette={() => setPaletteOpen(true)}
        />

        {mobileSidebarOpen && (
          <div className="fixed inset-0 z-50 flex lg:hidden" role="dialog" aria-modal="true">
            <button
              type="button"
              aria-label="Cerrar menú lateral"
              className="flex-1 bg-fulkro-ink-900/50"
              onClick={() => setMobileSidebarOpen(false)}
            />
            <div className="relative flex">
              <Sidebar
                onOpenCommandPalette={() => {
                  setMobileSidebarOpen(false);
                  setPaletteOpen(true);
                }}
                onNavigate={() => setMobileSidebarOpen(false)}
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => setMobileSidebarOpen(false)}
                aria-label="Cerrar menú lateral"
                className="absolute -right-9 top-3 h-9 w-9"
              >
                <X size={16} />
              </Button>
            </div>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col bg-fulkro-ink-50">
          <Header onOpenMobileSidebar={() => setMobileSidebarOpen(true)} />
          <CopilotNextStepBanner />
          <main
            id="main-content"
            tabIndex={-1}
            className="flex-1 overflow-y-auto p-4 pb-16 md:p-6 md:pb-24"
          >
            {children}
          </main>
        </div>
        <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
        <CopilotPanel />
        {/* Sub-atom Sesión 3A Phase B.4 · primer admin login welcome tour */}
        <OnboardingTourAdmin />
      </div>
    </AuthGuard>
  );
}
