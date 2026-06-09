"use client";

import { useSearchParams } from "next/navigation";

/**
 * Renderiza una anotación técnica de desarrollo (e.g.
 * "mocks · GET /api/.. pendiente en backend") que NO se muestra al
 * usuario por defecto.
 *
 * Visible sólo si:
 *   - URL incluye `?dev=true`
 *   - O variable env `NEXT_PUBLIC_SHOW_DEVHINTS=true` está activa al build
 *
 * Garantiza demos limpias sin filtrar contexto técnico al cliente.
 *
 * Uso:
 *   <DevHint>mocks · GET /api/v1/dashboard/* pendiente en backend</DevHint>
 */
export function DevHint({ children }: { children: React.ReactNode }) {
  const searchParams = useSearchParams();
  const explicitShow =
    searchParams?.get("dev") === "true" ||
    process.env.NEXT_PUBLIC_SHOW_DEVHINTS === "true";

  if (!explicitShow) return null;

  return (
    <span className="ml-2 inline-block font-mono text-xs text-fulkro-ink-300">
      {children}
    </span>
  );
}
