/**
 * AdaptationBadge · materializa R28 visualmente · sub-atom 1.C.D.B.2 v3.8.
 *
 * Click popover explica per-dim per qué este sub-paso aplica al proyecto.
 * Zero componente decorativo · materializa empíricamente las 19 dims.
 */
"use client";

import { Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

import type {
  EnrichedStepState,
  ProjectDimsLike,
} from "@/lib/api/workflow-command-center";

interface AdaptationBadgeProps {
  step: EnrichedStepState;
  dims: ProjectDimsLike;
}

export function AdaptationBadge({ step, dims }: AdaptationBadgeProps) {
  const reasons = buildReasons(step, dims);

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/50 px-2 py-0.5 text-[11px] font-medium text-foreground/80 hover:bg-muted transition-colors"
          aria-label="Por qué este paso aplica al proyecto"
        >
          <Info className="size-3" />
          <span>🎯 {summarize(step)}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent side="bottom" align="start" className="w-80 text-sm">
        <div className="space-y-2">
          <p className="font-semibold">
            Este paso aplica porque:
          </p>
          {reasons.length > 0 ? (
            <ul className="space-y-1 text-xs text-foreground/80">
              {reasons.map((r, idx) => (
                <li key={idx} className="flex gap-2">
                  <span className="text-emerald-600">✓</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-foreground/60 italic">
              Aplicable a todos los proyectos (sin restricciones específicas)
            </p>
          )}
          {step.variant_extra_focus && (
            <div className="border-t pt-2 mt-2">
              <p className="text-xs font-medium">
                🔵 Variante arquetipo aplicada:
              </p>
              <p className="text-xs text-foreground/80 italic">
                {step.variant_extra_focus}
              </p>
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

function summarize(step: EnrichedStepState): string {
  const parts: string[] = [];
  if (step.variant_extra_focus) parts.push("variant aplicada");
  if (step.actors.length > 0) parts.push(`${step.actors.length} actores`);
  if (step.is_enriched) parts.push("enriched");
  return parts.length > 0 ? parts.join(" · ") : "ver detalle";
}

function buildReasons(
  step: EnrichedStepState,
  dims: ProjectDimsLike,
): string[] {
  const reasons: string[] = [];

  // Categoría
  if (dims.categoria_objetivo) {
    reasons.push(
      `Categoría ${dims.categoria_objetivo} (aplica al sub-paso)`,
    );
  }

  // Archetype
  if (dims.archetype) {
    if (step.variant_extra_focus) {
      reasons.push(
        `Arquetipo ${dims.archetype} → variant específica aplicada`,
      );
    } else {
      reasons.push(`Arquetipo ${dims.archetype}`);
    }
  }

  // Tamaño empleados
  if (dims.tamano_empleados) {
    reasons.push(`Tamaño ${dims.tamano_empleados}`);
  }

  // Madurez
  if (dims.madurez_ens_actual && dims.madurez_ens_actual !== "L0") {
    reasons.push(`Madurez ENS ${dims.madurez_ens_actual}`);
  }

  // Legal requirements explícitos (si step tiene tooltips_ens · suelen mencionar)
  if (Object.keys(step.tooltips_ens).length > 0) {
    reasons.push(
      `Referencias ENS: ${Object.keys(step.tooltips_ens).join(" · ")}`,
    );
  }

  // DPO si aplica
  if (dims.dpo_designado && dims.dpo_designado !== "no_designado") {
    reasons.push(`DPO ${dims.dpo_designado}`);
  }

  // Legales flags
  if (dims.aplica_dora && dims.aplica_dora !== "no") {
    reasons.push(`DORA: ${dims.aplica_dora}`);
  }
  if (dims.aplica_nis2 && dims.aplica_nis2 !== "no") {
    reasons.push(`NIS2: ${dims.aplica_nis2}`);
  }
  if (dims.aplica_ai_act && dims.aplica_ai_act !== "no") {
    reasons.push(`AI Act: ${dims.aplica_ai_act}`);
  }
  if (dims.procesa_datos_sensibles_rgpd9) {
    reasons.push("Procesa datos sensibles RGPD art.9");
  }

  return reasons;
}
