"use client";

/**
 * /admin/cross-project-compliance · LEGACY REDIRECT (sub-atom Sesión 3B-1 Phase B.2).
 *
 * Canonical path: /admin/compliance/projects (Option B consolidation).
 * Kept here for backward compat (existing bookmarks · email links · etc).
 *
 * Auto-redirect on mount + Link fallback si JS disabled.
 */
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

const CANONICAL_PATH = "/admin/compliance/projects";

export default function CrossProjectCompliancePageLegacy() {
  const router = useRouter();

  useEffect(() => {
    router.replace(CANONICAL_PATH);
  }, [router]);

  return (
    <div
      className="mx-auto flex max-w-md flex-col items-center gap-4 text-center"
      data-testid="cross-project-compliance-legacy-redirect"
    >
      <Loader2 className="h-6 w-6 animate-spin text-fulkro-primary-700" aria-hidden />
      <div>
        <p className="text-base font-medium text-fulkro-ink-700">
          Esta ruta ha cambiado.
        </p>
        <p className="mt-1 text-sm text-fulkro-ink-500">
          La vista de compliance multi-cliente ahora vive bajo el centro de
          cumplimiento.
        </p>
      </div>
      <Link
        href={CANONICAL_PATH}
        className="text-sm font-medium text-fulkro-info underline hover:opacity-80"
      >
        Continuar a la nueva ubicación
      </Link>
    </div>
  );
}
