"use client";

/**
 * PortalSwitcher — históricamente alternaba entre el portal de
 * consultoría (/admin) y otros portales de owner.
 *
 * Tras la retirada del subsistema ENS Radar, el owner solo dispone del
 * portal de consultoría (/admin), por lo que no hay un segundo portal al
 * que alternar. El componente se conserva como punto de extensión por si
 * en el futuro se añaden nuevos portales de owner, pero por ahora no
 * renderiza nada.
 *
 * Ver ADR-013 (separación de portales).
 */
export function PortalSwitcher() {
  return null;
}
