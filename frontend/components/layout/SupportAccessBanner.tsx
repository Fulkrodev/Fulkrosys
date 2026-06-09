"use client";

/**
 * Banner de acceso de soporte (impersonation READ-ONLY admin → portal cliente).
 *
 * Su ÚNICO trabajo: que el admin (Marcos) NO confunda una sesión de soporte con
 * el portal real del cliente. Visible SOLO cuando la sesión actual es de soporte
 * (claim support=true · expuesto por GET /client-portal/me · is_support_access).
 * Color distinto (ámbar) + fijo arriba + texto inequívoco. Funcional, no bonito.
 */
import { useQuery } from "@tanstack/react-query";

import { clientApi } from "@/lib/client-portal-api";

interface MeContext {
  is_support_access?: boolean;
  support_expires_at?: string | null;
}

export function SupportAccessBanner() {
  const { data } = useQuery<MeContext>({
    queryKey: ["client-portal", "me", "support-banner"],
    queryFn: () => clientApi<MeContext>("/client-portal/me"),
    staleTime: 60_000,
    retry: false,
  });

  if (!data?.is_support_access) return null;

  let caduca = "";
  if (data.support_expires_at) {
    const d = new Date(data.support_expires_at);
    if (!Number.isNaN(d.getTime())) {
      caduca = ` · caduca ${d.toLocaleTimeString("es-ES", {
        hour: "2-digit",
        minute: "2-digit",
      })}`;
    }
  }

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="support-access-banner"
      className="sticky top-0 z-50 w-full bg-amber-500 px-4 py-2 text-center text-sm font-bold text-black"
    >
      🛟 Sesión de soporte · Marcos — modo solo lectura{caduca}
    </div>
  );
}
