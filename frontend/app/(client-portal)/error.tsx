"use client";

/**
 * Client-portal route group error boundary · Next.js 14 App Router convention.
 *
 * Sub-atom Sesión 3B-2B.2 Path B fix · OPS-052 16ª manifestación resolved.
 *
 * R29 firmísimo · cliente sin presión · friendly fallback con "Sin prisa".
 * NO técnico · NO jerga · NO admin lingo.
 */
import { useEffect } from "react";

export default function ClientPortalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[client-portal/error] segment crash", error);
  }, [error]);

  return (
    <div className="flex min-h-[50vh] items-center justify-center p-6">
      <div className="max-w-md space-y-4 rounded-xl bg-white p-6 text-center shadow-sm">
        <div className="text-4xl" aria-hidden>
          🌿
        </div>
        <h2 className="text-lg font-bold text-fulkro-primary-700">
          Hemos tenido un pequeño problema
        </h2>
        <p className="text-sm text-fulkro-ink-700">
          Algo no cargó bien. No te preocupes, tu información está a salvo. Puedes
          intentar de nuevo cuando quieras · sin prisa.
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="inline-flex items-center justify-center rounded-md bg-fulkro-primary-700 px-4 py-2 text-sm font-semibold text-white hover:bg-fulkro-primary-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700 focus-visible:ring-offset-2"
        >
          Intentar de nuevo
        </button>
        <p className="text-xs text-fulkro-ink-500">
          Si el problema persiste, Marcos te ayuda en cuanto pueda.
        </p>
      </div>
    </div>
  );
}
