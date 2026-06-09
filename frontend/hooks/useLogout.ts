"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { useAuthStore } from "@/lib/stores/auth-store";

type Portal = "admin" | "client";

interface UseLogoutResult {
  handleLogout: () => Promise<void>;
  loading: boolean;
}

/**
 * SAN-E v3.MB-1.3 · ADR-046 v3 · centralized logout logic.
 *
 * Cada layout (Header admin · ClientHeader · ClientSidebar)
 * mantiene su markup chrome-specific intacto · este hook centraliza:
 *   - fetch endpoint correcto per portal (admin vs client)
 *   - clear auth store local (useAuthStore.logout)
 *   - redirect a login correspondiente
 *   - toast condicional: admin sí (toast.success/error sonner) ·
 *     client silent intencional (cookies clear server-side · ver
 *     comments ClientHeader/ClientSidebar pre-1.3)
 *
 * Patrón: hook = lógica · componente = presentación.
 * Cada callsite pasa onClick={handleLogout} disabled={loading} y
 * conserva su markup (size icon · strokeWidth · classes · Button vs
 * native button · label sm:inline vs always).
 */
export function useLogout(portal: Portal): UseLogoutResult {
  const router = useRouter();
  const logoutStore = useAuthStore((s) => s.logout);
  const [loading, setLoading] = useState(false);

  const handleLogout = useCallback(async () => {
    setLoading(true);
    const endpoint =
      portal === "admin" ? "/api/v1/auth/logout" : "/client-auth/logout";
    const redirect = portal === "admin" ? "/login" : "/client-portal/login";

    try {
      await fetch(endpoint, {
        method: "POST",
        credentials: "include",
      });
      if (portal === "admin") {
        toast.success("Sesión cerrada");
      }
    } catch (error) {
      console.error(`[useLogout:${portal}] server logout failed:`, error);
      if (portal === "admin") {
        toast.error("Error al cerrar sesión · sesión limpiada localmente");
      }
      // client portal: silent intencional · cookies clear server-side
      // y middleware /client-portal/* sigue protegiendo rutas.
    } finally {
      logoutStore();
      setLoading(false);
      router.push(redirect);
    }
  }, [portal, router, logoutStore]);

  return { handleLogout, loading };
}
