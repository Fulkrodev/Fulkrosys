"use client";

/**
 * ClientNextActionCard · "Tu siguiente acción" prominent CTA (1.D.G.E v3.11).
 *
 * Top priority step actor=cliente status=available · CTA destacado.
 * R29 sostener · friendly · NO coercitive presión.
 *
 * Renderiza nada si NO hay step disponible cliente · dashboard mantiene fallback existing.
 */
import * as React from "react";
import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

import type { EnrichedStepState } from "@/lib/api/client-workflow-guide";

export interface ClientNextActionCardProps {
  step: EnrichedStepState | null;
}

export function ClientNextActionCard({ step }: ClientNextActionCardProps) {
  if (!step) return null;

  // Sólo render si actor cliente + status available/in_progress
  const actor = step.primary_actor ?? "admin";
  const depStatus = step.dependency_status ?? step.status;
  const isClienteActionable =
    actor === "cliente" &&
    (depStatus === "available" || depStatus === "in_progress");

  if (!isClienteActionable) return null;

  return (
    <Card
      className="border-l-4 border-l-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/20"
      data-testid="client-next-action-card"
    >
      <CardContent className="py-5 px-5 space-y-3">
        <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
          <Sparkles className="size-4" />
          <span className="text-xs font-semibold uppercase tracking-wide">
            Tu siguiente acción
          </span>
        </div>

        <h2
          className="text-lg font-bold leading-snug"
          data-testid="next-action-title"
        >
          {step.title}
        </h2>

        {step.description_detailed_es && (
          <p className="text-sm text-foreground/75 leading-relaxed">
            {step.description_detailed_es}
          </p>
        )}

        {step.estimated_days && (
          <Badge variant="outline" className="text-xs">
            ~{step.estimated_days} día{step.estimated_days === 1 ? "" : "s"}{" "}
            estimado
          </Badge>
        )}

        {step.cta_url && (
          <div className="pt-1">
            <Link
              href={step.cta_url}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-6 py-3 text-base font-semibold text-primary-foreground transition hover:opacity-90"
              data-testid="next-action-cta"
            >
              {step.cta_label ?? "Empezar ahora"}
              <ArrowRight className="size-4" />
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
