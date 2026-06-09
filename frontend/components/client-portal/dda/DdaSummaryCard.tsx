"use client";

/**
 * DdaSummaryCard · resumen Declaración de Aplicabilidad cliente.
 *
 * Muestra:
 * - Total medidas + categoría ENS objetivo
 * - Distribución client_review_status: revisadas · pendientes · preguntas · sugerencias
 * - Progress bar completion%
 * - Banner "lista para firmar" si ready_for_final_sign
 * - Última firma (si existe)
 *
 * SAN-E v3.MB-5.3 · cliente in-portal review 73 medidas Anexo II.
 */
import type { DdaClientSummary } from "@/lib/api/dda";

interface Props {
  summary: DdaClientSummary;
  className?: string;
}

const TIER_LABELS: Record<string, string> = {
  BASICA: "Básica",
  MEDIA: "Media",
  ALTA: "Alta",
};

export function DdaSummaryCard({ summary, className = "" }: Props) {
  const tier = summary.categoria_objetivo ?? "—";
  const tierLabel = TIER_LABELS[tier] ?? tier;
  const tierColor =
    tier === "ALTA"
      ? "bg-fulkro-danger/10 text-fulkro-danger border-fulkro-danger/30"
      : tier === "MEDIA"
      ? "bg-fulkro-warning/10 text-fulkro-warning border-fulkro-warning/30"
      : "bg-fulkro-success/10 text-fulkro-success border-fulkro-success/30";

  return (
    <div
      className={`rounded-lg border bg-card p-6 shadow-sm ${className}`.trim()}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[color:var(--fulkro-title)]">
            Tu Declaración de Aplicabilidad
          </h2>
          <p className="mt-1 text-sm text-[color:var(--fulkro-muted)]">
            Revisa cada una de las {summary.total_measures} medidas y
            confirma · pregunta · o sugiere cambio.
          </p>
        </div>
        <span
          className={`inline-flex items-center rounded-md border px-3 py-1 text-xs font-medium ${tierColor}`.trim()}
        >
          Categoría {tierLabel}
        </span>
      </div>

      <div className="mt-4">
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-sm font-medium">Progreso revisión</span>
          <span className="text-sm tabular-nums text-[color:var(--fulkro-muted)]">
            {summary.reviewed_count} de {summary.total_measures} ·{" "}
            {summary.completion_percentage}%
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-fulkro-ink-100">
          <div
            className="h-full bg-fulkro-primary-700 transition-all"
            style={{ width: `${summary.completion_percentage}%` }}
          />
        </div>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatBox label="Revisadas" value={summary.reviewed_count} variant="success" />
        <StatBox label="Pendientes" value={summary.pending_review_count} variant="muted" />
        <StatBox label="Preguntas" value={summary.questions_count} variant="warning" />
        <StatBox label="Sugerencias" value={summary.suggestions_count} variant="info" />
      </dl>

      {summary.ready_for_final_sign && !summary.last_signed_at && (
        <div className="mt-5 rounded-md border border-fulkro-success/30 bg-fulkro-success/10 px-4 py-3 text-sm text-fulkro-success">
          ✓ Has revisado todas las medidas. Puedes firmar la DdA final.
        </div>
      )}

      {!summary.ready_for_final_sign && (
        <div className="mt-5 rounded-md border bg-fulkro-ink-50 px-4 py-3 text-sm text-[color:var(--fulkro-muted)]">
          Completa la revisión de las {summary.pending_review_count} medidas
          pendientes antes de firmar la DdA.
        </div>
      )}

      {summary.last_signed_at && (
        <p className="mt-3 text-xs text-[color:var(--fulkro-muted)]">
          Última versión firmada:{" "}
          {new Date(summary.last_signed_at).toLocaleString("es-ES")}
        </p>
      )}
    </div>
  );
}

interface StatBoxProps {
  label: string;
  value: number;
  variant: "success" | "muted" | "warning" | "info";
}

function StatBox({ label, value, variant }: StatBoxProps) {
  const colorClass = {
    success: "text-fulkro-success",
    muted: "text-[color:var(--fulkro-muted)]",
    warning: "text-fulkro-warning",
    info: "text-fulkro-info",
  }[variant];
  return (
    <div className="rounded-md border bg-fulkro-ink-50/50 px-3 py-2">
      <dt className="text-xs text-[color:var(--fulkro-muted)]">{label}</dt>
      <dd className={`text-2xl font-semibold tabular-nums ${colorClass}`.trim()}>
        {value}
      </dd>
    </div>
  );
}
