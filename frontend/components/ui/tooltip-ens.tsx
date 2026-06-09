"use client";

import * as React from "react";
import { HelpCircle, Info } from "lucide-react";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { GLOSARIO_ENS, type GlossaryEntry, type GlossaryKey } from "@/lib/glosario-ens";
import { cn } from "@/lib/utils";

interface TooltipENSProps {
  term?: GlossaryKey;
  text?: string;
  icon?: "help" | "info";
  side?: "top" | "right" | "bottom" | "left";
  children?: React.ReactNode;
  iconSize?: number;
  className?: string;
}

/**
 * TooltipENS · tooltip estándar FULKRO con catálogo glosario ENS integrado.
 *
 * ── Pattern guide (Sprint 1 P2) ──
 *
 * Texto en prosa que necesita tooltip → usa <InfoTag> (mejor UX · underline
 * dotted + icono inline indican claramente que hay info disponible).
 *     <InfoTag term="MAGERIT" display="MAGERIT" />
 *
 * Wrap de Button/Badge/Card → usa TooltipENS sin icono extra (el componente
 * envuelto ya tiene affordance visual propio · no añadas chrome encima).
 *     <TooltipENS term="PILAR"><Badge>PILAR-compat</Badge></TooltipENS>
 *
 * Solo icono ? estándalone → TooltipENS self-closing (icono visible auto).
 *     <TooltipENS term="MAGERIT" />
 *     <TooltipENS text="Acción irreversible" />
 *
 * Mobile: tooltip se muestra on tap (no hover) · close on outside tap.
 */
export function TooltipENS({
  term,
  text,
  icon = "help",
  side = "top",
  children,
  iconSize = 16,
  className,
}: TooltipENSProps) {
  const entry: GlossaryEntry | null = term
    ? ((GLOSARIO_ENS as Record<string, GlossaryEntry>)[term] ?? null)
    : null;
  const content = text ?? entry?.definition ?? null;
  const docLink = entry?.docLink ?? null;
  const ariaLabel = entry?.label ?? "Información adicional";

  if (!content) return children ? <>{children}</> : null;

  const Icon = icon === "info" ? Info : HelpCircle;

  const trigger = children ?? (
    <button
      type="button"
      aria-label={`Ayuda: ${ariaLabel}`}
      className={cn(
        "inline-flex items-center justify-center rounded-full",
        // Sprint 1 P2 · purple tenue → más signal · menos ruido visual gris.
        "text-fulkro-primary-500/70 hover:text-fulkro-primary-700 transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700 focus-visible:ring-offset-2 focus-visible:ring-offset-fulkro-ink-50",
        "min-w-[24px] min-h-[24px]",
        className,
      )}
    >
      <Icon size={iconSize} aria-hidden />
    </button>
  );

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>{trigger}</TooltipTrigger>
        <TooltipContent
          side={side}
          className="max-w-xs text-sm leading-relaxed"
        >
          <div>{content}</div>
          {docLink && (
            <a
              href={docLink}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 block text-xs text-fulkro-info hover:underline underline-offset-2"
            >
              Más información →
            </a>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
