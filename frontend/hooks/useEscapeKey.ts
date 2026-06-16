"use client";

import { useEffect } from "react";

/**
 * Cierra un modal/overlay ad-hoc al pulsar `Escape` · a11y WCAG 2.1.2.
 *
 * Pensado para los modales caseros (no construidos sobre el primitivo
 * `@/components/ui/dialog`, que ya atrapa el foco y cierra con ESC vía Radix).
 * Sólo añade el listener de teclado · NO altera el layout ni el foco (el
 * focus-trap completo de los modales ad-hoc se aborda en el pase global de UX).
 *
 * @param onEscape callback de cierre (típicamente el `onClose` del modal).
 * @param enabled  desactiva el listener cuando el modal no está abierto.
 */
export function useEscapeKey(onEscape: () => void, enabled = true): void {
  useEffect(() => {
    if (!enabled) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onEscape();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onEscape, enabled]);
}
