"use client";

/**
 * ClientHeader — chrome cliente FASE 10.A.
 *
 * Hereda CONSISTENCY-001 (gradient horizontal var(--fulkro-topbar-gradient),
 * height 72px desktop / 64px mobile, padding-x matching admin) PERO
 * simplificado: SIN PortalSwitcher (cliente solo tiene un portal),
 * SIN bell notificaciones admin, SIN CommandPalette ⌘K, SIN dropdown
 * consultoría.
 *
 * Layout horizontal:
 *   - Izq: nombre cliente (de /client-portal/me) + email + fecha
 *   - Dcha: botón "Salir" (logout cliente)
 *
 * Logo NO aquí — vive en ClientSidebar arriba-izquierda. El header
 * es un "banner contextual" del estado del cliente.
 *
 * Datos: hace fetch /client-portal/me (existe en m21_portal_cliente,
 * devuelve ClientMeResponse con full_name + email + scope=rw post
 * MB-3 cleanup ADR-013 v3). Bounce a /login en 401 (defense in depth
 * — middleware ya filtró server-side).
 */

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { ClientMobileDrawer } from "@/components/layout/ClientMobileDrawer";
import { NotificationsBell } from "@/components/client-portal/header/NotificationsBell";
import { useLogout } from "@/hooks/useLogout";
import { clientApi, ClientApiError } from "@/lib/client-portal-api";
import { formatDay } from "@/lib/utils";

interface ClientMe {
  full_name: string;
  email: string;
  scope: string;
}

export function ClientHeader() {
  const router = useRouter();
  const { handleLogout, loading: logoutLoading } = useLogout("client");
  const [me, setMe] = React.useState<ClientMe | null>(null);
  const [now, setNow] = React.useState(() => new Date());

  React.useEffect(() => {
    let cancelled = false;
    clientApi<ClientMe>("/client-portal/me")
      .then((data) => {
        if (!cancelled) setMe(data);
      })
      .catch((err) => {
        if (cancelled) return;
        // 401 → bounce login (middleware ya redirigió en server, este es backup)
        if (err instanceof ClientApiError && err.status === 401) {
          router.replace("/client-portal/login");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  React.useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <header
      style={{ background: "var(--fulkro-topbar-gradient)" }}
      className="flex h-16 items-center justify-between border-b border-white/10 px-4 text-white md:h-[72px] md:px-6"
    >
      <div className="flex min-w-0 items-center gap-2">
        {/* Phase 4C · mobile drawer trigger lg:hidden (Sesión 3B-2B.8 CLUSTER 4) */}
        <ClientMobileDrawer />
        <div className="min-w-0">
          <h2 className="truncate text-base font-bold tracking-tight text-white md:text-lg">
            {me?.full_name ?? "Portal cliente"}
          </h2>
          <p className="hidden text-sm font-medium text-white/80 sm:block">
            {me?.email ? `${me.email} · ${formatDay(now)}` : formatDay(now)}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 text-white md:gap-3">
        <NotificationsBell />
        <Button
          variant="ghost"
          size="md"
          onClick={handleLogout}
          disabled={logoutLoading}
          aria-label="Cerrar sesión"
          className="text-base font-semibold text-white hover:bg-white/10 hover:text-white"
        >
          <LogOut size={18} strokeWidth={2.3} />
          <span className="hidden sm:inline">Salir</span>
        </Button>
      </div>
    </header>
  );
}
