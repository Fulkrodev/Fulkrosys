"use client";

/**
 * RiskRow · row análisis riesgo MAGERIT en lista cliente review.
 *
 * Sub-atom 5.4.B · cliente revisa riesgos (MageritThreatAssessment).
 * Inline expand RICHER (pattern atom 5.3.E) · 6 sections.
 *
 * Q5.3: cliente NO edita probability/degradación · admin owns · solo review.
 */
import { useState } from "react";

import type {
  AssetReviewAction,
  MageritRiskClientView,
  MageritSeverity,
} from "@/lib/api/magerit";


const PROBABILITY_LABELS: Record<string, string> = {
  MB: "Muy baja",
  B: "Baja",
  M: "Media",
  A: "Alta",
  MA: "Muy alta",
};


const SEVERITY_STYLES: Record<MageritSeverity, { label: string; cls: string }> = {
  baja: {
    label: "Baja",
    cls: "bg-fulkro-success/15 text-fulkro-success border-fulkro-success/30",
  },
  media: {
    label: "Media",
    cls: "bg-fulkro-warning/15 text-fulkro-warning border-fulkro-warning/30",
  },
  alta: {
    label: "Alta",
    cls: "bg-fulkro-danger/15 text-fulkro-danger border-fulkro-danger/30",
  },
  critica: {
    label: "Critica",
    cls: "bg-fulkro-danger/30 text-fulkro-danger border-fulkro-danger/60",
  },
};


const REVIEW_STATUS_LABELS: Record<string, { label: string; cls: string }> = {
  revisada_ok: {
    label: "Revisada",
    cls: "bg-fulkro-success/15 text-fulkro-success border-fulkro-success/30",
  },
  con_pregunta: {
    label: "Pregunta",
    cls: "bg-fulkro-warning/15 text-fulkro-warning border-fulkro-warning/30",
  },
  suggest_change: {
    label: "Sugerencia",
    cls: "bg-fulkro-info/15 text-fulkro-info border-fulkro-info/30",
  },
};


interface Props {
  risk: MageritRiskClientView;
  onReview: (
    riskId: string,
    action: AssetReviewAction,
    note?: string,
  ) => Promise<void>;
}


function DegradationChip({
  letter,
  label,
  value,
  affected,
}: {
  letter: string;
  label: string;
  value: number | null;
  affected: boolean;
}) {
  const hasValue = value !== null && value > 0;
  return (
    <div
      className={`rounded border px-2 py-1.5 ${
        affected ? "bg-fulkro-warning/5 border-fulkro-warning/30" : "bg-card"
      }`.trim()}
    >
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-sm font-bold">{letter}</span>
        <span
          className={`text-xs tabular-nums ${
            hasValue ? "font-semibold" : "text-[color:var(--fulkro-muted)]"
          }`.trim()}
        >
          {hasValue ? `${value}%` : "—"}
        </span>
      </div>
      <div className="text-[9px] uppercase tracking-wide text-[color:var(--fulkro-muted)]">
        {label}
      </div>
    </div>
  );
}


export function RiskRow({ risk, onReview }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [pendingAction, setPendingAction] =
    useState<AssetReviewAction | null>(null);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const severity = SEVERITY_STYLES[risk.severity];
  const reviewStatus = risk.client_review_status
    ? REVIEW_STATUS_LABELS[risk.client_review_status]
    : null;
  const affectedDims = new Set(risk.affected_dimensions ?? []);

  const handleAction = async (action: AssetReviewAction) => {
    if (action === "revisada_ok") {
      setSubmitting(true);
      try {
        await onReview(risk.id, action);
      } finally {
        setSubmitting(false);
      }
      return;
    }
    setPendingAction(action);
    setNote(risk.client_review_note ?? "");
  };

  const submitWithNote = async () => {
    if (!pendingAction) return;
    if (note.trim().length < 5) return;
    setSubmitting(true);
    try {
      await onReview(risk.id, pendingAction, note);
      setPendingAction(null);
      setNote("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <li className="rounded-md border bg-card p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded bg-fulkro-ink-100 px-1.5 py-0.5 font-mono text-xs text-[color:var(--fulkro-muted)]">
              {risk.asset_code}
            </span>
            <span className="text-xs text-[color:var(--fulkro-muted)]">×</span>
            <span className="rounded bg-fulkro-ink-100 px-1.5 py-0.5 font-mono text-xs text-[color:var(--fulkro-muted)]">
              {risk.threat_code}
            </span>
            <span
              className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${severity.cls}`.trim()}
            >
              {severity.label}
            </span>
            {reviewStatus && (
              <span
                className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${reviewStatus.cls}`.trim()}
              >
                {reviewStatus.label}
              </span>
            )}
          </div>
          <h3 className="mt-1 text-sm font-medium leading-snug">
            {risk.threat_name}
            <span className="ml-2 text-[color:var(--fulkro-muted)]">
              sobre {risk.asset_name}
            </span>
          </h3>
        </div>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-xs font-medium text-fulkro-primary-700 underline-offset-2 hover:underline"
        >
          {expanded ? "Ocultar detalle" : "Ver detalle"}
        </button>
      </div>

      {expanded && (
        <div className="mt-4 space-y-5 border-t pt-4 text-sm">
          {/* Section 1 · Threat description */}
          {risk.threat_description && (
            <section>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
                Amenaza · grupo {risk.threat_group_code}
              </h4>
              <p className="leading-relaxed text-[color:var(--fulkro-title)]">
                {risk.threat_description}
              </p>
            </section>
          )}

          {/* Section 2 · Análisis MAGERIT cuantitativo */}
          <section>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
              Análisis MAGERIT
            </h4>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <InfoBox
                label="Probabilidad"
                value={
                  PROBABILITY_LABELS[risk.probability] ?? risk.probability
                }
                code={risk.probability}
              />
              <InfoBox
                label="Degradación máx."
                value={`${risk.max_degradation}%`}
              />
              <InfoBox
                label="Severidad cliente"
                value={severity.label}
              />
              <InfoBox
                label="Dimensiones afectadas"
                value={
                  affectedDims.size > 0
                    ? Array.from(affectedDims).join(" · ")
                    : "—"
                }
              />
            </div>
            <p className="mt-2 text-[10px] italic text-[color:var(--fulkro-muted)]">
              Severidad cliente = probabilidad × max(degradación DICAT) ·
              cálculo formal MAGERIT (impacto efectivo · riesgo residual)
              en informe técnico generado por Marcos.
            </p>
          </section>

          {/* Section 3 · Degradación DICAT por dimensión */}
          <section>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
              Degradación por dimensión DICAT (% pérdida si materializa)
            </h4>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5">
              <DegradationChip
                letter="D"
                label="Disponibilidad"
                value={risk.degradation_d}
                affected={affectedDims.has("D")}
              />
              <DegradationChip
                letter="I"
                label="Integridad"
                value={risk.degradation_i}
                affected={affectedDims.has("I")}
              />
              <DegradationChip
                letter="C"
                label="Confidencialidad"
                value={risk.degradation_c}
                affected={affectedDims.has("C")}
              />
              <DegradationChip
                letter="A"
                label="Autenticidad"
                value={risk.degradation_a}
                affected={affectedDims.has("A")}
              />
              <DegradationChip
                letter="T"
                label="Trazabilidad"
                value={risk.degradation_t}
                affected={affectedDims.has("T")}
              />
            </div>
          </section>

          {/* Section 4 · Tu nota previa */}
          {risk.client_review_note && (
            <section>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
                Tu nota previa
              </h4>
              <p className="rounded bg-fulkro-info/10 px-3 py-2 text-xs">
                {risk.client_review_note}
              </p>
            </section>
          )}
        </div>
      )}

      {pendingAction ? (
        <div className="mt-3 space-y-2">
          <label
            htmlFor={`risk-note-${risk.id}`}
            className="text-xs font-medium"
          >
            {pendingAction === "con_pregunta"
              ? "Tu pregunta sobre este riesgo"
              : "Tu sugerencia de cambio"}
          </label>
          <textarea
            id={`risk-note-${risk.id}`}
            rows={3}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:border-fulkro-primary-700 focus:outline-none focus:ring-1 focus:ring-fulkro-primary-700"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={
              pendingAction === "con_pregunta"
                ? "Ej: ¿Por qué la probabilidad es Alta si nunca ha pasado?"
                : "Ej: La degradación de Disponibilidad la veo más cerca del 50%…"
            }
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setPendingAction(null);
                setNote("");
              }}
              className="rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-fulkro-ink-50"
              disabled={submitting}
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={() => void submitWithNote()}
              disabled={submitting || note.trim().length < 5}
              className="rounded-md bg-fulkro-primary-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-fulkro-primary-800 disabled:opacity-50"
            >
              {submitting ? "Guardando…" : "Enviar"}
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void handleAction("revisada_ok")}
            disabled={submitting || risk.client_review_status === "revisada_ok"}
            className="rounded-md bg-fulkro-primary-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-fulkro-primary-800 disabled:opacity-50"
          >
            {risk.client_review_status === "revisada_ok"
              ? "✓ Revisado"
              : "Aceptar · marcar revisado"}
          </button>
          <button
            type="button"
            onClick={() => void handleAction("con_pregunta")}
            disabled={submitting}
            className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-fulkro-warning/10"
          >
            Tengo una pregunta
          </button>
          <button
            type="button"
            onClick={() => void handleAction("suggest_change")}
            disabled={submitting}
            className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-fulkro-info/10"
          >
            Sugerir cambio
          </button>
        </div>
      )}
    </li>
  );
}


function InfoBox({
  label,
  value,
  code,
}: {
  label: string;
  value: string;
  code?: string;
}) {
  return (
    <div className="rounded border bg-fulkro-ink-50/60 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wide text-[color:var(--fulkro-muted)]">
        {label}
      </div>
      <div className="text-xs font-semibold">{value}</div>
      {code && (
        <div className="text-[10px] font-mono text-[color:var(--fulkro-muted)]">
          {code}
        </div>
      )}
    </div>
  );
}
