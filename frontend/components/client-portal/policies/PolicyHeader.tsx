"use client";

/**
 * Policy header · tier summary + progress bar · SAN-E v3.MB-6 atom 1.
 */
import { ShieldCheck } from "lucide-react";

import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { type PolicySummary } from "@/lib/api/policies";

interface Props {
  summary: PolicySummary;
}

export function PolicyHeader({ summary }: Props) {
  // §2.7: guarda división por cero → 0% en vez de NaN%.
  const percent = summary.expected_count > 0
    ? Math.round((summary.revisada_ok_count / summary.expected_count) * 100)
    : 0;

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2 text-fulkro-primary-700">
            <ShieldCheck className="h-4 w-4" aria-hidden />
            <span className="text-xs uppercase tracking-wide font-semibold">
              CCN-STIC 805 · Tier {summary.tier}
            </span>
          </div>
          <div className="mt-1 text-sm text-fulkro-ink-700 font-semibold">
            {summary.revisada_ok_count} de {summary.expected_count} políticas
            revisadas
          </div>
          <div className="text-xs text-fulkro-ink-500 mt-0.5">
            {summary.with_questions_count > 0
              ? `${summary.with_questions_count} con pregunta · `
              : ""}
            {summary.suggest_change_count > 0
              ? `${summary.suggest_change_count} con cambio sugerido · `
              : ""}
            {summary.pending_review_count} pendientes de revisar
          </div>
        </div>
        <div className="text-2xl font-bold text-fulkro-primary-700 font-mono tabular-nums flex-shrink-0">
          {percent}%
        </div>
      </div>
      <Progress value={percent} className="h-2" />
    </Card>
  );
}
