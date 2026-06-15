import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Contenedor de página canónico (§ estética audit-2026-06-15).
 *
 * Centra el contenido y fija UN ancho máximo + márgenes consistentes para todo el
 * producto, de modo que los shells de cada route-group dejen de resolver el
 * contenedor ad-hoc y las páginas NO inventen su propio `mx-auto max-w-X px-/py-`
 * (causa raíz de los márgenes inconsistentes detectada en la auditoría).
 *
 * variant:
 *   - "app"     max-w-6xl  → admin + portal cliente (por defecto)
 *   - "wide"    max-w-7xl  → páginas con tablas/datos densos
 *   - "reading" max-w-4xl  → prosa (legal, documentos)
 *   - "narrow"  max-w-2xl  → formularios cortos centrados
 */
const MAX_W = {
  app: "max-w-6xl",
  wide: "max-w-7xl",
  reading: "max-w-4xl",
  narrow: "max-w-2xl",
} as const;

export function PageContainer({
  children,
  variant = "app",
  className,
}: {
  children: React.ReactNode;
  variant?: keyof typeof MAX_W;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "mx-auto w-full px-4 py-6 md:px-6 md:py-8",
        MAX_W[variant],
        className,
      )}
    >
      {children}
    </div>
  );
}
