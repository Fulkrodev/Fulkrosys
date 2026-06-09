"use client";

/**
 * RemediationCard · Cliente UI Bloque 3+5 v3.12.
 *
 * Card per remediation propuesta cliente · R29 firmísimo:
 *   - Título friendly (gap.title) · NO jerga técnica
 *   - Severity badge tone-aware (rojo crítico empático · NO alarmista)
 *   - Status badge friendly Spanish ("Pendiente de tu decisión" · "¡Hecho!" · etc)
 *   - suggested_action expandable plain Spanish
 *   - "Revisar y decidir" button cuando proposed_to_cliente
 *   - "Ver detalles" cuando otros estados
 *   - Last updated relative time friendly
 *
 * R29 sostained · cliente NUNCA presión coercitiva · NUNCA jerga ENS sin glossary.
 */
import { useState } from "react";
import { AlertCircle, CheckCircle2, Clock, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  REMEDIATION_STATUS_LABELS,
  REMEDIATION_STATUS_VARIANTS,
  SEVERITY_LABELS,
  SEVERITY_VARIANTS,
  type RemediationApprovalStatus,
  type RemediationGap,
  type RemediationSeverity,
} from "@/lib/api/client-cloud-remediations";

interface RemediationCardProps {
  gap: RemediationGap;
  onReview: (gap: RemediationGap) => void;
}

function formatRelativeDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("es-ES", {
      year: "numeric",
      month: "short",
      day: "2-digit",
    });
  } catch {
    return iso;
  }
}

function statusIcon(status: string) {
  if (status === "proposed_to_cliente") {
    return <Clock className="h-4 w-4 text-amber-600" />;
  }
  if (status === "executed") {
    return <CheckCircle2 className="h-4 w-4 text-emerald-700" />;
  }
  if (status === "failed") {
    return <AlertCircle className="h-4 w-4 text-rose-600" />;
  }
  return <ShieldCheck className="h-4 w-4 text-slate-500" />;
}

export function RemediationCard({ gap, onReview }: RemediationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const status = gap.approval_status as RemediationApprovalStatus;
  const statusLabel =
    REMEDIATION_STATUS_LABELS[status] ?? gap.approval_status;
  const statusVariant = REMEDIATION_STATUS_VARIANTS[status] ?? "outline";
  const severity = gap.severity as RemediationSeverity;
  const severityLabel = SEVERITY_LABELS[severity] ?? gap.severity;
  const severityVariant = SEVERITY_VARIANTS[severity] ?? "outline";

  const needsDecision = status === "proposed_to_cliente";
  const lastUpdated =
    gap.cliente_approval_at ??
    gap.proposed_to_cliente_at ??
    gap.resolved_at ??
    null;

  return (
    <Card
      data-testid="remediation-card"
      data-gap-id={gap.id}
      data-status={status}
      className={
        needsDecision ? "border-amber-300 shadow-sm" : ""
      }
    >
      <CardContent className="p-4 space-y-3">
        {/* Header · title + severity + status */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {statusIcon(status)}
              <h3 className="font-medium text-base leading-tight">
                {gap.title}
              </h3>
            </div>
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <Badge variant={severityVariant} data-testid="severity-badge">
                {severityLabel}
              </Badge>
              <Badge variant={statusVariant} data-testid="status-badge">
                {statusLabel}
              </Badge>
              <span className="text-muted-foreground">
                Actualizado · {formatRelativeDate(lastUpdated)}
              </span>
            </div>
          </div>
        </div>

        {/* Explicación amigable expandable */}
        {gap.explanation_es && (
          <div data-testid="explanation-section">
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="text-sm text-muted-foreground underline-offset-2 hover:underline"
              data-testid="explanation-toggle"
            >
              {expanded ? "Ocultar detalles" : "Ver detalles"}
            </button>
            {expanded && (
              <p
                className="text-sm text-foreground/80 mt-2 whitespace-pre-line"
                data-testid="explanation-content"
              >
                {gap.explanation_es}
              </p>
            )}
          </div>
        )}

        {/* Sugerencia accion (solo si pendiente decision) */}
        {needsDecision && gap.suggested_action && (
          <div
            className="bg-amber-50 border border-amber-200 rounded-md p-3 text-sm"
            data-testid="suggested-action"
          >
            <strong className="text-amber-900">Qué propone Marcos:</strong>{" "}
            <span className="text-amber-800">{gap.suggested_action}</span>
          </div>
        )}

        {/* Action button */}
        <div className="flex justify-end">
          {needsDecision ? (
            <Button
              onClick={() => onReview(gap)}
              data-testid="review-button"
              size="sm"
            >
              Revisar y decidir
            </Button>
          ) : (
            <span
              className="text-xs text-muted-foreground italic"
              data-testid="status-hint"
            >
              {status === "approved" || status === "executing"
                ? "Cuando esté listo te avisamos."
                : status === "executed"
                  ? "Sin más acciones necesarias."
                  : status === "failed"
                    ? "Marcos te contactará pronto."
                    : ""}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
