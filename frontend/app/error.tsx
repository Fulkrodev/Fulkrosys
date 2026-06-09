"use client";

/**
 * Root error boundary · Next.js 14 App Router convention.
 *
 * Sub-atom Sesión 3B-2B.2 Path B fix · OPS-052 16ª manifestación resolved.
 *
 * Handles errors thrown in any segment WITHIN the root layout (root layout
 * itself preserved · vs global-error.tsx that replaces root layout).
 *
 * R30 admin tutor + R29 cliente sin presión · friendly fallback con reset CTA.
 */
import { AlertTriangle, Home, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[app/error] segment crash", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <div className="max-w-lg space-y-4 rounded-xl border border-fulkro-ink-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle
            className="mt-0.5 h-5 w-5 shrink-0 text-fulkro-warning"
            aria-hidden
          />
          <div>
            <h1 className="text-lg font-bold text-fulkro-primary-700">
              Algo no funcionó como esperábamos
            </h1>
            <p className="mt-1 text-sm text-fulkro-ink-700">
              Hubo un error al cargar esta sección. Puedes reintentar o volver al
              inicio.
            </p>
          </div>
        </div>

        {error.digest ? (
          <p className="font-mono text-xs text-fulkro-ink-500">
            Reference: <code>{error.digest}</code>
          </p>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => reset()}
            className="inline-flex items-center gap-1.5 rounded-md bg-fulkro-primary-700 px-4 py-2 text-sm font-semibold text-white hover:bg-fulkro-primary-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700 focus-visible:ring-offset-2"
            data-testid="root-error-retry"
          >
            <RefreshCw className="h-4 w-4" />
            Reintentar
          </button>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-md border border-fulkro-ink-300 bg-white px-4 py-2 text-sm font-semibold text-fulkro-primary-700 hover:bg-fulkro-ink-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-info focus-visible:ring-offset-2"
          >
            <Home className="h-4 w-4" />
            Ir al inicio
          </Link>
        </div>
      </div>
    </div>
  );
}
