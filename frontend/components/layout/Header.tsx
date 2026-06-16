"use client";

import { LogOut, Menu } from "lucide-react";
import * as React from "react";

import { AlertBell } from "@/components/alerts/AlertBell";
import { HeaderProjectChip } from "@/components/layout/HeaderProjectChip";
// Future: TODO-FE-DARK-MODE-COMPLETO-001 · ThemeToggle oculto hasta implementar
// dark mode completo (sub-fase dedicada). Tooltip "Próximamente" era visualmente
// confuso para chrome admin profesional. Componente y archivos se mantienen.
// import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Button } from "@/components/ui/button";
import { useLogout } from "@/hooks/useLogout";
import { useAuthStore } from "@/lib/stores/auth-store";
import { formatDay } from "@/lib/utils";

interface HeaderProps {
  onOpenMobileSidebar: () => void;
}

export function Header({ onOpenMobileSidebar }: HeaderProps) {
  const user = useAuthStore((s) => s.user);
  const { handleLogout, loading: logoutLoading } = useLogout("admin");
  const [now, setNow] = React.useState(() => new Date());

  React.useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <header
      style={{ background: "var(--fulkro-topbar-gradient)" }}
      className="flex h-16 items-center justify-between border-b border-white/10 px-4 text-white md:h-[72px] md:px-6"
    >
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobileSidebar}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md text-white hover:bg-white/10 lg:hidden"
          aria-label="Abrir menú lateral"
        >
          <Menu size={20} />
        </button>
        <div>
          <h2 className="text-base font-bold tracking-tight text-white md:text-lg">
            {user?.display_name ?? "FULKRO"}
          </h2>
          <p className="hidden text-sm font-medium text-white/80 sm:block">
            {formatDay(now)}
          </p>
        </div>
        <HeaderProjectChip />
      </div>

      <div className="flex items-center gap-3 text-white">
        {/* Future: TODO-FE-DARK-MODE-COMPLETO-001 · ThemeToggle oculto hasta
            implementar dark mode completo (sub-fase dedicada). Tooltip
            "Próximamente" era visualmente confuso para chrome admin profesional. */}
        {/* <ThemeToggle /> */}
        <AlertBell />
        <Button
          variant="ghost"
          size="md"
          onClick={handleLogout}
          disabled={logoutLoading}
          aria-label="Cerrar sesión"
          className="text-base font-semibold text-white hover:bg-white/10 hover:text-white"
        >
          <LogOut size={18} strokeWidth={2.2} />
          <span className="hidden sm:inline">Salir</span>
        </Button>
      </div>
    </header>
  );
}
