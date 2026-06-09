"use client";

import { TooltipENS } from "./tooltip-ens";
import { cn } from "@/lib/utils";
import type { GlossaryKey } from "@/lib/glosario-ens";

interface InfoTagProps {
  /** Key del glosario ENS · obligatorio si no se pasa `text`. */
  term?: GlossaryKey;
  /** Texto custom del tooltip · usado cuando no hay entry en glosario. */
  text?: string;
  /** Texto visible del tag · default = `term` si existe (obligatorio cuando solo se pasa `text`). */
  display?: string;
  className?: string;
}

/**
 * InfoTag · texto inline con tooltip integrado · pattern UX FULKRO.
 *
 * Indicador visual: underline dotted (standard "tiene info") + icono Info inline.
 * Coherente con paleta FULKRO (ink-300 dotted · primary-500/70 icono · primary-700 focus).
 *
 *   <p>Tu proyecto es <InfoTag term="categoria_alta" display="ALTA" /></p>
 *   <p><InfoTag text="Definición libre" display="Etiqueta visible" /></p>
 */
export function InfoTag({ term, text, display, className }: InfoTagProps) {
  return (
    <span
      className={cn(
        "underline decoration-dotted decoration-fulkro-ink-300 underline-offset-[3px]",
        className,
      )}
    >
      {display ?? term}{" "}
      <TooltipENS term={term} text={text} icon="info" iconSize={12} />
    </span>
  );
}
