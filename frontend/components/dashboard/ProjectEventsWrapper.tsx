"use client";

/**
 * ProjectEventsWrapper · client component SSE-aware (MB-13.3 · ADR-035).
 *
 * Envuelve el server component home admin proyecto y conecta el hook
 * ``useProjectEvents`` para que cualquier cambio backend (readiness /
 * phase / alert) invalide queries TanStack y refresque UI sin F5.
 *
 * Pattern: page.tsx (server component) renderiza este wrapper como
 * primer hijo · resto del árbol queda dentro · invalidations
 * cross-children porque el queryClient es shared globalmente.
 */
import { useProjectEvents } from "@/lib/admin-dashboard/useProjectEvents";

interface Props {
  projectId: string;
  children: React.ReactNode;
}

export function ProjectEventsWrapper({ projectId, children }: Props) {
  useProjectEvents({ projectId });
  return <>{children}</>;
}
