"use client";

/**
 * Portal route group error boundary · pentester-portal · remediation · verify-auth.
 *
 * Sub-atom Sesión 3B-2B.2 Path B fix · OPS-052 16ª manifestación resolved.
 *
 * R29 cliente facing · friendly fallback.
 */
import { useEffect } from "react";

export default function PortalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[(portal)/error] segment crash", error);
  }, [error]);

  return (
    <div className="flex min-h-[50vh] items-center justify-center p-6">
      <div className="max-w-md space-y-4 rounded-xl bg-white p-6 text-center shadow-sm">
        <h2 className="text-lg font-bold text-fulkro-primary-700">
          Algo no cargó bien
        </h2>
        <p className="text-sm text-fulkro-ink-700">
          Puedes intentar de nuevo. Si el problema persiste, contacta con quien
          te haya compartido el enlace.
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="inline-flex items-center justify-center rounded-md bg-fulkro-primary-700 px-4 py-2 text-sm font-semibold text-white hover:bg-fulkro-primary-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700 focus-visible:ring-offset-2"
        >
          Intentar de nuevo
        </button>
      </div>
    </div>
  );
}
