"use client";

import { usePathname, useRouter } from "next/navigation";
import * as React from "react";

import { api, ApiError } from "@/lib/api";
import { isAdminRole, isClientRole } from "@/lib/auth/roles";
import { ROUTES } from "@/lib/constants";
import { clientApi, ClientApiError } from "@/lib/client-portal-api";
import { useAuthStore } from "@/lib/stores/auth-store";
import type { MeResponse } from "@/lib/types";

/**
 * AuthGuard — protección client-side complementaria al middleware (3.C).
 *
 * Defensa en profundidad:
 *   1. Middleware Next.js bloquea server-side ANTES de cargar página
 *      (frontend/middleware.ts, ver ADR-013)
 *   2. AuthGuard valida client-side TRAS cargar página + hydra el
 *      auth-store con datos de /auth/me (admin/owner) o
 *      /client-portal/me (cliente) (este componente)
 *   3. Backend dependencies validan en cada API call
 *      (backend/app/auth/dependencies.py, commit fbcfdf4)
 *
 * Props:
 *   - requiredRole: "owner" | "client". Si set, valida que el role
 *     real coincida; si no, redirect al portal correcto.
 *   - fallback: skeleton custom durante el ready check.
 *
 * Polimorfismo (FASE 10.A):
 *   - requiredRole="owner": fetch /api/v1/auth/me (admin endpoint)
 *   - requiredRole="client": fetch /api/v1/client-portal/me + whitelist
 *     de paths públicos (login, forgot-password) bypass del check.
 *
 * Backward compat: defaults preservan el shape pre-FASE 10.A para que
 * (admin)/layout.tsx no requiera cambios.
 *
 * Ver ADR-013 (separación de portales), ADR-018 (regresión 3.C),
 * CONSISTENCY-001 (chrome cliente FASE 10.A).
 */

type RequiredRole = "owner" | "client";

/** Whitelist de paths públicos dentro de /client-portal/* — el
 * AuthGuard cliente los renderiza sin exigir sesión (matching el
 * middleware en frontend/middleware.ts). */
const PUBLIC_CLIENT_PATHS = new Set<string>([
  "/client-portal/login",
  "/client-portal/forgot-password",
  "/client-portal/reset-password",
]);

interface ClientMe {
  full_name: string;
  email: string;
  role: string;
}

interface AuthGuardProps {
  children: React.ReactNode;
  requiredRole?: RequiredRole;
  fallback?: React.ReactNode;
}

export function AuthGuard({
  children,
  requiredRole,
  fallback,
}: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const ready = useAuthStore((s) => s.ready);
  const setUser = useAuthStore((s) => s.setUser);
  const setReady = useAuthStore((s) => s.setReady);
  const setCsrf = useAuthStore((s) => s.setCsrf);

  // Local state para client mode (no contamina auth-store que es
  // owner-shaped). El user del store se setea solo en owner mode.
  const [clientMe, setClientMe] = React.useState<ClientMe | null>(null);
  const [clientReady, setClientReady] = React.useState(false);
  // §2.7 · error de auth NO-401 (500/red) → mostrar aviso + reintento (antes
  // se quedaba en pantalla en blanco renderizando null).
  const [authError, setAuthError] = React.useState(false);
  const [retryNonce, setRetryNonce] = React.useState(0);

  const isClientMode = requiredRole === "client";
  const isPublicClientPath =
    isClientMode && PUBLIC_CLIENT_PATHS.has(pathname);

  React.useEffect(() => {
    let cancelled = false;

    async function checkOwner() {
      try {
        const me = await api<MeResponse>("/api/v1/auth/me");
        if (cancelled) return;
        setUser(me);
        setAuthError(false);
        if (typeof document !== "undefined") {
          const match = document.cookie.match(/(?:^|;\s*)fulkro_csrf=([^;]+)/);
          if (match) setCsrf(decodeURIComponent(match[1]));
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          setUser(null);
          setCsrf(null);
          router.replace(ROUTES.login);
        } else {
          // §2.7 · error NO-401 (500/red): no quedarse en blanco · mostrar aviso.
          setAuthError(true);
        }
      } finally {
        if (!cancelled) setReady(true);
      }
    }

    async function checkClient() {
      try {
        const me = await clientApi<ClientMe>("/client-portal/me");
        if (cancelled) return;
        setClientMe(me);
        setAuthError(false);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ClientApiError && err.status === 401) {
          setClientMe(null);
          router.replace("/client-portal/login");
        } else {
          setAuthError(true);
        }
      } finally {
        if (!cancelled) setClientReady(true);
      }
    }

    if (isClientMode) {
      // Public path (login etc.): no fetch, render directo
      if (isPublicClientPath) {
        setClientReady(true);
      } else {
        void checkClient();
      }
    } else {
      void checkOwner();
    }
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, isClientMode, isPublicClientPath, retryNonce]);

  const retryAuth = React.useCallback(() => {
    setAuthError(false);
    setReady(false);
    setClientReady(false);
    setRetryNonce((n) => n + 1);
  }, [setReady]);

  // Role check (solo owner mode)
  React.useEffect(() => {
    if (isClientMode) return;
    if (!ready || !user) return;

    if (requiredRole === "owner" && user.role !== "owner") {
      if (isAdminRole(user.role)) {
        router.replace("/admin/dashboard");
      } else if (isClientRole(user.role)) {
        router.replace("/client-portal/dashboard");
      } else {
        router.replace(ROUTES.login);
      }
    }
  }, [
    ready,
    user,
    requiredRole,
    router,
    isClientMode,
  ]);

  // ─── Client mode rendering ───
  if (isClientMode) {
    // Public path: render hijos sin auth check
    if (isPublicClientPath) {
      return <>{children}</>;
    }
    if (!clientReady) {
      return (
        fallback ?? (
          <div className="flex min-h-dvh items-center justify-center bg-fulkro-ink-50">
            <div className="animate-pulse text-sm text-fulkro-ink-500">
              Cargando portal cliente…
            </div>
          </div>
        )
      );
    }
    if (authError) {
      return <AuthErrorCard onRetry={retryAuth} />;  // §2.7
    }
    if (!clientMe) {
      // 401 ya disparó redirect; null evita flash de contenido
      return null;
    }
    return <>{children}</>;
  }

  // ─── Owner mode rendering (path original, backward-compat) ───
  if (!ready) {
    return (
      fallback ?? (
        <div className="flex min-h-dvh items-center justify-center bg-fulkro-ink-50">
          <div className="animate-pulse text-sm text-fulkro-ink-500">
            Cargando FULKRO…
          </div>
        </div>
      )
    );
  }

  if (authError) {
    return <AuthErrorCard onRetry={retryAuth} />;  // §2.7
  }

  if (!user) {
    return null;
  }

  if (requiredRole === "owner" && user.role !== "owner") {
    return null;
  }

  return <>{children}</>;
}

/** §2.7 · aviso (no pantalla en blanco) cuando /me falla por 500/red. */
function AuthErrorCard({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-fulkro-ink-50 p-6">
      <div className="max-w-sm space-y-3 rounded-lg border border-fulkro-ink-200 bg-white p-6 text-center">
        <p className="text-sm font-medium text-fulkro-ink-700">
          No pudimos verificar tu sesión
        </p>
        <p className="text-xs text-fulkro-ink-500">
          Ha habido un problema temporal de conexión con el servidor. Inténtalo
          de nuevo.
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md bg-fulkro-primary-700 px-4 py-2 text-sm font-medium text-white hover:bg-fulkro-primary-800"
        >
          Reintentar
        </button>
      </div>
    </div>
  );
}
