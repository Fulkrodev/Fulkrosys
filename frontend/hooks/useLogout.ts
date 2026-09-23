"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { useAuthStore } from "@/lib/stores/auth-store";
import { csrfHeaders } from "@/lib/csrf";

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
    // Las dos rutas van bajo /api/v1: next.config solo reenvia /api/* al
    // backend, y "/client-auth/logout" (sin prefijo) daba 404 en Next sin
    // llegar nunca al servidor.
    const endpoint =
      portal === "admin" ? "/api/v1/auth/logout" : "/api/v1/client-auth/logout";
    const redirect = portal === "admin" ? "/login" : "/client-portal/login";

    try {
      // POST que escribe → exige X-CSRF-Token (auth/csrf.py). Sin el, 403, y
      // `fetch` no lanza con un 403: la sesion seguia viva en el servidor y la
      // cookie httpOnly (que JS no puede borrar) seguia en el navegador.
      const res = await fetch(endpoint, {
        method: "POST",
        credentials: "include",
        headers: csrfHeaders(),
      });
      if (!res.ok) {
        throw new Error(`logout HTTP ${res.status}`);
      }
      if (portal === "admin") {
        toast.success("Sesión cerrada");
      }
    } catch (error) {
      console.error(`[useLogout:${portal}] server logout failed:`, error);
      if (portal === "admin") {
        toast.error(
          "No se pudo cerrar la sesión en el servidor. Cierra el navegador si el equipo es compartido.",
        );
      }
    } finally {
      logoutStore();
      setLoading(false);
      router.push(redirect);
    }
  }, [portal, router, logoutStore]);

  return { handleLogout, loading };
}
